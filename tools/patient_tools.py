"""
Tools the agent can call. Each function decorated with @tool becomes
something the agent can decide to use on its own.
"""
import sqlite3
from pathlib import Path
from strands import tool

DB_PATH = Path(__file__).parent.parent / "patients.db"


@tool
def get_all_patients() -> list[dict]:
    """
    Returns the full patient list, including their treatment plan,
    scheduling status, vacation info, and any notes staff have logged.
    Use this to see who exists and their current state.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM patients")
    patients = [dict(row) for row in cur.fetchall()]

    for p in patients:
        cur.execute(
            "SELECT note_date, text FROM notes WHERE patient_id = ? ORDER BY note_date",
            (p["id"],),
        )
        p["notes"] = [dict(row) for row in cur.fetchall()]

    conn.close()
    return patients


@tool
def add_note(patient_id: str, note_text: str, note_date: str) -> str:
    """
    Logs a note for a patient — e.g. the reason they haven't scheduled,
    or an update on their vacation status. This is the only way notes
    get added; the agent never contacts patients or invents notes itself.

    Args:
        patient_id: The patient's id, e.g. "p001".
        note_text: The note content, as typed by staff.
        note_date: The date of the note in YYYY-MM-DD format.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
    if cur.fetchone() is None:
        conn.close()
        return f"No patient found with id {patient_id}."

    cur.execute(
        "INSERT INTO notes (patient_id, note_date, text) VALUES (?, ?, ?)",
        (patient_id, note_date, note_text),
    )
    conn.commit()
    conn.close()
    return f"Note added for {patient_id} on {note_date}."


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