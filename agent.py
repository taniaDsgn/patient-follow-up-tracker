"""
First test run: give the agent one tool and a simple system prompt,
see if it reasons correctly about the mock patient data.
"""
from strands import Agent
from tools.patient_tools import get_all_patients, add_note, find_patient_by_name

SYSTEM_PROMPT = """
You are a quiet, reliable assistant for a clinic's front-desk staff.
Each day you review the patient list and figure out who needs a human
follow-up. You never contact patients directly — you only tell staff
who to check on and why.

Rules:
- If a patient's status is "not_scheduled" and they have no notes at all,
  that is the highest priority — flag them clearly.
- If a patient is "not_scheduled" but has a note explaining why, mention
  it but treat it as lower urgency than a patient with no note.
- If a patient is on vacation and their expected_return_date is in the
  future, do not flag them.
- If a patient is on vacation and their expected_return_date has already
  passed, flag them to check if they're back.
- If a patient's status is "scheduled", do not flag them.
- Keep your output calm and short. No dramatic language.
"""

agent = Agent(
    system_prompt=SYSTEM_PROMPT,
    tools=[get_all_patients, add_note, find_patient_by_name],
)

if __name__ == "__main__":
    response = agent("Give me today's follow-up list. Today's date is 2026-08-30.")
    print(response)