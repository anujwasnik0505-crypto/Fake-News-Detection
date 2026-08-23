"""
SQLite database — logs every headline check.

Features:
- Automatically creates history.db
- Stores every verification
- Returns history with record IDs
- Deletes individual history records
- Provides dashboard statistics
"""

import os
import sqlite3
import datetime

# ============================================================
# DATABASE PATH
# ============================================================

DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "history.db"
)

# ============================================================
# CONNECTION
# ============================================================

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():
    conn = _connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            headline TEXT NOT NULL,
            verdict TEXT NOT NULL,
            mode TEXT NOT NULL,
            detail TEXT,
            checked_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

# ============================================================
# LOG CHECK
# ============================================================

def log_check(
    headline,
    verdict,
    mode,
    detail=""
):
    """
    Save one headline-check result.
    """

    init_db()

    conn = _connect()

    conn.execute(
        """
        INSERT INTO checks
        (
            headline,
            verdict,
            mode,
            detail,
            checked_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            headline,
            verdict,
            mode,
            detail,
            datetime.datetime.now().isoformat(
                timespec="seconds"
            ),
        ),
    )

    conn.commit()
    conn.close()

# ============================================================
# GET HISTORY
# ============================================================

def get_history(limit=20):
    """
    Return most recent checks.

    IMPORTANT:
    id is included so frontend can delete
    a specific history record.
    """

    init_db()

    conn = _connect()

    rows = conn.execute(
        """
        SELECT
            id,
            headline,
            verdict,
            mode,
            detail,
            checked_at
        FROM checks
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]

# ============================================================
# DELETE HISTORY
# ============================================================

def delete_history(check_id):
    """
    Delete one history record by ID.

    Returns:
        True  -> successfully deleted
        False -> record not found
    """

    init_db()

    conn = _connect()

    cursor = conn.execute(
        """
        DELETE FROM checks
        WHERE id = ?
        """,
        (check_id,),
    )

    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted

# ============================================================
# GET STATS
# ============================================================

def get_stats():
    """
    Return dashboard statistics.
    """

    init_db()

    conn = _connect()

    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM checks
        """
    ).fetchone()[0]

    by_verdict = conn.execute(
        """
        SELECT
            verdict,
            COUNT(*) AS n
        FROM checks
        GROUP BY verdict
        """
    ).fetchall()

    by_mode = conn.execute(
        """
        SELECT
            mode,
            COUNT(*) AS n
        FROM checks
        GROUP BY mode
        """
    ).fetchall()

    conn.close()

    verdict_stats = {
        row["verdict"]: row["n"]
        for row in by_verdict
    }

    mode_stats = {
        row["mode"]: row["n"]
        for row in by_mode
    }

    return {
        "total_checks": total,
        "real": verdict_stats.get("REAL", 0),
        "fake": verdict_stats.get("FAKE", 0),
        "unverified": verdict_stats.get("UNVERIFIED", 0),
        "by_verdict": verdict_stats,
        "by_mode": mode_stats
    }