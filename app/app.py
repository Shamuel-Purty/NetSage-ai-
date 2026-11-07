from flask import Flask, render_template, request
from ai.diagnosis import build_user_case, build_diagnosis_prompt, get_gemini_diagnosis
from pathlib import Path
import csv
import json

app = Flask(__name__)

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_FILE = PROJECT_ROOT / "logs" / "batch_evaluation.csv"
REVIEW_FILE = PROJECT_ROOT / "logs" / "responsible_ai_log.csv"
CASES_FILE = PROJECT_ROOT / "data" / "cases.csv"


def load_csv(path):
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


# ============================================================
# MAIN DASHBOARD
# ============================================================

@app.route("/")
def dashboard():

    results = load_csv(RESULTS_FILE)
    reviews = load_csv(REVIEW_FILE)
    cases = load_csv(CASES_FILE)

    # -----------------------------
    # Case Explorer
    # -----------------------------

    result_map = {}

    for row in results:
        case_id = (
            row.get("Case ID")
            or row.get("Case_ID")
            or ""
        ).strip()

        if case_id:
            result_map[case_id] = row

    case_explorer = []

    for case in cases:

        case_id = (
            case.get("Case ID")
            or case.get("Case_ID")
            or ""
        ).strip()

        result = result_map.get(case_id, {})

        concept = (
            case.get("Concept Tag")
            or case.get("Concept")
            or result.get("Concept")
            or "Unknown"
        ).strip()

        verdict = (
            result.get("Verdict")
            or "Not Evaluated"
        ).strip()

        score = (
            result.get("Score")
            or "-"
        ).strip()

        case_explorer.append({
            "case_id": case_id,
            "title": case.get("Title", "Untitled"),
            "symptom": case.get("Symptom", ""),
            "concept": concept,
            "severity": case.get("Severity", "Unknown"),
            "osi_layer": case.get("OSI Layer", ""),
            "verdict": verdict,
            "score": score
        })

    # -----------------------------
    # Overall AI performance
    # -----------------------------

    total = len(results)

    correct = sum(
        1 for row in results
        if row.get("Verdict", "").strip().upper() == "CORRECT"
    )

    partial = sum(
        1 for row in results
        if row.get("Verdict", "").strip().upper() == "PARTIALLY CORRECT"
    )

    errors = sum(
        1 for row in results
        if row.get("Verdict", "").strip().upper() == "ERROR"
    )

    completed = total - errors

    agreement_rate = (
        correct / completed
        if completed
        else 0
    )

    usable_rate = (
        (correct + partial) / completed
        if completed
        else 0
    )

    # -----------------------------
    # Issue type breakdown
    # -----------------------------

    issue_breakdown = {}

    for row in results:

        concept = row.get("Concept", "").strip()

        if not concept:
            concept = "Unknown"

        issue_breakdown[concept] = (
            issue_breakdown.get(concept, 0) + 1
        )

    # -----------------------------
    # Performance by concept
    # -----------------------------

    concept_results = {}

    for row in results:

        concept = row.get("Concept", "").strip()

        if not concept:
            concept = "Unknown"

        if concept not in concept_results:

            concept_results[concept] = {
                "total": 0,
                "correct": 0,
                "partial": 0
            }

        concept_results[concept]["total"] += 1

        verdict = row.get("Verdict", "").strip().upper()

        if verdict == "CORRECT":
            concept_results[concept]["correct"] += 1

        elif verdict == "PARTIALLY CORRECT":
            concept_results[concept]["partial"] += 1

    concept_performance = []

    for concept, data in sorted(concept_results.items()):

        completed_concept = data["total"]

        rate = (
            data["correct"] / completed_concept
            if completed_concept
            else 0
        )

        concept_performance.append({
            "concept": concept,
            "total": data["total"],
            "correct": data["correct"],
            "partial": data["partial"],
            "rate": rate
        })

    # -----------------------------
    # Human review
    # -----------------------------

    accepted = 0
    edited = 0
    rejected = 0

    for review in reviews:

        decision = (
            review.get("Human_Decision")
            or review.get("Human Decision")
            or ""
        ).strip().upper()

        if decision == "ACCEPTED":
            accepted += 1

        elif decision == "EDITED":
            edited += 1

        elif decision == "REJECTED":
            rejected += 1

    # -----------------------------
    # Cases needing attention
    # -----------------------------

    attention_cases = [
        row for row in results
        if row.get("Verdict", "").strip().upper()
        != "CORRECT"
    ]

    # -----------------------------
    # Responsible AI audit
    # -----------------------------

    audit = []

    for review in reviews:

        case_id = (
            review.get("Case_ID")
            or review.get("Case ID")
            or "Unknown"
        )

        ai_verdict = (
            review.get("AI_Verdict")
            or review.get("AI Verdict")
            or "Unknown"
        )

        ai_score = (
            review.get("AI_Score")
            or review.get("AI Score")
            or "Unknown"
        )

        decision = (
            review.get("Human_Decision")
            or review.get("Human Decision")
            or "Unknown"
        ).strip().upper()

        issue = (
            review.get("Issue")
            or "Not provided"
        )

        correction = (
            review.get("Human_Correction")
            or review.get("Human Correction")
            or "Not provided"
        )

        print("DEBUG decision:", repr(decision))

        if decision in {"EDITED", "REJECTED"}:
            print("DEBUG human correction found:", case_id)

            audit.append({
                "case_id": case_id,
                "ai_verdict": ai_verdict,
                "ai_score": ai_score,
                "decision": decision,
                "issue": issue,
                "correction": correction
            })

    print("DEBUG reviews:", len(reviews))
    print("DEBUG audit:", len(audit), audit)

    return render_template(
        "dashboard.html",
        total=total,
        correct=correct,
        partial=partial,
        errors=errors,
        agreement_rate=agreement_rate,
        usable_rate=usable_rate,
        issue_breakdown=issue_breakdown,
        concept_performance=concept_performance,
        accepted=accepted,
        edited=edited,
        rejected=rejected,
        attention_cases=attention_cases,
        audit=audit,
        cases=cases,
        case_explorer=case_explorer
    )


# ============================================================
# CASE EXPLORER
# ============================================================

@app.route("/case/<case_id>")
def case_details(case_id):

    cases = load_csv(CASES_FILE)
    results = load_csv(RESULTS_FILE)
    reviews = load_csv(REVIEW_FILE)

    # Find requested case
    case = next(
        (
            row for row in cases
            if row.get("Case ID", "").strip().upper()
            == case_id.strip().upper()
        ),
        None
    )

    if case is None:
        return "Case not found", 404

    # Find AI evaluation result
    result = next(
        (
            row for row in results
            if row.get("Case ID", "").strip().upper()
            == case_id.strip().upper()
        ),
        None
    )

    # Find human review
    review = next(
        (
            row for row in reviews
            if (
                row.get("Case_ID")
                or row.get("Case ID")
                or ""
            ).strip().upper()
            == case_id.strip().upper()
        ),
        None
    )

    # Parse AI diagnosis JSON
    ai_diagnosis = {}

    if result:

        raw_diagnosis = result.get("AI Diagnosis", "").strip()

        if raw_diagnosis:

            try:
                ai_diagnosis = json.loads(raw_diagnosis)

            except (json.JSONDecodeError, TypeError):
                ai_diagnosis = {
                    "raw": raw_diagnosis
                }

    return render_template(
        "case.html",
        case=case,
        result=result,
        review=review,
        ai_diagnosis=ai_diagnosis
    )


# ============================================================
# RUN FLASK
# ============================================================

@app.route("/diagnose", methods=["GET", "POST"])
def diagnose():

    if request.method == "POST":

        problem = request.form.get("problem", "").strip()
        symptoms = request.form.get("symptoms", "").strip()
        network_info = request.form.get("network_info", "").strip()

        # Build a case using the existing NetSage structure
        case = build_user_case(
            problem,
            symptoms,
            network_info
        )

        # Use the existing diagnosis pipeline
        diagnosis_prompt = build_diagnosis_prompt(case)

        raw_diagnosis = get_gemini_diagnosis(
            diagnosis_prompt
        )
        import json
        print("\n===== GEMINI DIAGNOSIS =====")
        print(raw_diagnosis)
        print("============================\n")

        try:
            diagnosis = json.loads(raw_diagnosis)
        except (json.JSONDecodeError, TypeError):
            diagnosis = {
        "root_cause": "Unable to parse AI diagnosis.",
        "confidence": "Unknown",
        "evidence": [],
        "next_command": "",
        "fix_steps": [],
        "raw": raw_diagnosis
    }

        return render_template(
            "diagnosis.html",
    submitted=True,
    problem=problem,
    symptoms=symptoms,
    network_info=network_info,
    diagnosis=diagnosis
)

    return render_template(
        "diagnosis.html",
        submitted=False
    )
if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )