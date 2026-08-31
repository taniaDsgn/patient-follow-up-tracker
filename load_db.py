"""
Loads patients.json into a SQLite database (patients.db).
Run: python3 load_db.py
"""
import json
import sqlite3
from pathlib import Path

DATA_FILE = Path(__file__).parent / "patients.json"
DB_FILE = Path(__file__).parent / "patients.db"


def load():
    with open(DATA_FILE) as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.executescript("""
    DROP TABLE IF EXISTS patients;
    DROP TABLE IF EXISTS notes;

    CREATE TABLE patients (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        treatment_type TEXT,
        frequency_per_week INTEGER,
        duration_weeks INTEGER,
        started_on TEXT,
        last_scheduled_date TEXT,
        status TEXT,               -- 'scheduled' or 'not_scheduled'
        next_appointment TEXT,     -- nullable
        on_vacation INTEGER,       -- 0 or 1
        expected_return_date TEXT  -- nullable
    );

    CREATE TABLE notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        note_date TEXT,
        text TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    );
    """)

    for p in data["patients"]:
        tp = p["treatment_plan"]
        vac = p["vacation"]
        cur.execute(
            """INSERT INTO patients
               (id, name, treatment_type, frequency_per_week, duration_weeks,
                started_on, last_scheduled_date, status, next_appointment,
                on_vacation, expected_return_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                p["id"], p["name"], tp["type"], tp["frequency_per_week"],
                tp["duration_weeks"], tp["started_on"], p["last_scheduled_date"],
                p["status"], p.get("next_appointment"),
                1 if vac["on_vacation"] else 0, vac["expected_return_date"],
            ),
        )
        for note in p.get("notes", []):
            cur.execute(
                "INSERT INTO notes (patient_id, note_date, text) VALUES (?, ?, ?)",
                (p["id"], note["date"], note["text"]),
            )

    conn.commit()
    print(f"Loaded {len(data['patients'])} patients into {DB_FILE}")
    conn.close()


if __name__ == "__main__":
    load()
