"""
Adds 21 more patients (with realistic mixed statuses) directly to patients.db,
bringing the total to 30+. Run once from your project root:

    python add_more_patients.py

Safe to run multiple times — it checks for existing IDs before inserting.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "patients.db"

# Today is treated as 2026-09-10 for these relative dates.
NEW_PATIENTS = [
    # --- Needs follow-up: no note, no future appointment ---
    {"id": "p101", "name": "Nathan Price", "treatment_type": "PT", "frequency_per_week": 2,
     "duration_weeks": 6, "started_on": "2026-07-20", "last_scheduled_date": "2026-08-18",
     "status": "not_scheduled", "next_appointment": None},
    {"id": "p102", "name": "Olivia Bennett", "treatment_type": "Massage", "frequency_per_week": 1,
     "duration_weeks": 4, "started_on": "2026-08-01", "last_scheduled_date": "2026-08-22",
     "status": "not_scheduled", "next_appointment": None},
    {"id": "p103", "name": "Carlos Mendez", "treatment_type": "Acu", "frequency_per_week": 1,
     "duration_weeks": 8, "started_on": "2026-06-10", "last_scheduled_date": "2026-08-15",
     "status": "not_scheduled", "next_appointment": None},
    {"id": "p104", "name": "Rachel Kim", "treatment_type": "PT", "frequency_per_week": 2,
     "duration_weeks": 6, "started_on": "2026-07-25", "last_scheduled_date": "2026-08-27",
     "status": "not_scheduled", "next_appointment": None},
    {"id": "p105", "name": "Derek Foster", "treatment_type": "Massage", "frequency_per_week": 1,
     "duration_weeks": 4, "started_on": "2026-08-05", "last_scheduled_date": "2026-08-29",
     "status": "not_scheduled", "next_appointment": None},
    {"id": "p106", "name": "Yuki Tanaka", "treatment_type": "Acu", "frequency_per_week": 2,
     "duration_weeks": 5, "started_on": "2026-07-15", "last_scheduled_date": "2026-08-20",
     "status": "not_scheduled", "next_appointment": None},

    # --- Follow-up logged: has a note, no future appointment ---
    {"id": "p107", "name": "Grace Liu", "treatment_type": "PT", "frequency_per_week": 1,
     "duration_weeks": 6, "started_on": "2026-07-10", "last_scheduled_date": "2026-08-24",
     "status": "not_scheduled", "next_appointment": None,
     "note": "Recovering from flu, will call once feeling better"},
    {"id": "p108", "name": "Marcus Webb Jr", "treatment_type": "Massage", "frequency_per_week": 1,
     "duration_weeks": 4, "started_on": "2026-08-02", "last_scheduled_date": "2026-08-26",
     "status": "not_scheduled", "next_appointment": None,
     "note": "Said she'd text once new work schedule is confirmed"},
    {"id": "p109", "name": "Aisha Rahman", "treatment_type": "Acu", "frequency_per_week": 1,
     "duration_weeks": 8, "started_on": "2026-06-20", "last_scheduled_date": "2026-08-19",
     "status": "not_scheduled", "next_appointment": None,
     "note": "Traveling for a family event, back next week"},
    {"id": "p110", "name": "Tom Bradley", "treatment_type": "PT", "frequency_per_week": 2,
     "duration_weeks": 6, "started_on": "2026-07-28", "last_scheduled_date": "2026-08-30",
     "status": "not_scheduled", "next_appointment": None,
     "note": "Left voicemail, no callback yet"},
    {"id": "p111", "name": "Nina Petrova", "treatment_type": "Massage", "frequency_per_week": 1,
     "duration_weeks": 4, "started_on": "2026-08-08", "last_scheduled_date": "2026-08-31",
     "status": "not_scheduled", "next_appointment": None,
     "note": "Confirmed she wants to continue, picking a date next week"},

    # --- Scheduled: has a future appointment ---
    {"id": "p112", "name": "Ethan Brooks", "treatment_type": "PT", "frequency_per_week": 2,
     "duration_weeks": 6, "started_on": "2026-08-01", "last_scheduled_date": "2026-09-01",
     "status": "scheduled", "next_appointment": "2026-09-15"},
    {"id": "p113", "name": "Sofia Moreno", "treatment_type": "Acu", "frequency_per_week": 1,
     "duration_weeks": 8, "started_on": "2026-07-05", "last_scheduled_date": "2026-09-03",
     "status": "scheduled", "next_appointment": "2026-09-17"},
    {"id": "p114", "name": "Ben Carter", "treatment_type": "Massage", "frequency_per_week": 1,
     "duration_weeks": 4, "started_on": "2026-08-10", "last_scheduled_date": "2026-09-05",
     "status": "scheduled", "next_appointment": "2026-09-12"},
    {"id": "p115", "name": "Chloe Anderson", "treatment_type": "PT", "frequency_per_week": 2,
     "duration_weeks": 6, "started_on": "2026-08-03", "last_scheduled_date": "2026-09-04",
     "status": "scheduled", "next_appointment": "2026-09-11"},
    {"id": "p116", "name": "Victor Nguyen", "treatment_type": "Acu", "frequency_per_week": 1,
     "duration_weeks": 8, "started_on": "2026-07-18", "last_scheduled_date": "2026-09-02",
     "status": "scheduled", "next_appointment": "2026-09-16"},

    # --- On vacation ---
    {"id": "p117", "name": "Isabella Rossi", "treatment_type": "Massage", "frequency_per_week": 1,
     "duration_weeks": 4, "started_on": "2026-07-22", "last_scheduled_date": "2026-08-20",
     "status": "not_scheduled", "next_appointment": None,
     "on_vacation": True, "vacation_start": "2026-08-25", "expected_return_date": "2026-09-20",
     "note": "Traveling abroad, back Sep 20"},
    {"id": "p118", "name": "Omar Farouk", "treatment_type": "PT", "frequency_per_week": 2,
     "duration_weeks": 6, "started_on": "2026-08-01", "last_scheduled_date": "2026-08-28",
     "status": "not_scheduled", "next_appointment": None,
     "on_vacation": True, "vacation_start": "2026-09-01", "expected_return_date": "2026-09-22"},

    # --- Paused ---
    {"id": "p119", "name": "Hannah Wright", "treatment_type": "PT", "frequency_per_week": 2,
     "duration_weeks": 6, "started_on": "2026-06-01", "last_scheduled_date": "2026-08-05",
     "status": "not_scheduled", "next_appointment": None,
     "is_paused": True, "pause_reason": "Insurance visits exhausted for the year",
     "resume_date": "2027-01-01"},
    {"id": "p120", "name": "Julian Castillo", "treatment_type": "Acu", "frequency_per_week": 1,
     "duration_weeks": 8, "started_on": "2026-05-15", "last_scheduled_date": "2026-07-30",
     "status": "not_scheduled", "next_appointment": None,
     "is_paused": True, "pause_reason": "Recovering from surgery, doctor's hold until cleared",
     "resume_date": "2026-10-15"},

    # --- Waitlist ---
    {"id": "p121", "name": "Zoe Fitzgerald", "treatment_type": "Massage", "frequency_per_week": 1,
     "duration_weeks": 4, "started_on": "2026-08-12", "last_scheduled_date": "2026-08-12",
     "status": "not_scheduled", "next_appointment": None,
     "waiting_for_opening": True, "preferred_time": "Wednesday afternoons",
     "note": "No opening available at last visit, wants next Wednesday slot"},
]


def add_patients():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id FROM patients")
    existing_ids = {row[0] for row in cur.fetchall()}

    added = 0
    for p in NEW_PATIENTS:
        if p["id"] in existing_ids:
            continue

        cur.execute(
            """INSERT INTO patients
               (id, name, treatment_type, frequency_per_week, duration_weeks,
                started_on, last_scheduled_date, status, next_appointment,
                on_vacation, expected_return_date, vacation_start,
                is_paused, pause_reason, resume_date,
                waiting_for_opening, preferred_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                p["id"], p["name"], p["treatment_type"], p["frequency_per_week"],
                p["duration_weeks"], p["started_on"], p["last_scheduled_date"],
                p["status"], p.get("next_appointment"),
                1 if p.get("on_vacation") else 0, p.get("expected_return_date"),
                p.get("vacation_start"),
                1 if p.get("is_paused") else 0, p.get("pause_reason"), p.get("resume_date"),
                1 if p.get("waiting_for_opening") else 0, p.get("preferred_time"),
            ),
        )

        if p.get("note"):
            cur.execute(
                "INSERT INTO notes (patient_id, note_date, text, created_by) VALUES (?, ?, ?, ?)",
                (p["id"], p["last_scheduled_date"] + "T09:00:00", p["note"], "Alex Rivera"),
            )

        added += 1

    conn.commit()
    conn.close()
    print(f"Added {added} new patients (skipped {len(NEW_PATIENTS) - added} already present).")


if __name__ == "__main__":
    add_patients()