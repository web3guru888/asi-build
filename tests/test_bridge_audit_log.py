"""
Bridge Audit Log Tests
=======================

20 tests covering:
- AuditLogger initialisation (2): directory creation, log file setup
- log_deposit (3): writes structured JSON, failed status, extra fields
- log_withdrawal (2): structured JSON with trace_id, withdrawal_id
- log_approval (2): approval and rejection events
- log_error (2): error events, extra context
- log_system (2): system events, not written to ops log
- query (4): filter by trace_id, operation, time range, limit
- generate_trace_id (2): UUID format, uniqueness
- _emit internals (1): audit log always receives events

All tests use tmp_path fixture for file operations — no side effects.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import pytest

from asi_build.rings.bridge.audit_log import AuditLogger


@pytest.fixture(autouse=True)
def _clear_audit_loggers():
    """Clear cached logger handlers between tests.

    AuditLogger uses named loggers (``bridge.operations``, ``bridge.errors``,
    ``bridge.audit``).  Python's ``logging.getLogger`` caches them globally,
    so handlers from a previous test's AuditLogger will persist and the
    ``if not self._*_logger.handlers`` guard in ``__init__`` prevents the
    new instance from adding handlers to the new tmp_path.

    This fixture strips all handlers before each test so every
    ``AuditLogger(log_dir=tmp_path)`` gets a clean slate.
    """
    for name in ("bridge.operations", "bridge.errors", "bridge.audit"):
        lgr = logging.getLogger(name)
        lgr.handlers.clear()
    yield
    for name in ("bridge.operations", "bridge.errors", "bridge.audit"):
        lgr = logging.getLogger(name)
        lgr.handlers.clear()


def _flush_logger(al: AuditLogger) -> None:
    """Flush all handlers so data is on disk before assertions."""
    for lgr in (al._ops_logger, al._err_logger, al._audit_logger):
        for h in lgr.handlers:
            h.flush()


# ===========================================================================
# Initialisation Tests (2)
# ===========================================================================


class TestAuditLoggerInit:
    """Tests for AuditLogger initialisation."""

    def test_creates_log_directory(self, tmp_path):
        """AuditLogger should create the log directory if it doesn't exist."""
        log_dir = tmp_path / "nonexistent" / "bridge-logs"
        assert not log_dir.exists()

        _logger = AuditLogger(log_dir=str(log_dir))
        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_creates_log_files_on_first_write(self, tmp_path):
        """Log files should be created when the first event is written."""
        log_dir = tmp_path / "logs"
        al = AuditLogger(log_dir=str(log_dir))

        al.log_system("startup", version="1.0")
        _flush_logger(al)

        # audit.log should exist (system events go to audit)
        assert (log_dir / "audit.log").exists()


# ===========================================================================
# log_deposit Tests (3)
# ===========================================================================


class TestLogDeposit:
    """Tests for deposit logging."""

    def test_deposit_writes_structured_json(self, tmp_path):
        """log_deposit should write a valid JSON line to operations and audit logs."""
        al = AuditLogger(log_dir=str(tmp_path))
        al.log_deposit(
            trace_id="dep-001",
            tx_hash="0xabc123",
            amount=10**18,
            sender="0xSender",
            recipient_did="did:rings:ed25519:abc",
            status="confirmed",
            block_number=12345,
        )
        _flush_logger(al)

        # Read the audit log
        content = (tmp_path / "audit.log").read_text()
        lines = [line for line in content.strip().split("\n") if line.strip()]
        assert len(lines) >= 1

        entry = json.loads(lines[-1])
        assert entry["operation"] == "deposit"
        assert entry["trace_id"] == "dep-001"
        assert entry["tx_hash"] == "0xabc123"
        assert entry["amount"] == 10**18
        assert entry["sender"] == "0xSender"
        assert entry["status"] == "confirmed"
        assert entry["block_number"] == 12345

    def test_deposit_failed_goes_to_error_log(self, tmp_path):
        """A deposit with status='failed' should also appear in errors.log."""
        al = AuditLogger(log_dir=str(tmp_path))
        al.log_deposit(
            trace_id="dep-fail",
            tx_hash="0xbad",
            amount=0,
            sender="0xS",
            recipient_did="did:rings:x",
            status="failed",
        )
        _flush_logger(al)

        errors_content = (tmp_path / "errors.log").read_text()
        assert "dep-fail" in errors_content

    def test_deposit_includes_amount_eth(self, tmp_path):
        """Deposit events should include a computed amount_eth field."""
        al = AuditLogger(log_dir=str(tmp_path))
        al.log_deposit(
            trace_id="dep-eth",
            tx_hash="0xeth",
            amount=2 * 10**18,
            sender="0xS",
            recipient_did="did:rings:x",
            status="confirmed",
        )
        _flush_logger(al)

        content = (tmp_path / "audit.log").read_text()
        entry = json.loads(content.strip().split("\n")[-1])
        assert entry["amount_eth"] == pytest.approx(2.0)


# ===========================================================================
# log_withdrawal Tests (2)
# ===========================================================================


class TestLogWithdrawal:
    """Tests for withdrawal logging."""

    def test_withdrawal_structured_json(self, tmp_path):
        """log_withdrawal should write structured JSON with all fields."""
        al = AuditLogger(log_dir=str(tmp_path))
        al.log_withdrawal(
            trace_id="wd-001",
            withdrawal_id="nonce-42",
            amount=5 * 10**18,
            recipient="0xRecip",
            status="confirmed",
            proof_valid=True,
        )
        _flush_logger(al)

        content = (tmp_path / "audit.log").read_text()
        entry = json.loads(content.strip().split("\n")[-1])
        assert entry["operation"] == "withdrawal"
        assert entry["trace_id"] == "wd-001"
        assert entry["withdrawal_id"] == "nonce-42"
        assert entry["recipient"] == "0xRecip"
        assert entry["proof_valid"] is True

    def test_withdrawal_failed_in_errors(self, tmp_path):
        """A failed withdrawal should appear in errors.log."""
        al = AuditLogger(log_dir=str(tmp_path))
        al.log_withdrawal(
            trace_id="wd-fail",
            withdrawal_id="nonce-99",
            amount=100,
            recipient="0xR",
            status="failed",
        )
        _flush_logger(al)

        errors_content = (tmp_path / "errors.log").read_text()
        assert "wd-fail" in errors_content


# ===========================================================================
# log_approval Tests (2)
# ===========================================================================


class TestLogApproval:
    """Tests for approval logging."""

    def test_approval_event(self, tmp_path):
        """log_approval should log an approval event."""
        al = AuditLogger(log_dir=str(tmp_path))
        al.log_approval(
            trace_id="wd-001",
            withdrawal_id="nonce-42",
            validator_id="v1",
            approved=True,
            quorum="4/6",
        )
        _flush_logger(al)

        content = (tmp_path / "audit.log").read_text()
        entry = json.loads(content.strip().split("\n")[-1])
        assert entry["operation"] == "approval"
        assert entry["approved"] is True
        assert entry["validator_id"] == "v1"
        assert entry["quorum"] == "4/6"

    def test_rejection_event(self, tmp_path):
        """log_approval with approved=False should log a rejection."""
        al = AuditLogger(log_dir=str(tmp_path))
        al.log_approval(
            trace_id="wd-002",
            withdrawal_id="nonce-43",
            validator_id="v2",
            approved=False,
            reason="amount exceeds limit",
        )
        _flush_logger(al)

        content = (tmp_path / "audit.log").read_text()
        entry = json.loads(content.strip().split("\n")[-1])
        assert entry["approved"] is False
        assert entry["reason"] == "amount exceeds limit"


# ===========================================================================
# log_error Tests (2)
# ===========================================================================


class TestLogError:
    """Tests for error logging."""

    def test_error_event(self, tmp_path):
        """log_error should write to both audit and errors logs."""
        al = AuditLogger(log_dir=str(tmp_path))
        al.log_error(
            trace_id="err-001",
            operation="deposit",
            error="insufficient gas",
            gas_price=25_000_000_000,
        )
        _flush_logger(al)

        # Check audit log
        audit_content = (tmp_path / "audit.log").read_text()
        entry = json.loads(audit_content.strip().split("\n")[-1])
        assert entry["operation"] == "deposit"
        assert entry["error"] == "insufficient gas"
        assert entry["severity"] == "error"
        assert entry["gas_price"] == 25_000_000_000

        # Check errors log
        errors_content = (tmp_path / "errors.log").read_text()
        assert "insufficient gas" in errors_content

    def test_error_with_extra_context(self, tmp_path):
        """Extra kwargs should be included in the error event."""
        al = AuditLogger(log_dir=str(tmp_path))
        al.log_error(
            trace_id="err-002",
            operation="withdrawal",
            error="proof verification failed",
            proof_hash="0xdeadbeef",
            attempt=3,
        )
        _flush_logger(al)

        content = (tmp_path / "audit.log").read_text()
        entry = json.loads(content.strip().split("\n")[-1])
        assert entry["proof_hash"] == "0xdeadbeef"
        assert entry["attempt"] == 3


# ===========================================================================
# log_system Tests (2)
# ===========================================================================


class TestLogSystem:
    """Tests for system event logging."""

    def test_system_event_to_audit(self, tmp_path):
        """System events should appear in audit.log."""
        al = AuditLogger(log_dir=str(tmp_path))
        al.log_system("startup", version="2.0", node_count=6)
        _flush_logger(al)

        content = (tmp_path / "audit.log").read_text()
        entry = json.loads(content.strip().split("\n")[-1])
        assert entry["operation"] == "system"
        assert entry["event"] == "startup"
        assert entry["version"] == "2.0"

    def test_system_event_not_in_ops_log(self, tmp_path):
        """System events should NOT appear in operations.log."""
        al = AuditLogger(log_dir=str(tmp_path))
        al.log_system("config_changed", setting="bridge_address")
        _flush_logger(al)

        ops_path = tmp_path / "operations.log"
        if ops_path.exists():
            ops_content = ops_path.read_text()
            assert "config_changed" not in ops_content
        # If ops.log doesn't exist, that also means no write — pass


# ===========================================================================
# query Tests (4)
# ===========================================================================


class TestQuery:
    """Tests for audit log querying."""

    @pytest.fixture
    def populated_logger(self, tmp_path):
        """Logger with some pre-populated events."""
        al = AuditLogger(log_dir=str(tmp_path))
        al.log_deposit(
            trace_id="t-001",
            tx_hash="0x1",
            amount=100,
            sender="0xS",
            recipient_did="did:rings:a",
            status="confirmed",
        )
        al.log_withdrawal(
            trace_id="t-002",
            withdrawal_id="wd-1",
            amount=200,
            recipient="0xR",
            status="pending",
        )
        al.log_deposit(
            trace_id="t-003",
            tx_hash="0x3",
            amount=300,
            sender="0xS2",
            recipient_did="did:rings:b",
            status="confirmed",
        )
        al.log_error(
            trace_id="t-001",
            operation="deposit",
            error="retry",
        )
        _flush_logger(al)
        return al

    def test_query_by_trace_id(self, populated_logger):
        """query(trace_id=...) should return only matching events."""
        results = populated_logger.query(trace_id="t-001")
        assert len(results) >= 2  # deposit + error, both with trace t-001
        for r in results:
            assert r["trace_id"] == "t-001"

    def test_query_by_operation(self, populated_logger):
        """query(operation=...) should filter by operation type."""
        deposits = populated_logger.query(operation="deposit")
        assert len(deposits) >= 2
        for d in deposits:
            assert d["operation"] == "deposit"

    def test_query_limit(self, populated_logger):
        """query(limit=N) should cap results."""
        results = populated_logger.query(limit=1)
        assert len(results) == 1

    def test_query_returns_newest_first(self, populated_logger):
        """Results should be ordered newest-first (reversed from file order)."""
        # The file has: t-001 dep, t-002 wd, t-003 dep, t-001 err(op=deposit)
        # Querying all (no filter) returns them reversed:
        # [t-001 err, t-003 dep, t-002 wd, t-001 dep]
        results = populated_logger.query()
        assert len(results) == 4
        # Last written event should be first in results
        assert results[0]["trace_id"] == "t-001"
        assert results[0].get("error") == "retry"


# ===========================================================================
# generate_trace_id Tests (2)
# ===========================================================================


class TestGenerateTraceId:
    """Tests for trace ID generation."""

    def test_format(self):
        """Trace IDs should be prefixed with 'trace-' and contain hex chars."""
        tid = AuditLogger.generate_trace_id()
        assert tid.startswith("trace-")
        hex_part = tid.removeprefix("trace-")
        assert len(hex_part) == 16
        int(hex_part, 16)  # should not raise

    def test_uniqueness(self):
        """Multiple calls should produce unique trace IDs."""
        ids = {AuditLogger.generate_trace_id() for _ in range(100)}
        assert len(ids) == 100


# ===========================================================================
# _emit Internals Test (1)
# ===========================================================================


class TestEmitInternals:
    """Test that _emit always writes to audit log."""

    def test_audit_log_always_receives(self, tmp_path):
        """Every _emit call should produce a line in audit.log."""
        al = AuditLogger(log_dir=str(tmp_path))

        # Log different types
        al.log_deposit(
            trace_id="e1", tx_hash="0x1", amount=1, sender="0xS",
            recipient_did="did:x", status="confirmed",
        )
        al.log_system("test_event")
        al.log_error(trace_id="e3", operation="test", error="oops")
        _flush_logger(al)

        content = (tmp_path / "audit.log").read_text()
        lines = [line for line in content.strip().split("\n") if line.strip()]
        assert len(lines) == 3
