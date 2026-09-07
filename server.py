"""
Small local API server that bridges the UI to the real agent and database.
Run with: python server.py
Then the UI can call http://localhost:5000/api/...
"""
from flask import Flask, request, jsonify
from flask_cors import CORS

from tools.patient_tools import (
    get_all_patients, add_note, find_patient_by_name,
    edit_note, delete_note, update_vacation, schedule_appointment,
    add_patient, set_paused, set_waitlist, set_reminder,
)
from agent import agent

app = Flask(__name__)
CORS(app)  # allows the HTML/JS frontend to call this server from a different origin


@app.route("/api/patients", methods=["GET"])
def api_get_patients():
    """Returns the raw patient list — no agent reasoning, just the data."""
    return jsonify(get_all_patients())


@app.route("/api/patients/search", methods=["GET"])
def api_search_patients():
    """Used for the autocomplete search box."""
    query = request.args.get("q", "")
    return jsonify(find_patient_by_name(query))


@app.route("/api/notes", methods=["POST"])
def api_add_note():
    """
    Staff saves a note for a patient. The note is saved directly first
    (so saving never depends on the agent), then a focused agent call
    checks the note text for a relative time reference and sets a
    reminder if one is found.
    """
    data = request.get_json()
    patient_id = data.get("patient_id")
    note_text = data.get("note_text")
    note_date = data.get("note_date")
    created_by = data.get("created_by")
    if not (patient_id and note_text and note_date):
        return jsonify({"error": "patient_id, note_text, and note_date are required"}), 400

    result = add_note(patient_id, note_text, note_date, created_by)

    reminder_note = None
    try:
        reminder_prompt = (
            f'A note was just logged for patient {patient_id} on {note_date}: '
            f'"{note_text}". If this note contains a relative time reference '
            f'(e.g. "tomorrow", "next Monday", "in a week"), calculate the '
            f'concrete date it refers to (using {note_date} as "today") and '
            f'call set_reminder for patient {patient_id} with that date and a '
            f'short quote as source_note. If there is no time reference, do '
            f'not call any tool at all — just reply with the word "none".'
        )
        agent(reminder_prompt)
    except Exception as e:
        # Reminder detection is a nice-to-have — never let it block the save.
        reminder_note = f"(reminder check skipped: {e})"

    response = {"message": result}
    if reminder_note:
        response["note"] = reminder_note
    return jsonify(response)


@app.route("/api/notes/<int:note_id>", methods=["PUT"])
def api_edit_note(note_id):
    """Staff edits an existing note."""
    data = request.get_json()
    new_text = data.get("new_text")
    if not new_text:
        return jsonify({"error": "new_text is required"}), 400
    result = edit_note(note_id, new_text)
    return jsonify({"message": result})


@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def api_delete_note(note_id):
    """Staff deletes a note. Never auto-promotes an older note."""
    result = delete_note(note_id)
    return jsonify({"message": result})


@app.route("/api/vacation", methods=["POST"])
def api_update_vacation():
    """Logs, edits, or ends a patient's vacation status with a from-to range."""
    data = request.get_json()
    patient_id = data.get("patient_id")
    on_vacation = data.get("on_vacation")
    vacation_start = data.get("vacation_start")
    expected_return_date = data.get("expected_return_date")
    if patient_id is None or on_vacation is None:
        return jsonify({"error": "patient_id and on_vacation are required"}), 400
    result = update_vacation(patient_id, on_vacation, vacation_start, expected_return_date)
    return jsonify({"message": result})


@app.route("/api/paused", methods=["POST"])
def api_set_paused():
    """Marks a patient as paused (e.g. insurance) or resumes normal tracking."""
    data = request.get_json()
    patient_id = data.get("patient_id")
    is_paused = data.get("is_paused")
    pause_reason = data.get("pause_reason")
    resume_date = data.get("resume_date")
    if patient_id is None or is_paused is None:
        return jsonify({"error": "patient_id and is_paused are required"}), 400
    result = set_paused(patient_id, is_paused, pause_reason, resume_date)
    return jsonify({"message": result})


@app.route("/api/waitlist", methods=["POST"])
def api_set_waitlist():
    """Marks whether a patient is waiting for a preferred slot to open up."""
    data = request.get_json()
    patient_id = data.get("patient_id")
    waiting_for_opening = data.get("waiting_for_opening")
    preferred_time = data.get("preferred_time")
    if patient_id is None or waiting_for_opening is None:
        return jsonify({"error": "patient_id and waiting_for_opening are required"}), 400
    result = set_waitlist(patient_id, waiting_for_opening, preferred_time)
    return jsonify({"message": result})


@app.route("/api/appointments", methods=["POST"])
def api_schedule_appointment():
    """Sets a patient's next appointment date."""
    data = request.get_json()
    patient_id = data.get("patient_id")
    appointment_date = data.get("appointment_date")
    if not (patient_id and appointment_date):
        return jsonify({"error": "patient_id and appointment_date are required"}), 400
    result = schedule_appointment(patient_id, appointment_date)
    return jsonify({"message": result})


@app.route("/api/patients", methods=["POST"])
def api_add_patient():
    """Adds a brand-new patient with their treatment plan."""
    data = request.get_json()
    name = data.get("name")
    treatment_type = data.get("treatment_type")
    frequency_per_week = data.get("frequency_per_week")
    duration_weeks = data.get("duration_weeks", 6)
    if not (name and treatment_type and frequency_per_week):
        return jsonify({"error": "name, treatment_type, and frequency_per_week are required"}), 400
    result = add_patient(name, treatment_type, frequency_per_week, duration_weeks)
    return jsonify({"message": result})


@app.route("/api/followup", methods=["GET"])
def api_followup():
    """
    Runs the actual Strands agent and returns its reasoning as today's
    follow-up list. This is the real agent output, not hardcoded logic.
    """
    today = request.args.get("date", "2026-08-30")
    response = agent(f"Give me today's follow-up list. Today's date is {today}.")
    return jsonify({"followup_text": str(response)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)