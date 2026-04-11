"""
Bi-temporal Knowledge Graph with Provenance Tracking
=====================================================
Contributed by MemPalace-AGI (https://github.com/milla-jovovich/mempalace)

A standalone, SQLite-backed knowledge graph designed for autonomous research
systems. Stores entity-relationship triples with:

- **Bi-temporal validity**: ``valid_at`` (when the fact became true in the world)
  and ``invalid_at`` (when it ceased being true). Separate from *recording* time.
- **Provenance chain**: who asserted the triple, from what source, with what
  confidence, and how confidence evolved over time.
- **Statement classification**: observation, inference, hypothesis, or fact —
  with temporal type (static event, dynamic/ongoing, atemporal law).
- **Contradiction detection**: automatically finds conflicting triples (same
  subject + predicate, different object) and resolves by invalidating the
  weaker assertion.
- **Pheromone-based stigmergic learning**: three pheromone channels on each
  triple (success, traversal, recency) that guide pathfinding toward
  high-value edges.

All operations use parameterized queries and WAL journaling for safety.
Thread-safe (``check_same_thread=False``).

No external dependencies — only the Python standard library (``sqlite3``,
``uuid``, ``json``, ``datetime``, ``logging``).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Pheromone defaults (from STAN_X v8 SPEC.md FR-014) ────────────────

DEFAULT_DECAY_RATES: Dict[str, float] = {
    "success": 0.03,  # slow decay — marks confirmed paths
    "traversal": 0.08,  # moderate — general usage tracking
    "recency": 0.15,  # fast decay — recent-access signal
}

PHEROMONE_CHANNELS = ("success", "traversal", "recency")


def _utcnow_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _new_id() -> str:
    """Generate a 12-char hex ID for a triple."""
    return uuid.uuid4().hex[:12]


class TemporalKnowledgeGraph:
    """SQLite-backed bi-temporal knowledge graph with provenance.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file. Use ``":memory:"`` for in-memory.
    """

    # ── Initialisation ─────────────────────────────────────────────────

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(
            db_path,
            timeout=10,
            check_same_thread=False,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.row_factory = sqlite3.Row
        self._create_schema()
        logger.info("TemporalKnowledgeGraph initialised (db=%s)", db_path)

    def _create_schema(self) -> None:
        """Create tables if they don't already exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS triples (
                id              TEXT PRIMARY KEY,
                subject         TEXT NOT NULL,
                predicate       TEXT NOT NULL,
                object          TEXT NOT NULL,
                source          TEXT NOT NULL DEFAULT '',
                confidence      REAL NOT NULL DEFAULT 1.0,
                valid_at        TEXT DEFAULT NULL,
                invalid_at      TEXT DEFAULT NULL,
                created_at      TEXT NOT NULL,
                expired_at      TEXT DEFAULT NULL,
                statement_type  TEXT NOT NULL DEFAULT 'fact',
                temporal_type   TEXT NOT NULL DEFAULT 'static',
                -- pheromone channels
                pheromone_success   REAL NOT NULL DEFAULT 0.0,
                pheromone_traversal REAL NOT NULL DEFAULT 0.0,
                pheromone_recency   REAL NOT NULL DEFAULT 0.0
            );

            CREATE INDEX IF NOT EXISTS idx_triples_subject
                ON triples(subject);
            CREATE INDEX IF NOT EXISTS idx_triples_object
                ON triples(object);
            CREATE INDEX IF NOT EXISTS idx_triples_predicate
                ON triples(predicate);
            CREATE INDEX IF NOT EXISTS idx_triples_valid
                ON triples(valid_at, invalid_at);

            CREATE TABLE IF NOT EXISTS triple_provenance (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                triple_id       TEXT NOT NULL,
                agent           TEXT NOT NULL DEFAULT '',
                source          TEXT NOT NULL DEFAULT '',
                confidence      REAL NOT NULL DEFAULT 1.0,
                valid_at        TEXT DEFAULT NULL,
                invalid_at      TEXT DEFAULT NULL,
                recorded_at     TEXT NOT NULL,
                reason          TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (triple_id) REFERENCES triples(id)
            );

            CREATE INDEX IF NOT EXISTS idx_provenance_triple
                ON triple_provenance(triple_id);
        """)
        self._conn.commit()

    # ── Connection helper ──────────────────────────────────────────────

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # ── Triple CRUD ────────────────────────────────────────────────────

    def add_triple(
        self,
        subject: str,
        predicate: str,
        object: str,  # noqa: A002 — shadows builtin intentionally
        source: str = "",
        confidence: float = 1.0,
        agent: str = "",
        statement_type: str = "fact",
        temporal_type: str = "static",
        valid_at: Optional[str] = None,
    ) -> str:
        """Add a new triple to the knowledge graph.

        Parameters
        ----------
        subject : str
            Entity that is the subject of the relationship.
        predicate : str
            The relationship type (e.g. ``"causes"``, ``"correlated_with"``).
        object : str
            Entity that is the object of the relationship.
        source : str
            Free-text provenance label (e.g. ``"causal_inference"``).
        confidence : float
            Confidence score in ``[0, 1]``.
        agent : str
            Identifier of the agent/system that asserted this triple.
        statement_type : str
            One of ``"fact"``, ``"observation"``, ``"inference"``,
            ``"hypothesis"``.
        temporal_type : str
            One of ``"static"`` (single event), ``"dynamic"`` (ongoing),
            ``"atemporal"`` (universal law).
        valid_at : str or None
            ISO-8601 timestamp for when the fact became true. Defaults to
            the current time.

        Returns
        -------
        str
            The newly created triple ID (12-char hex).
        """
        triple_id = _new_id()
        now = _utcnow_iso()
        effective_valid = valid_at or now

        # Normalise entities to lowercase with underscores
        norm_subject = self._normalise(subject)
        norm_object = self._normalise(object)

        self._conn.execute(
            """INSERT INTO triples
               (id, subject, predicate, object, source, confidence,
                valid_at, created_at, statement_type, temporal_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                triple_id,
                norm_subject,
                predicate,
                norm_object,
                source,
                confidence,
                effective_valid,
                now,
                statement_type,
                temporal_type,
            ),
        )

        # Record provenance entry
        self._conn.execute(
            """INSERT INTO triple_provenance
               (triple_id, agent, source, confidence, valid_at, recorded_at, reason)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                triple_id,
                agent,
                source,
                confidence,
                effective_valid,
                now,
                "Initial assertion",
            ),
        )

        self._conn.commit()

        logger.debug(
            "Added triple %s: %s %s %s (conf=%.2f, type=%s)",
            triple_id,
            norm_subject,
            predicate,
            norm_object,
            confidence,
            statement_type,
        )
        return triple_id

    def get_triples(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[str] = None,  # noqa: A002
        current_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Query triples with optional filters.

        Parameters
        ----------
        subject : str or None
            Filter by subject entity.
        predicate : str or None
            Filter by predicate.
        object : str or None
            Filter by object entity.
        current_only : bool
            If True (default), exclude invalidated triples.

        Returns
        -------
        list of dict
            Matching triples as dictionaries.
        """
        conditions: List[str] = []
        params: List[Any] = []

        if subject is not None:
            conditions.append("subject = ?")
            params.append(self._normalise(subject))
        if predicate is not None:
            conditions.append("predicate = ?")
            params.append(predicate)
        if object is not None:
            conditions.append("object = ?")
            params.append(self._normalise(object))
        if current_only:
            conditions.append("invalid_at IS NULL")

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        rows = self._conn.execute(
            f"SELECT * FROM triples {where} ORDER BY created_at DESC",
            params,
        ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def invalidate_triple(
        self,
        triple_id: str,
        reason: str = "",
        agent: str = "",
    ) -> None:
        """Mark a triple as no longer valid.

        Sets ``invalid_at`` to the current time and records a provenance
        entry with zero confidence. Does **not** delete — the full temporal
        history is preserved.

        Parameters
        ----------
        triple_id : str
            The triple to invalidate.
        reason : str
            Human-readable reason for invalidation.
        agent : str
            Identifier of the invalidating agent.
        """
        now = _utcnow_iso()

        self._conn.execute(
            "UPDATE triples SET invalid_at = ?, expired_at = ? WHERE id = ?",
            (now, now, triple_id),
        )

        self._conn.execute(
            """INSERT INTO triple_provenance
               (triple_id, agent, source, confidence, invalid_at, recorded_at, reason)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                triple_id,
                agent,
                "invalidation",
                0.0,
                now,
                now,
                reason or "Triple invalidated",
            ),
        )

        self._conn.commit()
        logger.debug("Invalidated triple %s: %s", triple_id, reason)

    def update_confidence(
        self,
        triple_id: str,
        new_confidence: float,
        reason: str = "",
        agent: str = "",
    ) -> None:
        """Update the confidence score of a triple and record the change.

        Parameters
        ----------
        triple_id : str
            The triple to update.
        new_confidence : float
            New confidence in ``[0, 1]``.
        reason : str
            Why the confidence changed.
        agent : str
            Who made the change.
        """
        now = _utcnow_iso()

        self._conn.execute(
            "UPDATE triples SET confidence = ? WHERE id = ?",
            (new_confidence, triple_id),
        )

        self._conn.execute(
            """INSERT INTO triple_provenance
               (triple_id, agent, source, confidence, recorded_at, reason)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                triple_id,
                agent,
                "confidence_update",
                new_confidence,
                now,
                reason or f"Confidence updated to {new_confidence:.3f}",
            ),
        )

        self._conn.commit()
        logger.debug("Updated confidence for %s to %.3f", triple_id, new_confidence)

    # ── Contradiction Detection and Resolution ─────────────────────────

    def detect_contradictions(
        self,
        subject: str,
        predicate: str,
        new_object: str,
        new_confidence: float,
    ) -> List[Dict[str, Any]]:
        """Find existing triples that contradict a proposed assertion.

        A contradiction exists when there's an active triple with the same
        ``subject`` and ``predicate`` but a different ``object``.

        Parameters
        ----------
        subject : str
            Subject of the proposed triple.
        predicate : str
            Predicate of the proposed triple.
        new_object : str
            Object of the proposed triple.
        new_confidence : float
            Confidence of the proposed triple.

        Returns
        -------
        list of dict
            Each dict has keys ``triple_id``, ``subject``, ``predicate``,
            ``object``, ``confidence``, and ``dominated`` (bool — True if the
            existing triple has lower confidence than the proposed one).
        """
        norm_subject = self._normalise(subject)
        norm_object = self._normalise(new_object)

        rows = self._conn.execute(
            """SELECT * FROM triples
               WHERE subject = ? AND predicate = ?
                 AND object != ?
                 AND invalid_at IS NULL""",
            (norm_subject, predicate, norm_object),
        ).fetchall()

        conflicts = []
        for row in rows:
            old_conf = float(row["confidence"]) if row["confidence"] else 0.0
            conflicts.append(
                {
                    "triple_id": row["id"],
                    "subject": row["subject"],
                    "predicate": row["predicate"],
                    "object": row["object"],
                    "confidence": old_conf,
                    "dominated": new_confidence > old_conf,
                }
            )

        return conflicts

    def resolve_contradictions(
        self,
        subject: str,
        predicate: str,
        new_object: str,
        new_confidence: float,
        source: str = "",
        agent: str = "",
    ) -> Dict[str, Any]:
        """Detect contradictions and auto-invalidate weaker triples.

        Finds all active triples with the same subject/predicate but a
        different object. Those with confidence strictly less than
        ``new_confidence`` are invalidated. Then the new triple is added.

        Parameters
        ----------
        subject, predicate, new_object, new_confidence, source, agent
            Same as ``add_triple``.

        Returns
        -------
        dict
            Keys: ``new_triple_id`` (the added triple), ``invalidated``
            (list of IDs that were invalidated), ``kept`` (list of IDs that
            had equal or higher confidence).
        """
        conflicts = self.detect_contradictions(
            subject,
            predicate,
            new_object,
            new_confidence,
        )

        invalidated: List[str] = []
        kept: List[str] = []

        for conflict in conflicts:
            if conflict["dominated"]:
                reason = (
                    f"Contradiction: '{subject} {predicate} {new_object}' "
                    f"(conf={new_confidence:.2f}) supersedes "
                    f"'{conflict['object']}' (conf={conflict['confidence']:.2f})"
                )
                self.invalidate_triple(
                    triple_id=conflict["triple_id"],
                    reason=reason,
                    agent="contradiction_resolver",
                )
                invalidated.append(conflict["triple_id"])
                logger.warning(
                    "Invalidated contradictory triple %s: %s",
                    conflict["triple_id"],
                    reason,
                )
            else:
                kept.append(conflict["triple_id"])

        new_id = self.add_triple(
            subject=subject,
            predicate=predicate,
            object=new_object,
            source=source,
            confidence=new_confidence,
            agent=agent,
        )

        return {
            "new_triple_id": new_id,
            "invalidated": invalidated,
            "kept": kept,
        }

    # ── Temporal Queries ───────────────────────────────────────────────

    def get_temporal_history(
        self,
        subject: str,
        predicate: str,
    ) -> List[Dict[str, Any]]:
        """Return all versions of a (subject, predicate) pair, ordered by time.

        Includes both valid and invalidated triples to show full evolution.

        Parameters
        ----------
        subject : str
            Subject entity.
        predicate : str
            Predicate to filter by.

        Returns
        -------
        list of dict
            All triples matching (subject, predicate), ordered by
            ``created_at`` ascending.
        """
        norm_subject = self._normalise(subject)
        rows = self._conn.execute(
            """SELECT * FROM triples
               WHERE subject = ? AND predicate = ?
               ORDER BY created_at ASC""",
            (norm_subject, predicate),
        ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def get_valid_at(
        self,
        point_in_time: str,
    ) -> List[Dict[str, Any]]:
        """Return triples that were valid at a specific point in time.

        A triple is valid at time *t* if:
        - ``valid_at <= t`` (it had started being true), AND
        - ``invalid_at IS NULL`` OR ``invalid_at > t`` (it hadn't been
          invalidated yet).

        Parameters
        ----------
        point_in_time : str
            ISO-8601 timestamp to query.

        Returns
        -------
        list of dict
        """
        rows = self._conn.execute(
            """SELECT * FROM triples
               WHERE valid_at IS NOT NULL
                 AND valid_at <= ?
                 AND (invalid_at IS NULL OR invalid_at > ?)
               ORDER BY valid_at ASC""",
            (point_in_time, point_in_time),
        ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def get_entity_relations(
        self,
        entity: str,
    ) -> List[Dict[str, Any]]:
        """Get all active triples involving an entity as subject or object.

        Parameters
        ----------
        entity : str
            Entity name to search for.

        Returns
        -------
        list of dict
        """
        norm = self._normalise(entity)
        rows = self._conn.execute(
            """SELECT * FROM triples
               WHERE (subject = ? OR object = ?)
                 AND invalid_at IS NULL
               ORDER BY created_at DESC""",
            (norm, norm),
        ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def get_provenance(
        self,
        triple_id: str,
    ) -> List[Dict[str, Any]]:
        """Return the full provenance chain for a triple.

        Parameters
        ----------
        triple_id : str
            The triple to look up.

        Returns
        -------
        list of dict
            Provenance records ordered by ``recorded_at`` ascending.
        """
        rows = self._conn.execute(
            """SELECT * FROM triple_provenance
               WHERE triple_id = ?
               ORDER BY recorded_at ASC""",
            (triple_id,),
        ).fetchall()

        return [
            {
                "id": row["id"],
                "triple_id": row["triple_id"],
                "agent": row["agent"],
                "source": row["source"],
                "confidence": row["confidence"],
                "valid_at": row["valid_at"],
                "invalid_at": row["invalid_at"],
                "recorded_at": row["recorded_at"],
                "reason": row["reason"],
            }
            for row in rows
        ]

    def search_triples(
        self,
        text_query: str,
        current_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Simple text search across subject, predicate, and object.

        Uses SQL ``LIKE`` with wildcards. For semantic search, use the
        :class:`KGPathfinder` with an embedding function instead.

        Parameters
        ----------
        text_query : str
            Text to search for (case-insensitive, substring match).
        current_only : bool
            If True (default), exclude invalidated triples.

        Returns
        -------
        list of dict
        """
        pattern = f"%{text_query.lower()}%"
        validity = "AND invalid_at IS NULL" if current_only else ""

        rows = self._conn.execute(
            f"""SELECT * FROM triples
                WHERE (subject LIKE ? OR predicate LIKE ? OR object LIKE ?)
                {validity}
                ORDER BY created_at DESC""",
            (pattern, pattern, pattern),
        ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    # ── Statistics ─────────────────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """Return summary statistics about the knowledge graph.

        Returns
        -------
        dict
            Keys: ``total_triples``, ``active_triples``,
            ``invalidated_triples``, ``unique_subjects``,
            ``unique_objects``, ``unique_entities``,
            ``unique_predicates``, ``statement_types`` (dict of counts),
            ``avg_confidence``.
        """
        total = self._scalar("SELECT COUNT(*) FROM triples")
        active = self._scalar("SELECT COUNT(*) FROM triples WHERE invalid_at IS NULL")
        invalidated = total - active
        subjects = self._scalar("SELECT COUNT(DISTINCT subject) FROM triples")
        objects = self._scalar("SELECT COUNT(DISTINCT object) FROM triples")
        predicates = self._scalar("SELECT COUNT(DISTINCT predicate) FROM triples")

        # Unique entities = union of subjects and objects
        entities = self._scalar("""SELECT COUNT(*) FROM (
                   SELECT subject AS entity FROM triples
                   UNION
                   SELECT object AS entity FROM triples
               )""")

        avg_conf = (
            self._scalar("SELECT AVG(confidence) FROM triples WHERE invalid_at IS NULL") or 0.0
        )

        # Statement type breakdown
        type_rows = self._conn.execute("""SELECT statement_type, COUNT(*) as cnt
               FROM triples
               WHERE invalid_at IS NULL
               GROUP BY statement_type""").fetchall()
        statement_types = {row["statement_type"]: row["cnt"] for row in type_rows}

        return {
            "total_triples": total,
            "active_triples": active,
            "invalidated_triples": invalidated,
            "unique_subjects": subjects,
            "unique_objects": objects,
            "unique_entities": entities,
            "unique_predicates": predicates,
            "statement_types": statement_types,
            "avg_confidence": round(avg_conf, 4),
        }

    # ── Pheromone System ───────────────────────────────────────────────

    def deposit_pheromone(
        self,
        triple_id: str,
        channel: str,
        amount: float = 1.0,
    ) -> None:
        """Add pheromone to a specific channel of a triple.

        Parameters
        ----------
        triple_id : str
            The triple to deposit on.
        channel : str
            One of ``"success"``, ``"traversal"``, ``"recency"``.
        amount : float
            Amount to add (default 1.0).

        Raises
        ------
        ValueError
            If *channel* is not a valid pheromone channel.
        """
        if channel not in PHEROMONE_CHANNELS:
            raise ValueError(
                f"Invalid pheromone channel '{channel}'. " f"Must be one of {PHEROMONE_CHANNELS}"
            )

        col = f"pheromone_{channel}"
        self._conn.execute(
            f"UPDATE triples SET {col} = {col} + ? WHERE id = ?",
            (amount, triple_id),
        )
        self._conn.commit()
        logger.debug(
            "Deposited %.2f %s pheromone on triple %s",
            amount,
            channel,
            triple_id,
        )

    def deposit_path_pheromone(
        self,
        triple_ids: List[str],
        channel: str = "success",
        total_amount: float = 1.0,
    ) -> None:
        """Deposit position-weighted pheromone along a path.

        Triples earlier in the path receive more pheromone. Weight for
        position *i* in a path of length *n*:
        ``w_i = (n - i) / sum(1..n)``

        Parameters
        ----------
        triple_ids : list of str
            Ordered triple IDs along the path.
        channel : str
            Pheromone channel (default ``"success"``).
        total_amount : float
            Total pheromone to distribute (default 1.0).
        """
        n = len(triple_ids)
        if n == 0:
            return

        weight_sum = n * (n + 1) / 2.0
        for i, tid in enumerate(triple_ids):
            weight = (n - i) / weight_sum
            self.deposit_pheromone(tid, channel, amount=total_amount * weight)

    def decay_pheromones(
        self,
        channel: str,
        rate: Optional[float] = None,
    ) -> int:
        """Apply exponential decay to a pheromone channel across all triples.

        Decay formula: ``τ(t+1) = τ(t) × (1 − ρ)``

        Parameters
        ----------
        channel : str
            One of ``"success"``, ``"traversal"``, ``"recency"``.
        rate : float or None
            Decay rate ρ. If None, uses the default for the channel.

        Returns
        -------
        int
            Number of triples that had non-zero pheromone and were decayed.

        Raises
        ------
        ValueError
            If *channel* is not a valid pheromone channel.
        """
        if channel not in PHEROMONE_CHANNELS:
            raise ValueError(
                f"Invalid pheromone channel '{channel}'. " f"Must be one of {PHEROMONE_CHANNELS}"
            )

        rho = rate if rate is not None else DEFAULT_DECAY_RATES[channel]
        col = f"pheromone_{channel}"
        factor = 1.0 - rho

        cursor = self._conn.execute(
            f"UPDATE triples SET {col} = {col} * ? WHERE {col} > 0",
            (factor,),
        )
        self._conn.commit()

        affected = cursor.rowcount
        logger.debug(
            "Decayed %s pheromone (ρ=%.3f) on %d triples",
            channel,
            rho,
            affected,
        )
        return affected

    def get_pheromone_modifier(self, triple_id: str) -> float:
        """Compute the pheromone-based cost modifier for a triple.

        Formula (from STAN_X v8):
            ``modifier = 1.0 - (0.5·s + 0.3·r + 0.2·t) × 0.5``
        where s, r, t are clamped to [0, 1].

        A modifier < 1 means the edge is "cheaper" to traverse.

        Parameters
        ----------
        triple_id : str
            The triple to compute the modifier for.

        Returns
        -------
        float
            Modifier in ``[0.5, 1.0]``. Returns 1.0 if triple not found.
        """
        row = self._conn.execute(
            """SELECT pheromone_success, pheromone_traversal, pheromone_recency
               FROM triples WHERE id = ?""",
            (triple_id,),
        ).fetchone()

        if row is None:
            return 1.0

        s = min(1.0, max(0.0, float(row["pheromone_success"])))
        t = min(1.0, max(0.0, float(row["pheromone_traversal"])))
        r = min(1.0, max(0.0, float(row["pheromone_recency"])))

        weighted = 0.5 * s + 0.3 * r + 0.2 * t
        modifier = 1.0 - weighted * 0.5

        return modifier

    def get_pheromone_stats(self) -> Dict[str, Dict[str, float]]:
        """Return aggregate pheromone statistics per channel.

        Returns
        -------
        dict
            Keyed by channel name, each with ``min``, ``max``, ``avg``,
            ``nonzero_count``.
        """
        stats: Dict[str, Dict[str, float]] = {}
        for ch in PHEROMONE_CHANNELS:
            col = f"pheromone_{ch}"
            row = self._conn.execute(f"""SELECT
                        MIN({col}) as mn,
                        MAX({col}) as mx,
                        AVG({col}) as av,
                        SUM(CASE WHEN {col} > 0 THEN 1 ELSE 0 END) as nz
                    FROM triples""").fetchone()
            stats[ch] = {
                "min": float(row["mn"]) if row["mn"] is not None else 0.0,
                "max": float(row["mx"]) if row["mx"] is not None else 0.0,
                "avg": float(row["av"]) if row["av"] is not None else 0.0,
                "nonzero_count": int(row["nz"]) if row["nz"] is not None else 0,
            }
        return stats

    # ── Internal Helpers ───────────────────────────────────────────────

    @staticmethod
    def _normalise(entity: str) -> str:
        """Normalise an entity name for consistent storage and lookup.

        - Lowercase
        - Spaces → underscores
        - Apostrophes removed
        """
        return entity.lower().replace(" ", "_").replace("'", "")

    def _scalar(self, sql: str, params: tuple = ()) -> Any:
        """Execute a query and return the first column of the first row."""
        row = self._conn.execute(sql, params).fetchone()
        return row[0] if row else None

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a ``triples`` table row to a dictionary."""
        return {
            "triple_id": row["id"],
            "subject": row["subject"],
            "predicate": row["predicate"],
            "object": row["object"],
            "source": row["source"],
            "confidence": row["confidence"],
            "valid_at": row["valid_at"],
            "invalid_at": row["invalid_at"],
            "created_at": row["created_at"],
            "expired_at": row["expired_at"],
            "statement_type": row["statement_type"],
            "temporal_type": row["temporal_type"],
            "pheromone_success": row["pheromone_success"],
            "pheromone_traversal": row["pheromone_traversal"],
            "pheromone_recency": row["pheromone_recency"],
        }

    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (
            f"<TemporalKnowledgeGraph "
            f"triples={stats['total_triples']} "
            f"active={stats['active_triples']} "
            f"entities={stats['unique_entities']}>"
        )
