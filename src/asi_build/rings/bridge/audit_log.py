#!/usr/bin/env python3
"""
Audit Logging
==============

Structured JSON logging for all bridge operations.  Every deposit,
withdrawal, and approval gets a unique trace ID for end-to-end tracking.

Three log files are maintained:

- ``operations.log`` — all bridge operations (deposits, withdrawals, approvals)
- ``errors.log`` — errors and anomalies only
- ``audit.log`` — immutable audit trail (all events, never truncated independently)

All files use newline-delimited JSON (NDJSON) format for easy ingestion
by log aggregators (Loki, ELK, Datadog, etc.).

Supports:
- Automatic file rotation (``RotatingFileHandler``)
- Structured queries by trace ID, operation type, or time range
- System-level event logging (startup, shutdown, config changes)
- Thread-safe operation

Usage
-----
::

    from asi_build.rings.bridge.audit_log import AuditLogger

    logger = AuditLogger(log_dir="logs/bridge")

    # Log a deposit
    logger.log_deposit(
        trace_id="dep-001",
        tx_hash="0xabc...",
        amount=10**18,
        sender="0x123...",
        recipient_did="did:rings:ed25519:abc",
        status="confirmed",
        block_number=12345,
    )

    # Log an error
    logger.log_error(
        trace_id="dep-001",
        operation="deposit",
        error="insufficient gas",
        gas_price=25_000_000_000,
    )

    # Query recent operations
    events = logger.query(operation="deposit", since=time.time() - 3600)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional


class _JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects.

    Each record is a self-contained JSON dict with at least:
    ``timestamp``, ``level``, ``logger``, ``message``, plus any
    ``extra`` fields attached to the record.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }

        # Merge structured data from the record's extra dict
        if hasattr(record, "structured"):
            entry.update(record.structured)  # type: ignore[arg-type]
        else:
            entry["message"] = record.getMessage()

        return json.dumps(entry, default=str, ensure_ascii=False)


class AuditLogger:
    """Production audit logger with structured JSON output.

    Creates three rotating log files under ``log_dir``:

    - ``operations.log`` — deposits, withdrawals, approvals
    - ``errors.log`` — error events only
    - ``audit.log`` — all events (immutable audit trail)

    Parameters
    ----------
    log_dir : str
        Directory for log files (created if it doesn't exist).
    max_bytes : int
        Maximum size per log file before rotation (default: 50 MB).
    backup_count : int
        Number of rotated backups to keep (default: 10).
    """

    def __init__(
        self,
        log_dir: str = "logs",
        max_bytes: int = 50 * 1024 * 1024,
        backup_count: int = 10,
    ) -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        formatter = _JSONFormatter()

        # ── Operations logger ───────────────────────────────────────────
        self._ops_logger = logging.getLogger("bridge.operations")
        self._ops_logger.setLevel(logging.INFO)
        self._ops_logger.propagate = False
        ops_handler = RotatingFileHandler(
            str(self._log_dir / "operations.log"),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        ops_handler.setFormatter(formatter)
        # Avoid duplicate handlers on re-initialization
        if not self._ops_logger.handlers:
            self._ops_logger.addHandler(ops_handler)

        # ── Errors logger ───────────────────────────────────────────────
        self._err_logger = logging.getLogger("bridge.errors")
        self._err_logger.setLevel(logging.ERROR)
        self._err_logger.propagate = False
        err_handler = RotatingFileHandler(
            str(self._log_dir / "errors.log"),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        err_handler.setFormatter(formatter)
        if not self._err_logger.handlers:
            self._err_logger.addHandler(err_handler)

        # ── Audit logger (all events) ──────────────────────────────────
        self._audit_logger = logging.getLogger("bridge.audit")
        self._audit_logger.setLevel(logging.DEBUG)
        self._audit_logger.propagate = False
        audit_handler = RotatingFileHandler(
            str(self._log_dir / "audit.log"),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        audit_handler.setFormatter(formatter)
        if not self._audit_logger.handlers:
            self._audit_logger.addHandler(audit_handler)

    # ── Internal helpers ───────────────────────────────────────────────

    @staticmethod
    def generate_trace_id() -> str:
        """Generate a unique trace ID (UUID4-based, prefixed)."""
        return f"trace-{uuid.uuid4().hex[:16]}"

    def _emit(
        self,
        level: int,
        data: Dict[str, Any],
        *,
        to_ops: bool = True,
        to_err: bool = False,
    ) -> None:
        """Emit a structured log record to the appropriate loggers.

        Parameters
        ----------
        level : int
            Python logging level (e.g. ``logging.INFO``).
        data : dict
            Structured event data.
        to_ops : bool
            Emit to the operations log.
        to_err : bool
            Emit to the errors log.
        """
        # Always goes to audit
        record = logging.LogRecord(
            name="bridge.audit",
            level=level,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        record.structured = data  # type: ignore[attr-defined]

        with self._lock:
            self._audit_logger.handle(record)

            if to_ops:
                ops_record = logging.LogRecord(
                    name="bridge.operations",
                    level=level,
                    pathname="",
                    lineno=0,
                    msg="",
                    args=(),
                    exc_info=None,
                )
                ops_record.structured = data  # type: ignore[attr-defined]
                self._ops_logger.handle(ops_record)

            if to_err:
                err_record = logging.LogRecord(
                    name="bridge.errors",
                    level=logging.ERROR,
                    pathname="",
                    lineno=0,
                    msg="",
                    args=(),
                    exc_info=None,
                )
                err_record.structured = data  # type: ignore[attr-defined]
                self._err_logger.handle(err_record)

    # ── Public API ────────────────────────────────────────────────────

    def log_deposit(
        self,
        trace_id: str,
        tx_hash: str,
        amount: int,
        sender: str,
        recipient_did: str,
        status: str,
        **extra: Any,
    ) -> None:
        """Log a deposit operation.

        Parameters
        ----------
        trace_id : str
            Unique trace identifier for this operation.
        tx_hash : str
            On-chain transaction hash.
        amount : int
            Deposit amount in wei (or smallest token unit).
        sender : str
            Depositor's Ethereum address.
        recipient_did : str
            Rings DID to credit on the other side of the bridge.
        status : str
            Current status (e.g. ``"pending"``, ``"confirmed"``, ``"failed"``).
        **extra
            Additional key-value pairs (``block_number``, ``gas_used``, etc.).
        """
        data: Dict[str, Any] = {
            "operation": "deposit",
            "trace_id": trace_id,
            "tx_hash": tx_hash,
            "amount": amount,
            "amount_eth": amount / 1e18 if isinstance(amount, (int, float)) else None,
            "sender": sender,
            "recipient_did": recipient_did,
            "status": status,
            **extra,
        }
        level = logging.INFO if status != "failed" else logging.ERROR
        self._emit(level, data, to_err=(status == "failed"))

    def log_withdrawal(
        self,
        trace_id: str,
        withdrawal_id: str,
        amount: int,
        recipient: str,
        status: str,
        **extra: Any,
    ) -> None:
        """Log a withdrawal operation.

        Parameters
        ----------
        trace_id : str
            Unique trace identifier.
        withdrawal_id : str
            On-chain withdrawal nonce or identifier.
        amount : int
            Withdrawal amount in wei.
        recipient : str
            Ethereum address receiving the withdrawal.
        status : str
            Current status (``"pending"``, ``"confirmed"``, ``"failed"``).
        **extra
            Additional fields (``proof_valid``, ``block_number``, etc.).
        """
        data: Dict[str, Any] = {
            "operation": "withdrawal",
            "trace_id": trace_id,
            "withdrawal_id": withdrawal_id,
            "amount": amount,
            "amount_eth": amount / 1e18 if isinstance(amount, (int, float)) else None,
            "recipient": recipient,
            "status": status,
            **extra,
        }
        level = logging.INFO if status != "failed" else logging.ERROR
        self._emit(level, data, to_err=(status == "failed"))

    def log_approval(
        self,
        trace_id: str,
        withdrawal_id: str,
        validator_id: str,
        approved: bool,
        **extra: Any,
    ) -> None:
        """Log a validator approval/rejection for a withdrawal.

        Parameters
        ----------
        trace_id : str
            Unique trace identifier.
        withdrawal_id : str
            The withdrawal being voted on.
        validator_id : str
            Identifier of the validator casting the vote.
        approved : bool
            True if the validator approved the withdrawal.
        **extra
            Additional fields (``reason``, ``quorum``, ``votes_for``, etc.).
        """
        data: Dict[str, Any] = {
            "operation": "approval",
            "trace_id": trace_id,
            "withdrawal_id": withdrawal_id,
            "validator_id": validator_id,
            "approved": approved,
            **extra,
        }
        self._emit(logging.INFO, data)

    def log_error(
        self,
        trace_id: str,
        operation: str,
        error: str,
        **extra: Any,
    ) -> None:
        """Log an error event.

        Parameters
        ----------
        trace_id : str
            Trace ID of the operation that failed.
        operation : str
            Operation type (``"deposit"``, ``"withdrawal"``, ``"approval"``,
            ``"system"``, etc.).
        error : str
            Human-readable error description.
        **extra
            Additional context (``stack_trace``, ``tx_hash``, ``gas_used``).
        """
        data: Dict[str, Any] = {
            "operation": operation,
            "trace_id": trace_id,
            "error": error,
            "severity": "error",
            **extra,
        }
        self._emit(logging.ERROR, data, to_err=True)

    def log_system(self, event: str, **extra: Any) -> None:
        """Log a system-level event.

        Parameters
        ----------
        event : str
            Event name (e.g. ``"startup"``, ``"shutdown"``, ``"config_changed"``,
            ``"guardian_rotated"``, ``"bridge_paused"``).
        **extra
            Additional context.
        """
        data: Dict[str, Any] = {
            "operation": "system",
            "event": event,
            **extra,
        }
        self._emit(logging.INFO, data, to_ops=False)

    # ── Query ─────────────────────────────────────────────────────────

    def query(
        self,
        trace_id: Optional[str] = None,
        operation: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Query the audit log for matching events.

        Searches the ``audit.log`` file (plus rotated backups) for events
        matching the given filters.  Returns newest-first.

        Parameters
        ----------
        trace_id : str, optional
            Filter by exact trace ID.
        operation : str, optional
            Filter by operation type (``"deposit"``, ``"withdrawal"``, etc.).
        since : float, optional
            Unix timestamp — only return events after this time.
        limit : int
            Maximum number of results to return (default: 1000).

        Returns
        -------
        list of dict
            Matching events, newest first.
        """
        results: List[Dict[str, Any]] = []
        log_files = self._get_log_files("audit.log")

        for log_file in log_files:
            if len(results) >= limit:
                break
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        # Apply filters
                        if trace_id and entry.get("trace_id") != trace_id:
                            continue
                        if operation and entry.get("operation") != operation:
                            continue
                        if since:
                            ts = entry.get("timestamp", "")
                            if ts:
                                try:
                                    entry_time = datetime.fromisoformat(ts).timestamp()
                                    if entry_time < since:
                                        continue
                                except (ValueError, TypeError):
                                    pass

                        results.append(entry)
                        if len(results) >= limit:
                            break
            except FileNotFoundError:
                continue

        # Newest first
        results.reverse()
        return results[:limit]

    def _get_log_files(self, base_name: str) -> List[Path]:
        """Get all log files for a given base name (including rotated ones).

        Returns files ordered: current → .1 → .2 → ... (newest data first
        within each file, but we read them in order).
        """
        base = self._log_dir / base_name
        files: List[Path] = []
        if base.exists():
            files.append(base)
        # Rotated files: audit.log.1, audit.log.2, ...
        for i in range(1, 100):
            rotated = self._log_dir / f"{base_name}.{i}"
            if rotated.exists():
                files.append(rotated)
            else:
                break
        return files

    # ── Convenience ───────────────────────────────────────────────────

    @property
    def log_dir(self) -> Path:
        """Return the log directory path."""
        return self._log_dir

    def __repr__(self) -> str:
        return f"AuditLogger(log_dir={self._log_dir!r})"
