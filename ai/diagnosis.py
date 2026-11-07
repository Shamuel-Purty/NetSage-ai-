import csv
import os
from pathlib import Path
from google import genai

# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent
CASE_FILE = BASE_DIR / "data" / "cases.csv"
PROMPT_FILE = BASE_DIR / "prompts" / "diagnose_prompt.md"
# Gemini client
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def load_cases():
    """Load troubleshooting cases from cases.csv."""
    with open(CASE_FILE, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)


def get_case(case_id):
    """Find a case by Case ID."""
    cases = load_cases()

    for case in cases:
        if case["Case ID"].strip() == case_id:
            return case

    return None


def load_prompt():
    """Load the NetSage diagnosis prompt."""
    with open(PROMPT_FILE, "r", encoding="utf-8") as file:
        return file.read()


def build_case_input(case):
    """
    Build the information that is allowed to be shown
    to the diagnosis model.

    Ground-truth fields are intentionally excluded.
    """

    return f"""
Case ID:
{case["Case ID"]}

Title:
{case["Title"]}

Symptoms:
{case["Symptoms"]}

Topology Note:
{case["Topology Note"]}

Devices:
{case["Devices"]}

Concept Tag:
{case["Concept Tag"]}

OSI Layer:
{case["OSI Layer"]}

Severity:
{case["Severity"]}

Show Command Outputs:
{case["Show Command Outputs"]}
""".strip()
def build_user_case(problem, symptoms, network_info):
    """
    Convert free-form user input into the case structure
    expected by the existing diagnosis pipeline.
    """

    return {
        "Case ID": "LIVE-DIAGNOSIS",
        "Title": problem,
        "Symptoms": symptoms,
        "Topology Note": network_info,
        "Devices": network_info,
        "Concept Tag": "Unknown",
        "OSI Layer": "Unknown",
        "Severity": "Unknown",
        "Show Command Outputs": network_info
    }

def build_diagnosis_prompt(case):
    """Combine the system troubleshooting prompt with case data."""

    base_prompt = load_prompt()
    case_input = build_case_input(case)
    return f"""
{base_prompt}

---

## Supplied Case

{case_input}

---

## Task

Analyze the supplied case according to the rules above.

Return ONLY the required JSON output.
""".strip()
def get_gemini_diagnosis(diagnosis_prompt):
    """Send the troubleshooting prompt to Gemini."""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=diagnosis_prompt
    )

    return response.text



if __name__ == "__main__":

    case_id = input("Enter Case ID: ").strip()

    case = get_case(case_id)

    if case is None:
        print(f"\nCase {case_id} not found.")
    else:
        diagnosis_prompt = build_diagnosis_prompt(case)

        print("\n" + "=" * 70)
        print("NETSAGE AI DIAGNOSIS")
        print("=" * 70)

        try:
            diagnosis = get_gemini_diagnosis(diagnosis_prompt)
            print(diagnosis)

        except Exception as error:
            print("\nGemini request failed:")
            print(error)

        print("=" * 70)