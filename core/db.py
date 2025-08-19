import sqlite3
from pathlib import Path
from typing import Iterable, Dict, Any

DB_PATH = Path("data/db/results.db")

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        operator TEXT,
        lot TEXT,
        dut_id TEXT,
        board_name TEXT,
        layout_file TEXT,
        notes TEXT
    );
    """ ,
    """
    CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        field_id TEXT NOT NULL,
        label TEXT,
        component_type TEXT,
        value TEXT,
        unit TEXT,
        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
    );
    """
]

def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        for stmt in SCHEMA:
            cur.execute(stmt)
        conn.commit()

def insert_run(run_meta: Dict[str, Any], measurements: Iterable[Dict[str, Any]]):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO runs(run_id, timestamp, operator, lot, dut_id, board_name, layout_file, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""" ,
            (
                run_meta.get("run_id"),
                run_meta.get("timestamp"),
                run_meta.get("operator"),
                run_meta.get("lot"),
                run_meta.get("dut_id"),
                run_meta.get("board_name"),
                run_meta.get("layout_file"),
                run_meta.get("notes","")
            )
        )
        cur.executemany(
            """INSERT INTO measurements(run_id, field_id, label, component_type, value, unit)
                   VALUES (?, ?, ?, ?, ?, ?)""" ,
            [
                (run_meta.get("run_id"), m.get("field_id"), m.get("label"), m.get("component_type"), m.get("value"), m.get("unit"))
                for m in measurements
            ]
        )
        conn.commit()
