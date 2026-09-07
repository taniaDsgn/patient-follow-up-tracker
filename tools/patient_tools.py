"""
Tools the agent can call. Each function decorated with @tool becomes
something the agent can decide to use on its own.
"""
import sqlite3
import datetime
from pathlib import Path
from strands import tool

DB_PATH = Path(__file__).parent.parent / "patients.db"


def _ensure_columns():
    """Adds any new columns this file depends on, safe to run repeatedly."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(notes)")
    note_cols = [row[1] for row in cur.fetchall()]
    if "created_by" not in note_cols:
        cur.execute("ALTER TABLE notes ADD COLUMN created_by TEXT")

    cur.execute("PRAGMA table_info(patients)")
    patient_cols = [row[1] for row in cur.fetchall()]
    new_patient_cols = {
        "vacation_start": "TEXT",
        "is_paused": "INTEGER DEFAULT 0",
        "pause_reason": "TEXT",
        "resume_date": "TEXT",
        "waiting_for_opening": "INTEGER DEFAULT 0",
        "preferred_time": "TEXT",
        "reminder_date": "TEXT",
        "reminder_source": "TEXT",
    }
    for col, coltype in new_patient_cols.items():
        if col not in patient_cols:
            cur.execute(f"ALTER TABLE patients ADD COLUMN {col} {coltype}")

    conn.commit()
    conn.close()


_ensure_columns()


@tool
def get_all_patients() -> list[dict]:
    """
    Returns the full patient list, including their treatment plan,
    scheduling status, vacation info, pause info, waitlist info, and
    any notes staff have logged. Use this to see who exists and their
    current state.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM patients")
    patients = [dict(row) for row in cur.fetchall()]

    for p in patients:
        cur.execute(
            "SELECT id, note_date, text, created_by FROM notes WHERE patient_id = ? ORDER BY note_date",
            (p["id"],),
        )
        p["notes"] = [dict(row) for row in cur.fetchall()]

    conn.close()
    return patients


@tool
def add_note(patient_id: str, note_text: str, note_date: str, created_by: str = None) -> str:
    """
    Logs a note for a patient — e.g. the reason they haven't scheduled,
    or an update on their vacation status. This is the only way notes
    get added; the agent never contacts patients or invents notes itself.

    Args:
        patient_id: The patient's id, e.g. "p001".
        note_text: The note content, as typed by staff.
        note_date: The date and time of the note, ISO format (e.g. "2026-08-30T14:32:00").
        created_by: Name of the staff member who logged this note.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
    if cur.fetchone() is None:
        conn.close()
        return f"No patient found with id {patient_id}."

    cur.execute(
        "INSERT INTO notes (patient_id, note_date, text, created_by) VALUES (?, ?, ?, ?)",
        (patient_id, note_date, note_text, created_by),
    )
    conn.commit()
    conn.close()
    return f"Note added for {patient_id} on {note_date}."


@tool
def edit_note(note_id: int, new_text: str) -> str:
    """
    Edits the text of an existing note by its id. Only staff-initiated
    edits use this — the agent never rewrites a note on its own.

    Args:
        note_id: The database id of the note (from get_all_patients' notes list).
        new_text: The corrected note text.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM notes WHERE id = ?", (note_id,))
    if cur.fetchone() is None:
        conn.close()
        return f"No note found with id {note_id}."
    cur.execute("UPDATE notes SET text = ? WHERE id = ?", (new_text, note_id))
    conn.commit()
    conn.close()
    return f"Note {note_id} updated."


@tool
def delete_note(note_id: int) -> str:
    """
    Deletes a note by its id. This never auto-promotes an older note —
    if the deleted note was the most recent one, the patient simply
    has no current note until staff adds a new one.

    Args:
        note_id: The database id of the note (from get_all_patients' notes list).
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return f"Deleted note {note_id}." if deleted else f"No note found with id {note_id}."


@tool
def update_vacation(patient_id: str, on_vacation: bool, vacation_start: str = None, expected_return_date: str = None) -> str:
    """
    Logs, edits, or ends a patient's vacation status, with a from-to date range.

    Args:
        patient_id: The patient's id, e.g. "p001".
        on_vacation: True to mark them on vacation, False to end vacation status.
        vacation_start: Vacation start date in YYYY-MM-DD format. Required when on_vacation is True.
        expected_return_date: Expected return date in YYYY-MM-DD format. Required when on_vacation is True.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
    if cur.fetchone() is None:
        conn.close()
        return f"No patient found with id {patient_id}."
    cur.execute(
        "UPDATE patients SET on_vacation = ?, vacation_start = ?, expected_return_date = ? WHERE id = ?",
        (1 if on_vacation else 0,
         vacation_start if on_vacation else None,
         expected_return_date if on_vacation else None,
         patient_id),
    )
    conn.commit()
    conn.close()
    return f"Vacation status updated for {patient_id}."


@tool
def set_paused(patient_id: str, is_paused: bool, pause_reason: str = None, resume_date: str = None) -> str:
    """
    Marks a patient as paused (e.g. insurance ran out of visits for the
    year) or un-pauses them. Paused patients are excluded from normal
    overdue follow-up — they are not ignoring calls, they are waiting
    on something outside their control. They should only be flagged
    again once resume_date arrives.

    Args:
        patient_id: The patient's id, e.g. "p001".
        is_paused: True to mark as paused, False to resume normal tracking.
        pause_reason: Why treatment paused, e.g. "Insurance visits exhausted for the year".
        resume_date: Date treatment is expected to resume, YYYY-MM-DD format.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
    if cur.fetchone() is None:
        conn.close()
        return f"No patient found with id {patient_id}."
    cur.execute(
        "UPDATE patients SET is_paused = ?, pause_reason = ?, resume_date = ? WHERE id = ?",
        (1 if is_paused else 0,
         pause_reason if is_paused else None,
         resume_date if is_paused else None,
         patient_id),
    )
    conn.commit()
    conn.close()
    return f"Paused status updated for {patient_id}."


@tool
def set_waitlist(patient_id: str, waiting_for_opening: bool, preferred_time: str = None) -> str:
    """
    Marks whether a patient is waiting for a preferred appointment slot
    to open up (e.g. "Tuesday afternoons"), so staff can quickly find
    who to call when a slot frees up.

    Args:
        patient_id: The patient's id, e.g. "p001".
        waiting_for_opening: True if they want to be notified of openings.
        preferred_time: Free-text description of their preferred time, e.g. "Tuesday afternoons".
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
    if cur.fetchone() is None:
        conn.close()
        return f"No patient found with id {patient_id}."
    cur.execute(
        "UPDATE patients SET waiting_for_opening = ?, preferred_time = ? WHERE id = ?",
        (1 if waiting_for_opening else 0, preferred_time if waiting_for_opening else None, patient_id),
    )
    conn.commit()
    conn.close()
    return f"Waitlist status updated for {patient_id}."


@tool
def set_reminder(patient_id: str, reminder_date: str, source_note: str = None) -> str:
    """
    Sets a reminder date for staff to check back on a patient — typically
    called after reading a note that mentions a specific timeframe
    (e.g. "will call tomorrow", "reaching out next Monday"). Use this
    to translate relative time references in notes into a concrete date
    so staff gets reminded at the right moment instead of being asked
    to remember it themselves.

    Args:
        patient_id: The patient's id, e.g. "p001".
        reminder_date: The calculated date to remind staff, YYYY-MM-DD format.
        source_note: Optional short quote of the note text that prompted this reminder.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
    if cur.fetchone() is None:
        conn.close()
        return f"No patient found with id {patient_id}."
    cur.execute(
        "UPDATE patients SET reminder_date = ?, reminder_source = ? WHERE id = ?",
        (reminder_date, source_note, patient_id),
    )
    conn.commit()
    conn.close()
    return f"Reminder set for {patient_id} on {reminder_date}."


@tool
def schedule_appointment(patient_id: str, appointment_date: str) -> str:
    """
    Sets a patient's next scheduled appointment date, entered manually by staff.

    Args:
        patient_id: The patient's id, e.g. "p001".
        appointment_date: The appointment date in YYYY-MM-DD format.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
    if cur.fetchone() is None:
        conn.close()
        return f"No patient found with id {patient_id}."
    cur.execute(
        "UPDATE patients SET next_appointment = ?, status = 'scheduled' WHERE id = ?",
        (appointment_date, patient_id),
    )
    conn.commit()
    conn.close()
    return f"Appointment set for {patient_id} on {appointment_date}."


@tool
def add_patient(name: str, treatment_type: str, frequency_per_week: int, duration_weeks: int) -> str:
    """
    Adds a brand-new patient with their treatment plan. They start as
    not_scheduled with no notes, since they haven't been seen yet.

    Args:
        name: The patient's full name.
        treatment_type: e.g. "PT", "Acu", or "Massage".
        frequency_per_week: How many visits per week their plan calls for (1 or 2).
        duration_weeks: How many weeks the treatment plan runs.
    """
    new_id = "p" + str(int(datetime.datetime.now().timestamp()))[-6:]
    today = datetime.date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO patients
           (id, name, treatment_type, frequency_per_week, duration_weeks,
            started_on, last_scheduled_date, status, next_appointment,
            on_vacation, expected_return_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'not_scheduled', NULL, 0, NULL)""",
        (new_id, name, treatment_type, frequency_per_week, duration_weeks, today, today),
    )
    conn.commit()
    conn.close()
    return f"Added new patient {name} with id {new_id}."


@tool
def find_patient_by_name(name_query: str) -> list[dict]:
    """
    Looks up patients by partial name match — used to power a
    type-ahead search when staff start typing a patient's name.

    Args:
        name_query: Partial or full patient name to search for.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, status FROM patients WHERE name LIKE ? ORDER BY name",
        (f"%{name_query}%",),
    )
    results = [dict(row) for row in cur.fetchall()]
    conn.close()
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(get_all_patients(), indent=2))