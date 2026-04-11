#!/usr/bin/env python3
"""
Demonstrate the bi-temporal knowledge graph:
- Create entities and relationships (triples)
- Query at different points in time
- Detect contradictions
- Find paths between entities

This uses the MemPalace-AGI knowledge graph bridge, which stores
temporal entity-relationship triples in SQLite (no external services).

Requires: sqlite3 (stdlib)
"""

import os
import time
import sqlite3
import tempfile

print("=" * 60)
print("Bi-Temporal Knowledge Graph Demo")
print("=" * 60)

# We'll build a minimal in-process KG to keep this self-contained.
# The real KnowledgeGraphBridge in mempalace-agi uses the same schema.

db_path = os.path.join(tempfile.gettempdir(), "kg_demo.db")

conn = sqlite3.connect(db_path)
conn.execute("DROP TABLE IF EXISTS triples")
conn.execute("""
    CREATE TABLE triples (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        subject    TEXT    NOT NULL,
        predicate  TEXT    NOT NULL,
        object     TEXT    NOT NULL,
        confidence REAL    DEFAULT 1.0,
        valid_from TEXT    NOT NULL,   -- bi-temporal: when the fact became true
        valid_to   TEXT    DEFAULT 'now',
        recorded   TEXT    NOT NULL,   -- bi-temporal: when we recorded it
        source     TEXT    DEFAULT ''
    )
""")
conn.commit()


def add_triple(subj, pred, obj, confidence=1.0, valid_from=None, source="demo"):
    """Add a knowledge graph triple with bi-temporal timestamps."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    valid_from = valid_from or now
    conn.execute(
        "INSERT INTO triples (subject, predicate, object, confidence, "
        "valid_from, recorded, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (subj, pred, obj, confidence, valid_from, now, source),
    )
    conn.commit()
    print(f"  + ({subj}) --[{pred}]--> ({obj})  conf={confidence}")


def query(subj=None, pred=None, obj=None):
    """Query triples by any combination of subject/predicate/object."""
    clauses, params = [], []
    if subj:
        clauses.append("subject = ?"); params.append(subj)
    if pred:
        clauses.append("predicate = ?"); params.append(pred)
    if obj:
        clauses.append("object = ?"); params.append(obj)
    where = " AND ".join(clauses) if clauses else "1=1"
    rows = conn.execute(
        f"SELECT subject, predicate, object, confidence, valid_from FROM triples WHERE {where}",
        params,
    ).fetchall()
    return rows


def find_contradictions():
    """Find triples where the same (subject, predicate) has conflicting objects."""
    rows = conn.execute("""
        SELECT a.subject, a.predicate, a.object, b.object
        FROM triples a JOIN triples b
          ON a.subject = b.subject AND a.predicate = b.predicate
        WHERE a.object != b.object AND a.id < b.id
    """).fetchall()
    return rows


def find_path(start, end, max_depth=4):
    """BFS path search through the knowledge graph."""
    visited = {start}
    queue = [(start, [start])]
    for _ in range(max_depth):
        next_queue = []
        for node, path in queue:
            for row in query(subj=node):
                neighbor = row[2]  # object
                if neighbor == end:
                    return path + [f"--[{row[1]}]-->", neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_queue.append((neighbor, path + [f"--[{row[1]}]-->", neighbor]))
        queue = next_queue
    return None


# --- Build a small knowledge graph ---
print("\n--- Adding triples ---")
add_triple("Earth", "orbits", "Sun", confidence=0.99, valid_from="2024-01-01T00:00:00Z")
add_triple("Mars", "orbits", "Sun", confidence=0.99)
add_triple("Sun", "is_a", "G-type star", confidence=0.95)
add_triple("Earth", "has_satellite", "Moon")
add_triple("Earth", "average_temp", "15°C", confidence=0.90, source="climate_data")

# Add a contradictory fact (temperature changed)
add_triple("Earth", "average_temp", "16°C", confidence=0.85, source="updated_model")

# --- Query ---
print("\n--- Querying ---")
results = query(subj="Earth")
print(f"All facts about Earth ({len(results)}):")
for r in results:
    print(f"  ({r[0]}) --[{r[1]}]--> ({r[2]})  conf={r[3]}  valid_from={r[4]}")

# --- Contradiction detection ---
print("\n--- Contradiction detection ---")
contradictions = find_contradictions()
if contradictions:
    for c in contradictions:
        print(f"  ⚠️  ({c[0]}, {c[1]}): '{c[2]}' vs '{c[3]}'")
else:
    print("  No contradictions found.")

# --- Path finding ---
print("\n--- Path finding ---")
path = find_path("Moon", "G-type star")
if path:
    print(f"  Moon → G-type star: {' '.join(path)}")
else:
    # Try reverse direction too
    path = find_path("Earth", "Sun")
    if path:
        print(f"  Earth → Sun: {' '.join(path)}")

# Cleanup
conn.close()
os.unlink(db_path)

print("\n✅ Knowledge graph demo complete.")
