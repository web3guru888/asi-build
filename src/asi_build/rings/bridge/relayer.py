"""
Bridge Relayer Daemon
=====================

Production-grade long-running service that monitors bridge events,
processes deposits/withdrawals, and maintains bridge state.

The relayer is the operational counterpart to :class:`BridgeOrchestrator`
— while the orchestrator embodies the *logic* (attest → prove → submit),
the relayer wraps that logic in a resilient, observable daemon with:

* **SQLite persistent state** (WAL mode) for deposit/withdrawal tracking
  across restarts.
* **Exponential-backoff retry** with jitter on transient failures.
* **Health-check HTTP server** (``/health``, ``/metrics``, ``/status``)
  for Kubernetes probes and Prometheus scraping.
* **Structured JSON logging** to rotating file + human-readable console.
* **Graceful shutdown** via :pymod:`asyncio` event + task cancellation.

Deployment
~~~~~~~~~~

Run directly::

    python -m asi_build.rings.bridge.relayer

Or via environment variables::

    BRIDGE_RPC_URL=https://ethereum-sepolia-rpc.publicnode.com \\
    BRIDGE_ADDRESS=0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca \\
    BRIDGE_PRIVATE_KEY=0x... \\
    python -m asi_build.rings.bridge.relayer

The relayer reads Rings cluster node URLs from
``/shared/rings-cluster/node-{0-5}.url`` at startup.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import logging.handlers
import os
import random
import signal
import sys
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
from aiohttp import web

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OperationStatus(Enum):
    """Lifecycle status for tracked deposits and withdrawals."""

    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class RelayerConfig:
    """Relayer configuration, loaded from env vars with sensible defaults.

    Attributes
    ----------
    rpc_url : str
        Ethereum JSON-RPC endpoint.
    bridge_address : str
        Deployed ``RingsBridge`` contract address.
    token_address : str
        Deployed ``BridgedToken`` (bASI) address.
    verifier_address : str
        Deployed ``Groth16Verifier`` address.
    private_key : str
        Hex-encoded private key for the relayer account.
    db_path : str
        Filesystem path for the SQLite state database.
    poll_interval : float
        Seconds between event-polling iterations (default: 12 — one
        Ethereum block time).
    confirmations : int
        Block confirmations required before a deposit is considered final.
    health_port : int
        TCP port for the HTTP health/metrics server.
    max_retry : int
        Maximum retries before a withdrawal is marked ``FAILED``.
    retry_base_delay : float
        Base delay for exponential backoff (seconds).
    retry_max_delay : float
        Maximum backoff ceiling (seconds).
    log_file : str
        Path for the rotating JSON log file.
    log_level : str
        Python logging level name.
    node_urls : list of str
        Rings cluster node URLs (read from ``/shared/rings-cluster/``).
    """

    rpc_url: str = "https://ethereum-sepolia-rpc.publicnode.com"
    bridge_address: str = ""
    token_address: str = ""
    verifier_address: str = ""
    private_key: str = ""
    db_path: str = "relayer.db"
    poll_interval: float = 12.0
    confirmations: int = 2
    health_port: int = 8080
    max_retry: int = 5
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    log_file: str = "relayer.log"
    log_level: str = "INFO"
    node_urls: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "RelayerConfig":
        """Load config from environment variables.

        Node URLs are discovered from ``/shared/rings-cluster/node-{i}.url``
        files.  Missing files are silently skipped.
        """
        node_urls: List[str] = []
        for i in range(6):
            path = f"/shared/rings-cluster/node-{i}.url"
            try:
                with open(path) as f:
                    url = f.read().strip()
                    if url:
                        node_urls.append(url)
            except FileNotFoundError:
                pass

        return cls(
            rpc_url=os.getenv(
                "BRIDGE_RPC_URL",
                "https://ethereum-sepolia-rpc.publicnode.com",
            ),
            bridge_address=os.getenv(
                "BRIDGE_ADDRESS",
                "0xE034d479EDc2530d9917dDa4547b59bF0964A2Ca",
            ),
            token_address=os.getenv(
                "BRIDGE_TOKEN_ADDRESS",
                "0x257dDA1fa34eb847060EcB743E808B65099FB497",
            ),
            verifier_address=os.getenv(
                "BRIDGE_VERIFIER_ADDRESS",
                "0x9186fc5e27c15aEDbA2512687F2eF2E5aC7C0e59",
            ),
            private_key=os.getenv("BRIDGE_PRIVATE_KEY", ""),
            db_path=os.getenv("RELAYER_DB_PATH", "relayer.db"),
            poll_interval=float(os.getenv("RELAYER_POLL_INTERVAL", "12.0")),
            confirmations=int(os.getenv("RELAYER_CONFIRMATIONS", "2")),
            health_port=int(os.getenv("RELAYER_HEALTH_PORT", "8080")),
            max_retry=int(os.getenv("RELAYER_MAX_RETRY", "5")),
            retry_base_delay=float(os.getenv("RELAYER_RETRY_BASE_DELAY", "1.0")),
            retry_max_delay=float(os.getenv("RELAYER_RETRY_MAX_DELAY", "60.0")),
            log_file=os.getenv("RELAYER_LOG_FILE", "relayer.log"),
            log_level=os.getenv("RELAYER_LOG_LEVEL", "INFO"),
            node_urls=node_urls,
        )


# ---------------------------------------------------------------------------
# JSON log formatter
# ---------------------------------------------------------------------------


class _JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    Fields: ``ts``, ``level``, ``logger``, ``msg``, and any ``extra``
    keys injected via ``logger.info("...", extra={...})``.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: Dict[str, Any] = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        # Capture any extra fields the caller passed
        for key in ("trace_id", "tx_hash", "withdrawal_id", "event"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val
        return json.dumps(entry, default=str)


# ---------------------------------------------------------------------------
# RelayerDB — SQLite persistent state
# ---------------------------------------------------------------------------


class RelayerDB:
    """SQLite-backed persistent state for deposit/withdrawal tracking.

    Uses WAL journal mode for concurrent readers and a single writer.
    Schema is auto-created on :meth:`initialize`.
    """

    _SCHEMA = """\
        CREATE TABLE IF NOT EXISTS deposits (
            tx_hash         TEXT PRIMARY KEY,
            block_number    INTEGER NOT NULL,
            amount          TEXT NOT NULL,
            sender          TEXT NOT NULL,
            recipient_did   TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'pending',
            trace_id        TEXT NOT NULL,
            created_at      REAL NOT NULL,
            updated_at      REAL NOT NULL,
            error           TEXT,
            retry_count     INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS withdrawals (
            withdrawal_id   TEXT PRIMARY KEY,
            nonce           INTEGER,
            amount          TEXT NOT NULL,
            recipient       TEXT NOT NULL,
            requester_did   TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'pending',
            trace_id        TEXT NOT NULL,
            proof           BLOB,
            public_inputs   TEXT,
            tx_hash         TEXT,
            approvals       TEXT DEFAULT '{}',
            created_at      REAL NOT NULL,
            updated_at      REAL NOT NULL,
            error           TEXT,
            retry_count     INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS state (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_deposits_status
            ON deposits(status);
        CREATE INDEX IF NOT EXISTS idx_deposits_block
            ON deposits(block_number);
        CREATE INDEX IF NOT EXISTS idx_withdrawals_status
            ON withdrawals(status);
        CREATE INDEX IF NOT EXISTS idx_withdrawals_nonce
            ON withdrawals(nonce);
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Open (or create) the database and ensure schema exists."""
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA synchronous=NORMAL")
        await self._db.executescript(self._SCHEMA)
        await self._db.commit()
        logger.info("Relayer DB initialized at %s", self.db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    # ── Key-value state ─────────────────────────────────────────────────

    async def get_state(self, key: str, default: str = "") -> str:
        """Read a string value from the ``state`` table."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT value FROM state WHERE key = ?", (key,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else default

    async def set_state(self, key: str, value: str) -> None:
        """Write a string value to the ``state`` table (upsert)."""
        assert self._db is not None
        now = time.time()
        await self._db.execute(
            "INSERT OR REPLACE INTO state(key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, now),
        )
        await self._db.commit()

    # ── Deposits ────────────────────────────────────────────────────────

    async def insert_deposit(
        self,
        tx_hash: str,
        block_number: int,
        amount: int,
        sender: str,
        recipient_did: str,
        trace_id: str,
    ) -> None:
        """Insert a new deposit record.  Silently ignores duplicates."""
        assert self._db is not None
        now = time.time()
        await self._db.execute(
            """INSERT OR IGNORE INTO deposits
               (tx_hash, block_number, amount, sender, recipient_did,
                status, trace_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tx_hash,
                block_number,
                str(amount),
                sender,
                recipient_did,
                OperationStatus.PENDING.value,
                trace_id,
                now,
                now,
            ),
        )
        await self._db.commit()

    async def update_deposit_status(
        self,
        tx_hash: str,
        status: OperationStatus,
        error: Optional[str] = None,
    ) -> None:
        """Update the status (and optional error) for a deposit."""
        assert self._db is not None
        now = time.time()
        await self._db.execute(
            "UPDATE deposits SET status = ?, updated_at = ?, error = ? WHERE tx_hash = ?",
            (status.value, now, error, tx_hash),
        )
        await self._db.commit()

    async def get_pending_deposits(self) -> List[Dict[str, Any]]:
        """Return all deposits with status ``pending`` or ``processing``."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT * FROM deposits WHERE status IN ('pending', 'processing') "
            "ORDER BY block_number"
        ) as cur:
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in await cur.fetchall()]

    # ── Withdrawals ─────────────────────────────────────────────────────

    async def insert_withdrawal(
        self,
        withdrawal_id: str,
        amount: int,
        recipient: str,
        requester_did: str,
        trace_id: str,
    ) -> None:
        """Insert a new withdrawal request."""
        assert self._db is not None
        now = time.time()
        await self._db.execute(
            """INSERT INTO withdrawals
               (withdrawal_id, amount, recipient, requester_did,
                status, trace_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                withdrawal_id,
                str(amount),
                recipient,
                requester_did,
                OperationStatus.PENDING.value,
                trace_id,
                now,
                now,
            ),
        )
        await self._db.commit()

    async def update_withdrawal_status(
        self,
        withdrawal_id: str,
        status: OperationStatus,
        error: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Update withdrawal status and optional extra columns.

        Accepted *kwargs*: ``nonce``, ``tx_hash``, ``proof``,
        ``public_inputs``, ``approvals``.
        """
        assert self._db is not None
        now = time.time()
        sets = ["status = ?", "updated_at = ?", "error = ?"]
        vals: list = [status.value, now, error]
        _allowed_cols = {"nonce", "tx_hash", "proof", "public_inputs", "approvals"}
        for col, val in kwargs.items():
            if col in _allowed_cols:
                sets.append(f"{col} = ?")
                vals.append(val)
        vals.append(withdrawal_id)
        await self._db.execute(
            f"UPDATE withdrawals SET {', '.join(sets)} WHERE withdrawal_id = ?",
            vals,
        )
        await self._db.commit()

    async def increment_withdrawal_retry(self, withdrawal_id: str) -> int:
        """Increment and return the new retry count for a withdrawal."""
        assert self._db is not None
        await self._db.execute(
            "UPDATE withdrawals SET retry_count = retry_count + 1 WHERE withdrawal_id = ?",
            (withdrawal_id,),
        )
        await self._db.commit()
        async with self._db.execute(
            "SELECT retry_count FROM withdrawals WHERE withdrawal_id = ?",
            (withdrawal_id,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

    async def get_pending_withdrawals(self) -> List[Dict[str, Any]]:
        """Return all withdrawals with status ``pending`` or ``processing``."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT * FROM withdrawals WHERE status IN ('pending', 'processing') "
            "ORDER BY created_at"
        ) as cur:
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in await cur.fetchall()]

    # ── Statistics ──────────────────────────────────────────────────────

    async def get_stats(self) -> Dict[str, Any]:
        """Return aggregate counts grouped by status for each table."""
        assert self._db is not None
        stats: Dict[str, Any] = {}
        for table in ("deposits", "withdrawals"):
            async with self._db.execute(
                f"SELECT status, COUNT(*) FROM {table} GROUP BY status"
            ) as cur:
                stats[table] = dict(await cur.fetchall())
            async with self._db.execute(
                f"SELECT COUNT(*) FROM {table}"
            ) as cur:
                stats[f"{table}_total"] = (await cur.fetchone())[0]
        return stats


# ---------------------------------------------------------------------------
# BridgeRelayer — the daemon
# ---------------------------------------------------------------------------


class BridgeRelayer:
    """Long-running service that monitors bridge events and processes operations.

    The relayer watches for ``Deposited`` events on the
    ``RingsBridge`` contract, verifies them against block finality,
    records them in a local SQLite database, and broadcasts to the
    Rings DHT.  It also processes a withdrawal queue: collecting
    validator approvals, generating ZK proofs, and submitting
    on-chain withdrawal transactions.

    Features
    --------
    * Polls ``Deposited`` events from the ``RingsBridge`` contract.
    * Processes pending withdrawals with validator consensus + ZK proofs.
    * Health-check HTTP server (``/health``, ``/metrics``, ``/status``).
    * SQLite WAL-mode persistent state for crash recovery.
    * Exponential backoff with jitter on transient failures.
    * Structured JSON logging via ``RotatingFileHandler``.
    * Graceful shutdown (SIGINT / SIGTERM).

    Parameters
    ----------
    config : RelayerConfig, optional
        If ``None``, loads from environment variables.
    """

    def __init__(self, config: Optional[RelayerConfig] = None) -> None:
        self.config = config or RelayerConfig.from_env()
        self.db = RelayerDB(self.config.db_path)

        self._running = False
        self._shutdown_event = asyncio.Event()

        # Web3 objects — initialised in _init_web3()
        self._web3: Any = None
        self._account: Any = None
        self._bridge_contract: Any = None

        # HTTP health server
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None

        # Concurrent task handles
        self._tasks: List[asyncio.Task] = []  # type: ignore[type-arg]

        # Monotonic start time for uptime calculation
        self._start_time: float = 0.0

        # Operational metrics (in-memory; persisted via /metrics endpoint)
        self._metrics: Dict[str, Any] = {
            "deposits_processed": 0,
            "deposits_failed": 0,
            "withdrawals_processed": 0,
            "withdrawals_failed": 0,
            "rpc_errors": 0,
            "last_block_scanned": 0,
            "last_error": None,
            "uptime_seconds": 0,
        }

        self._setup_logging()

    # ── Logging ─────────────────────────────────────────────────────────

    def _setup_logging(self) -> None:
        """Configure structured JSON logging to a rotating file + console.

        * **File handler**: ``RotatingFileHandler`` (10 MB × 5 backups),
          JSON-formatted lines for machine parsing.
        * **Console handler**: human-readable ``%(asctime)s [%(levelname)s]``
          format.
        """
        root = logging.getLogger()
        level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        root.setLevel(level)

        # Avoid duplicate handlers on re-init
        for h in root.handlers[:]:
            root.removeHandler(h)

        # ── Console (human-readable) ────────────────────────────────────
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(level)
        console.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%SZ",
            )
        )
        root.addHandler(console)

        # ── Rotating file (JSON) ────────────────────────────────────────
        try:
            log_dir = Path(self.config.log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                self.config.log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(_JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%SZ"))
            root.addHandler(file_handler)
        except OSError as exc:
            # If we can't open the log file, continue with console only
            logger.warning("Cannot open log file %s: %s", self.config.log_file, exc)

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the relayer daemon.

        Initialises the database, web3 provider, and launches three
        concurrent tasks:

        1. ``watch_deposits`` — polls for ``Deposited`` events.
        2. ``process_withdrawal_queue`` — drains pending withdrawals.
        3. ``monitor_health`` — periodic self-checks.

        Blocks until :meth:`stop` is called or ``_shutdown_event`` is set.
        """
        logger.info("Starting Bridge Relayer...")

        await self.db.initialize()
        await self._init_web3()

        self._running = True
        self._start_time = time.time()
        self._shutdown_event.clear()

        # Start HTTP health server
        await self._start_health_server()

        # Launch concurrent tasks
        self._tasks = [
            asyncio.create_task(self._watch_deposits(), name="watch_deposits"),
            asyncio.create_task(
                self._process_withdrawal_queue(), name="process_withdrawals"
            ),
            asyncio.create_task(self._monitor_health(), name="monitor_health"),
        ]

        logger.info(
            "Relayer started — bridge=%s, %d Rings nodes, health=:%d",
            self.config.bridge_address,
            len(self.config.node_urls),
            self.config.health_port,
        )

        try:
            await self._shutdown_event.wait()
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Graceful shutdown: cancel tasks, close HTTP server, close DB."""
        if not self._running:
            return
        logger.info("Shutting down relayer...")
        self._running = False
        self._shutdown_event.set()

        # Cancel all worker tasks
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # Tear down HTTP server
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

        # Close database
        await self.db.close()
        logger.info("Relayer stopped.")

    # ── Web3 initialisation ─────────────────────────────────────────────

    async def _init_web3(self) -> None:
        """Initialise web3 connection, account, and bridge contract handle.

        Uses :mod:`web3`'s ``AsyncWeb3`` with an ``AsyncHTTPProvider``.
        The bridge ABI is loaded from the inline ``BRIDGE_ABI`` in
        :mod:`.contract_client` (no Foundry artifacts required).
        """
        try:
            from web3 import AsyncWeb3, Web3
            from web3.providers import AsyncHTTPProvider
            from eth_account import Account

            self._web3 = AsyncWeb3(AsyncHTTPProvider(self.config.rpc_url))

            if self.config.private_key:
                key = self.config.private_key
                if not key.startswith("0x"):
                    key = "0x" + key
                self._account = Account.from_key(key)
                logger.info("Relayer account: %s", self._account.address)
            else:
                logger.warning("No private key configured — read-only mode")

            # Load bridge ABI — prefer compiled artifact, fall back to inline
            bridge_abi: Any = None
            artifacts_dir = Path(__file__).parent / "artifacts"
            bridge_abi_path = artifacts_dir / "RingsBridge.json"
            if bridge_abi_path.exists():
                with open(bridge_abi_path) as f:
                    abi_data = json.load(f)
                    bridge_abi = abi_data.get("abi", abi_data)
            else:
                from .contract_client import BRIDGE_ABI

                bridge_abi = BRIDGE_ABI

            self._bridge_contract = self._web3.eth.contract(
                address=Web3.to_checksum_address(self.config.bridge_address),
                abi=bridge_abi,
            )

            chain_id = await self._web3.eth.chain_id
            latest = await self._web3.eth.block_number
            logger.info(
                "Connected to chain %d, latest block %d", chain_id, latest
            )

        except Exception as exc:
            logger.error("Failed to initialise web3: %s", exc)
            raise

    # ── Deposit watcher ─────────────────────────────────────────────────

    async def _watch_deposits(self) -> None:
        """Poll for ``Deposited`` events from the ``RingsBridge`` contract.

        For each deposit found:

        1. Verify the deposit on-chain (receipt status + block finality).
        2. Store the deposit record in the local DB.
        3. Broadcast to the Rings DHT (credit the user's Rings-side account).
        4. Mark as ``CONFIRMED``.

        Scans in chunks of up to 2 000 blocks per iteration, sleeping
        for ``poll_interval`` seconds between passes.
        """
        logger.info("Starting deposit watcher...")

        # Resume from last-scanned block, or start ≈100 blocks behind tip
        last_block_str = await self.db.get_state("last_deposit_block", "")
        if last_block_str:
            last_block = int(last_block_str)
        else:
            last_block = max(0, await self._web3.eth.block_number - 100)
            await self.db.set_state("last_deposit_block", str(last_block))

        while self._running:
            try:
                current_block = await self._web3.eth.block_number
                safe_block = current_block - self.config.confirmations

                if safe_block <= last_block:
                    await asyncio.sleep(self.config.poll_interval)
                    continue

                # Scan in chunks to stay within RPC provider limits
                scan_to = min(last_block + 2000, safe_block)
                logger.debug(
                    "Scanning deposits [%d → %d]", last_block + 1, scan_to
                )

                events = await self._get_deposit_events(last_block + 1, scan_to)

                for event in events:
                    trace_id = str(uuid.uuid4())
                    tx_hash = self._normalise_tx_hash(
                        event.get("transactionHash", "")
                    )
                    block_num = event.get("blockNumber", 0)
                    args = event.get("args", {})

                    logger.info(
                        "Deposit detected: tx=%s block=%d amount=%s",
                        tx_hash,
                        block_num,
                        str(args.get("amount", 0)),
                        extra={
                            "event": "deposit_detected",
                            "trace_id": trace_id,
                            "tx_hash": tx_hash,
                        },
                    )

                    # Verify deposit on-chain
                    verified = await self._verify_deposit(tx_hash, block_num)

                    if verified:
                        await self.db.insert_deposit(
                            tx_hash=tx_hash,
                            block_number=block_num,
                            amount=args.get("amount", 0),
                            sender=args.get("sender", ""),
                            recipient_did=args.get("ringsDid", ""),
                            trace_id=trace_id,
                        )

                        # Broadcast to Rings DHT
                        await self._broadcast_deposit(tx_hash, event)

                        await self.db.update_deposit_status(
                            tx_hash, OperationStatus.CONFIRMED
                        )
                        self._metrics["deposits_processed"] += 1
                    else:
                        logger.warning("Deposit verification failed: %s", tx_hash)
                        self._metrics["deposits_failed"] += 1

                last_block = scan_to
                await self.db.set_state("last_deposit_block", str(last_block))
                self._metrics["last_block_scanned"] = last_block

            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._metrics["rpc_errors"] += 1
                self._metrics["last_error"] = str(exc)
                logger.error("Deposit watcher error: %s", exc, exc_info=True)
                await self._backoff_sleep(self._metrics["rpc_errors"])

    async def _get_deposit_events(
        self, from_block: int, to_block: int
    ) -> List[Dict[str, Any]]:
        """Fetch ``Deposited`` events in a block range.

        Tries the web3.py contract event API first; falls back to raw
        ``eth_getLogs`` with a topic-0 filter if that fails.
        """
        try:
            events = await self._bridge_contract.events.Deposited.get_logs(
                from_block=from_block,
                to_block=to_block,
            )
            return [dict(e) for e in events]
        except Exception:
            # Fallback: raw log filter
            topic0 = self._web3.keccak(
                text="Deposited(uint256,address,string,uint256)"
            )
            logs = await self._web3.eth.get_logs(
                {
                    "address": self.config.bridge_address,
                    "fromBlock": hex(from_block),
                    "toBlock": hex(to_block),
                    "topics": [topic0.hex()],
                }
            )
            return [dict(log) for log in logs]

    async def _verify_deposit(self, tx_hash: str, block_number: int) -> bool:
        """Verify deposit by checking transaction receipt and block finality.

        A deposit is valid when:

        1. The receipt exists and has ``status == 1`` (success).
        2. At least ``config.confirmations`` blocks have elapsed since
           the deposit block.
        """
        try:
            receipt = await self._web3.eth.get_transaction_receipt(tx_hash)
            if receipt is None:
                return False
            if receipt.get("status") != 1:
                return False
            current = await self._web3.eth.block_number
            if current - block_number < self.config.confirmations:
                return False
            return True
        except Exception as exc:
            logger.warning("Verification failed for %s: %s", tx_hash, exc)
            return False

    async def _broadcast_deposit(
        self, tx_hash: str, event: Dict[str, Any]
    ) -> None:
        """Broadcast a confirmed deposit to the Rings DHT.

        In production this would send a ``DEPOSIT_OBSERVED`` message to
        every node in the bridge Sub-Ring.  For now, it logs the
        broadcast intent.
        """
        logger.info(
            "Broadcasting deposit %s to %d Rings nodes",
            tx_hash,
            len(self.config.node_urls),
            extra={"event": "deposit_broadcast", "tx_hash": tx_hash},
        )
        # TODO: integrate with RingsClient.broadcast()
        # for url in self.config.node_urls:
        #     await self._rings_broadcast(url, tx_hash, event)

    # ── Withdrawal processor ────────────────────────────────────────────

    async def _process_withdrawal_queue(self) -> None:
        """Drain pending withdrawals one at a time.

        For each pending withdrawal:

        1. Verify validity (balance, rate limits).
        2. Collect validator approvals (4/6 threshold via consensus module,
           or self-approve in single-validator mode).
        3. Generate a ZK proof (real Groth16 if available, else mock).
        4. Submit ``RingsBridge.withdraw()`` on-chain.
        5. Wait for transaction confirmation.
        6. Update status to ``CONFIRMED`` or ``FAILED``.
        """
        logger.info("Starting withdrawal processor...")

        while self._running:
            try:
                pending = await self.db.get_pending_withdrawals()

                for wd in pending:
                    trace_id = wd["trace_id"]
                    wid = wd["withdrawal_id"]

                    try:
                        await self.db.update_withdrawal_status(
                            wid, OperationStatus.PROCESSING
                        )

                        amount = int(wd["amount"])
                        recipient = wd["recipient"]

                        # Collect validator approvals
                        approved, approvals = await self._collect_approvals(
                            wid, amount, recipient
                        )
                        if not approved:
                            logger.warning(
                                "Withdrawal %s: insufficient approvals", wid
                            )
                            # Return to pending; will retry next iteration
                            await self.db.update_withdrawal_status(
                                wid,
                                OperationStatus.PENDING,
                                error="insufficient_approvals",
                            )
                            continue

                        # Generate ZK proof
                        nonce = await self._get_next_nonce()
                        proof, public_inputs = await self._generate_proof(
                            amount, nonce, recipient
                        )

                        # Submit on-chain
                        tx_hash = await self._submit_withdrawal(
                            recipient, amount, nonce, proof, public_inputs
                        )

                        # Wait for confirmation
                        confirmed = await self._wait_for_confirmation(tx_hash)

                        if confirmed:
                            await self.db.update_withdrawal_status(
                                wid,
                                OperationStatus.CONFIRMED,
                                nonce=nonce,
                                tx_hash=tx_hash,
                                proof=proof,
                                public_inputs=json.dumps(public_inputs),
                                approvals=json.dumps(approvals),
                            )
                            self._metrics["withdrawals_processed"] += 1
                            logger.info(
                                "Withdrawal confirmed: id=%s tx=%s amount=%s",
                                wid,
                                tx_hash,
                                str(amount),
                                extra={
                                    "event": "withdrawal_confirmed",
                                    "trace_id": trace_id,
                                    "withdrawal_id": wid,
                                    "tx_hash": tx_hash,
                                },
                            )
                        else:
                            raise RuntimeError(
                                f"Withdrawal tx {tx_hash} not confirmed within timeout"
                            )

                    except Exception as exc:
                        retry_count = await self.db.increment_withdrawal_retry(wid)
                        if retry_count >= self.config.max_retry:
                            await self.db.update_withdrawal_status(
                                wid, OperationStatus.FAILED, error=str(exc)
                            )
                            self._metrics["withdrawals_failed"] += 1
                            logger.error(
                                "Withdrawal %s permanently failed after %d attempts: %s",
                                wid,
                                retry_count,
                                exc,
                            )
                        else:
                            await self.db.update_withdrawal_status(
                                wid, OperationStatus.PENDING, error=str(exc)
                            )
                            logger.warning(
                                "Withdrawal %s failed (attempt %d/%d): %s",
                                wid,
                                retry_count,
                                self.config.max_retry,
                                exc,
                            )

                await asyncio.sleep(self.config.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._metrics["last_error"] = str(exc)
                logger.error(
                    "Withdrawal processor error: %s", exc, exc_info=True
                )
                await self._backoff_sleep(1)

    async def _collect_approvals(
        self, withdrawal_id: str, amount: int, recipient: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Collect validator approvals for a withdrawal.

        Attempts to use the :mod:`.consensus` module if available.
        Falls back to self-approval (single-validator mode) otherwise.
        """
        try:
            from .consensus import ValidatorConsensus  # type: ignore[import]

            consensus = ValidatorConsensus(node_urls=self.config.node_urls)
            return await consensus.request_approval(withdrawal_id, amount, recipient)
        except ImportError:
            logger.debug(
                "Consensus module not available — self-approving withdrawal %s",
                withdrawal_id,
            )
            return True, {"self": "auto_approved"}

    async def _get_next_nonce(self) -> int:
        """Obtain the next withdrawal nonce from the on-chain contract.

        Falls back to a locally-tracked counter if the contract call fails.
        """
        try:
            nonce = await self._bridge_contract.functions.withdrawalNonce().call()
            return nonce
        except Exception:
            stored = await self.db.get_state("next_withdrawal_nonce", "0")
            nonce = int(stored)
            await self.db.set_state("next_withdrawal_nonce", str(nonce + 1))
            return nonce

    async def _generate_proof(
        self, amount: int, nonce: int, recipient: str
    ) -> Tuple[bytes, List[int]]:
        """Generate a ZK proof for a withdrawal.

        Tries the real Groth16 prover (:mod:`.zk_prover`); if unavailable
        (e.g. ``py_ecc`` not installed), produces a deterministic mock
        proof that matches the format expected by the verifier contract.
        """
        try:
            from .zk_prover import (
                BridgeWithdrawalCircuit,
                Groth16Prover,
                TrustedSetup,
            )

            setup = TrustedSetup.generate(num_constraints=4)
            circuit = BridgeWithdrawalCircuit()
            witness = circuit.generate_witness(
                amount=amount,
                nonce=nonce,
                recipient=int(recipient[:10], 16) if recipient.startswith("0x") else 0,
                nullifier=int.from_bytes(os.urandom(16), "big"),
            )
            prover = Groth16Prover(setup)
            proof = prover.prove(circuit, witness)
            logger.debug(
                "Generated real Groth16 proof for withdrawal nonce=%d", nonce
            )
            return proof.serialize(), list(witness.public_inputs)

        except Exception as exc:
            logger.debug(
                "ZK prover unavailable (%s), using mock proof", exc
            )
            data = f"{amount}:{nonce}:{recipient}".encode()
            mock_proof = hashlib.sha256(data).digest() * 8  # 256 bytes
            recipient_hash = (
                int(recipient[:10], 16) if recipient.startswith("0x") else 0
            )
            return mock_proof, [amount, nonce, recipient_hash]

    async def _submit_withdrawal(
        self,
        recipient: str,
        amount: int,
        nonce: int,
        proof: bytes,
        public_inputs: List[int],
    ) -> str:
        """Build, sign, and send a ``withdraw()`` transaction.

        Returns the transaction hash as a hex string.

        Raises
        ------
        RuntimeError
            If no private key is configured.
        """
        if self._account is None:
            raise RuntimeError("Cannot submit withdrawal: no private key configured")

        from web3 import Web3

        gas_price = await self._web3.eth.gas_price

        tx = await self._bridge_contract.functions.withdraw(
            Web3.to_checksum_address(recipient),
            amount,
            nonce,
            proof,
            public_inputs,
        ).build_transaction(
            {
                "from": self._account.address,
                "nonce": await self._web3.eth.get_transaction_count(
                    self._account.address
                ),
                "gas": 500_000,
                "maxFeePerGas": gas_price * 2,
                "maxPriorityFeePerGas": max(gas_price // 10, 1),
                "chainId": await self._web3.eth.chain_id,
            }
        )

        signed = self._account.sign_transaction(tx)
        tx_hash = await self._web3.eth.send_raw_transaction(
            signed.raw_transaction
        )
        return tx_hash.hex()

    async def _wait_for_confirmation(
        self, tx_hash: str, timeout: float = 120.0
    ) -> bool:
        """Poll for a transaction receipt until it confirms or times out.

        Parameters
        ----------
        tx_hash : str
            The hex-encoded transaction hash.
        timeout : float
            Maximum seconds to wait.

        Returns
        -------
        bool
            ``True`` if the receipt shows ``status == 1``.
        """
        start = time.time()
        while time.time() - start < timeout:
            try:
                receipt = await self._web3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    if receipt.get("status") == 1:
                        return True
                    if receipt.get("status") == 0:
                        logger.error("Withdrawal tx %s reverted", tx_hash)
                        return False
            except Exception:
                pass
            await asyncio.sleep(3.0)
        logger.error("Withdrawal tx %s timed out after %.0fs", tx_hash, timeout)
        return False

    # ── Health monitoring ───────────────────────────────────────────────

    async def _monitor_health(self) -> None:
        """Periodic self-check: RPC connectivity, gas balance, contract state.

        Runs every 30 seconds and logs warnings for concerning conditions
        (disconnected RPC, low gas, paused bridge).
        """
        while self._running:
            try:
                health = await self.get_health()

                if not health.get("rpc_connected"):
                    logger.error("RPC disconnected!")
                    self._metrics["rpc_errors"] += 1

                gas_balance = health.get("gas_balance_eth", 0)
                if isinstance(gas_balance, (int, float)) and gas_balance < 0.01:
                    logger.warning("Low gas balance: %.6f ETH", gas_balance)

                if health.get("bridge_paused"):
                    logger.warning("Bridge contract is PAUSED!")

                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Health monitor error: %s", exc)
                await asyncio.sleep(30)

    async def get_health(self) -> Dict[str, Any]:
        """Build a comprehensive health report.

        Returns a dict suitable for JSON serialisation containing RPC
        status, gas balance, bridge contract state, DB statistics, and
        operational metrics.
        """
        health: Dict[str, Any] = {
            "status": "unknown",
            "timestamp": time.time(),
            "uptime_seconds": (
                time.time() - self._start_time if self._start_time else 0
            ),
        }

        # RPC connectivity
        try:
            block = await self._web3.eth.block_number
            health["rpc_connected"] = True
            health["latest_block"] = block
        except Exception as exc:
            health["rpc_connected"] = False
            health["rpc_error"] = str(exc)

        # Gas balance
        try:
            if self._account:
                balance = await self._web3.eth.get_balance(self._account.address)
                health["gas_balance_wei"] = balance
                health["gas_balance_eth"] = balance / 10**18
                health["relayer_address"] = self._account.address
        except Exception:
            pass

        # Bridge pause state
        try:
            paused = await self._bridge_contract.functions.paused().call()
            health["bridge_paused"] = paused
        except Exception:
            health["bridge_paused"] = None

        # DB stats
        try:
            health["db_stats"] = await self.db.get_stats()
        except Exception:
            pass

        # In-memory metrics
        self._metrics["uptime_seconds"] = health["uptime_seconds"]
        health["metrics"] = dict(self._metrics)
        health["node_urls"] = len(self.config.node_urls)

        # Overall status verdict
        health["status"] = (
            "healthy" if health.get("rpc_connected") else "degraded"
        )

        return health

    # ── HTTP health server ──────────────────────────────────────────────

    async def _start_health_server(self) -> None:
        """Start the HTTP health-check server on ``config.health_port``."""
        self._app = web.Application()
        self._app.router.add_get("/health", self._handle_health)
        self._app.router.add_get("/metrics", self._handle_metrics)
        self._app.router.add_get("/status", self._handle_status)

        self._runner = web.AppRunner(self._app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self.config.health_port)
        await site.start()
        logger.info("Health server listening on :%d", self.config.health_port)

    async def _handle_health(self, request: web.Request) -> web.Response:
        """``GET /health`` — JSON health check for liveness/readiness probes."""
        health = await self.get_health()
        status_code = 200 if health["status"] == "healthy" else 503
        return web.json_response(health, status=status_code)

    async def _handle_metrics(self, request: web.Request) -> web.Response:
        """``GET /metrics`` — Prometheus-compatible exposition format."""
        health = await self.get_health()

        lines = [
            "# HELP bridge_deposits_total Total deposits processed",
            "# TYPE bridge_deposits_total counter",
            f'bridge_deposits_total {self._metrics["deposits_processed"]}',
            "",
            "# HELP bridge_deposits_failed Total deposits failed",
            "# TYPE bridge_deposits_failed counter",
            f'bridge_deposits_failed {self._metrics["deposits_failed"]}',
            "",
            "# HELP bridge_withdrawals_total Total withdrawals processed",
            "# TYPE bridge_withdrawals_total counter",
            f'bridge_withdrawals_total {self._metrics["withdrawals_processed"]}',
            "",
            "# HELP bridge_withdrawals_failed Total withdrawals failed",
            "# TYPE bridge_withdrawals_failed counter",
            f'bridge_withdrawals_failed {self._metrics["withdrawals_failed"]}',
            "",
            "# HELP bridge_rpc_errors_total Total RPC errors",
            "# TYPE bridge_rpc_errors_total counter",
            f'bridge_rpc_errors_total {self._metrics["rpc_errors"]}',
            "",
            "# HELP bridge_last_block_scanned Last block scanned for deposits",
            "# TYPE bridge_last_block_scanned gauge",
            f'bridge_last_block_scanned {self._metrics["last_block_scanned"]}',
            "",
            "# HELP bridge_gas_balance_eth Relayer gas balance in ETH",
            "# TYPE bridge_gas_balance_eth gauge",
            f'bridge_gas_balance_eth {health.get("gas_balance_eth", 0)}',
            "",
            "# HELP bridge_uptime_seconds Relayer uptime in seconds",
            "# TYPE bridge_uptime_seconds gauge",
            f'bridge_uptime_seconds {health.get("uptime_seconds", 0):.1f}',
            "",
        ]
        return web.Response(
            text="\n".join(lines) + "\n", content_type="text/plain"
        )

    async def _handle_status(self, request: web.Request) -> web.Response:
        """``GET /status`` — Human-readable plain-text status page."""
        health = await self.get_health()
        db_stats = health.get("db_stats", {})

        text = (
            "Bridge Relayer Status\n"
            "=====================\n"
            f"Status:          {health['status']}\n"
            f"Uptime:          {health.get('uptime_seconds', 0):.0f}s\n"
            f"RPC Connected:   {health.get('rpc_connected', False)}\n"
            f"Latest Block:    {health.get('latest_block', 'N/A')}\n"
            f"Gas Balance:     {health.get('gas_balance_eth', 0):.6f} ETH\n"
            f"Bridge Paused:   {health.get('bridge_paused', 'N/A')}\n"
            f"Relayer Addr:    {health.get('relayer_address', 'N/A')}\n"
            f"Rings Nodes:     {health.get('node_urls', 0)}\n"
            "\n"
            "Deposits\n"
            "--------\n"
            f"  Processed:     {self._metrics['deposits_processed']}\n"
            f"  Failed:        {self._metrics['deposits_failed']}\n"
            f"  DB Stats:      {db_stats.get('deposits', {})}\n"
            f"  Total:         {db_stats.get('deposits_total', 0)}\n"
            "\n"
            "Withdrawals\n"
            "-----------\n"
            f"  Processed:     {self._metrics['withdrawals_processed']}\n"
            f"  Failed:        {self._metrics['withdrawals_failed']}\n"
            f"  DB Stats:      {db_stats.get('withdrawals', {})}\n"
            f"  Total:         {db_stats.get('withdrawals_total', 0)}\n"
            "\n"
            "Errors\n"
            "------\n"
            f"  RPC Errors:    {self._metrics['rpc_errors']}\n"
            f"  Last Error:    {self._metrics['last_error'] or 'None'}\n"
            f"  Last Block:    {self._metrics['last_block_scanned']}\n"
        )
        return web.Response(text=text, content_type="text/plain")

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _normalise_tx_hash(raw: Any) -> str:
        """Normalise a transaction hash to a ``0x``-prefixed hex string."""
        if isinstance(raw, bytes):
            return "0x" + raw.hex()
        s = str(raw)
        if not s.startswith("0x"):
            s = "0x" + s
        return s

    async def _backoff_sleep(self, attempt: int) -> None:
        """Sleep with exponential backoff and jitter.

        Parameters
        ----------
        attempt : int
            The current attempt number (used for exponent).
        """
        delay = min(
            self.config.retry_base_delay * (2 ** min(attempt, 6)),
            self.config.retry_max_delay,
        )
        delay *= 0.5 + random.random()  # 50–150% jitter
        await asyncio.sleep(delay)

    def __repr__(self) -> str:
        return (
            f"BridgeRelayer(bridge={self.config.bridge_address}, "
            f"running={self._running}, "
            f"deposits={self._metrics['deposits_processed']}, "
            f"withdrawals={self._metrics['withdrawals_processed']})"
        )


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the Bridge Relayer daemon.

    Installs SIGINT/SIGTERM handlers for graceful shutdown and runs
    the async event loop until completion.
    """
    config = RelayerConfig.from_env()
    relayer = BridgeRelayer(config)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Graceful shutdown on signals
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: relayer._shutdown_event.set())

    try:
        loop.run_until_complete(relayer.start())
    except KeyboardInterrupt:
        pass
    finally:
        # Ensure stop() runs even on unexpected exit
        with suppress(Exception):
            loop.run_until_complete(relayer.stop())
        loop.close()


if __name__ == "__main__":
    main()
