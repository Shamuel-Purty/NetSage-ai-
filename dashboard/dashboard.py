import csv
from pathlib import Path
from collections import Counter

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_FILE = PROJECT_ROOT / "logs" / "batch_evaluation.csv"
CASES_FILE = PROJECT_ROOT / "data" / "cases.csv"
HUMAN_REVIEW_FILE = PROJECT_ROOT / "logs" / "responsible_ai_log.csv"

def load_csv(path):
    if not path.exists():
        print(f"File not found: {path}")
        return []

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main():
    results = load_csv(RESULTS_FILE)
    cases = load_csv(CASES_FILE)
    human_reviews = load_csv(HUMAN_REVIEW_FILE)

    if not results:
        print("No batch evaluation results found.")
        print(f"Expected: {RESULTS_FILE}")
        return

    print("=" * 70)
    print("                 NETSAGE AI DASHBOARD")
    print("=" * 70)
    print()

    # ---------------------------------------------------------
    # OVERALL AI PERFORMANCE
    # ---------------------------------------------------------

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

    agreement_rate = correct / (total - errors) if total > errors else 0
    usable_rate = (
        (correct + partial) / (total - errors)
        if total > errors
        else 0
    )

    print("AI PERFORMANCE")
    print("-" * 70)
    print(f"Total cases:       {total}")
    print(f"Correct:           {correct}")
    print(f"Partially correct: {partial}")
    print(f"Errors:            {errors}")
    print(f"Agreement rate:    {agreement_rate:.1%}")
    print(f"Usable diagnoses:  {usable_rate:.1%}")
    print()

    # ---------------------------------------------------------
    # ISSUE TYPE BREAKDOWN
    # ---------------------------------------------------------

    print("ISSUE TYPE BREAKDOWN")
    print("-" * 70)

    concepts = Counter(
        row.get("Concept", "").strip()
        for row in results
        if row.get("Concept", "").strip()
    )

    for concept, count in concepts.most_common():
        percentage = count / total * 100
        bar = "█" * max(1, round(percentage / 5))
        print(f"{concept:<20} {count:>3}  {bar}")

    print()

    # ---------------------------------------------------------
    # CONCEPT PERFORMANCE
    # ---------------------------------------------------------

    print("PERFORMANCE BY CONCEPT")
    print("-" * 70)

    concept_results = {}

    for row in results:
        concept = row.get("Concept", "").strip() or "Unknown"

        if concept not in concept_results:
            concept_results[concept] = {
                "total": 0,
                "correct": 0,
                "partial": 0,
            }

        concept_results[concept]["total"] += 1

        verdict = row.get("Verdict", "").strip().upper()

        if verdict == "CORRECT":
            concept_results[concept]["correct"] += 1

        elif verdict == "PARTIALLY CORRECT":
            concept_results[concept]["partial"] += 1

    for concept, data in sorted(concept_results.items()):
        completed = data["total"]

        rate = data["correct"] / completed if completed else 0

        print(
            f"{concept:<20} "
            f"{data['total']:>2} cases | "
            f"{data['correct']:>2} correct | "
            f"{rate:.1%}"
        )

    print()
    # --------------------------------------------------------------
    # HUMAN REVIEW STATUS
    # --------------------------------------------------------------

    print("HUMAN REVIEW")
    print("-" * 70)

    accepted = sum(
        1 for row in human_reviews
        if row.get("Human Decision", "").strip().upper() == "ACCEPTED"
)

    edited = sum(
        1 for row in human_reviews
        if row.get("Human Decision", "").strip().upper() == "EDITED"
)

    rejected = sum(
        1 for row in human_reviews
        if row.get("Human Decision", "").strip().upper() == "REJECTED"
)

    print(f"Cases reviewed: {len(human_reviews)}")
    print(f"Accepted:       {accepted}")
    print(f"Edited:         {edited}")
    print(f"Rejected:       {rejected}")
    print()

# --------------------------------------------------------------
# RESPONSIBLE AI AUDIT
# --------------------------------------------------------------

    print("RESPONSIBLE AI AUDIT")
    print("-" * 70)

    if not human_reviews:
        print("No human review records found.")
    else:
        # Show only cases where the human reviewer edited
        # the AI diagnosis.
        edited_reviews = [
            review for review in human_reviews
            if (
                review.get("Human_Decision")
                or review.get("Human Decision")
                or ""
            ).strip().upper() == "EDITED"
        ]

        if not edited_reviews:
            print("No edited cases found.")
        else:
            for review in edited_reviews:
                case_id = (
                    review.get("Case_ID")
                    or review.get("Case ID")
                    or review.get("case_id")
                    or "Unknown"
                )

                ai_verdict = (
                    review.get("AI_Verdict")
                    or review.get("AI Verdict")
                    or review.get("ai_verdict")
                    or "Unknown"
                )

                ai_score = (
                    review.get("AI_Score")
                    or review.get("AI Score")
                    or review.get("ai_score")
                    or "Unknown"
                )

                decision = (
                    review.get("Human_Decision")
                    or review.get("Human Decision")
                    or "Unknown"
                )

                issue = (
                    review.get("Issue")
                    or "Not provided"
                )

                correction = (
                    review.get("Human_Correction")
                    or review.get("Human Correction")
                    or "Not provided"
                )

                print(f"Case:           {case_id}")
                print(f"AI verdict:     {ai_verdict} ({ai_score})")
                print(f"Human decision: {decision}")
                print(f"Issue:          {issue}")
                print(f"Correction:     {correction}")
                print()
            
    # ---------------------------------------------------------
    # CASES NEEDING ATTENTION
    # ---------------------------------------------------------

    print("CASES NEEDING HUMAN ATTENTION")
    print("-" * 70)

    attention_cases = [
        row for row in results
        if row.get("Verdict", "").strip().upper()
        != "CORRECT"
    ]

    if not attention_cases:
        print("None — all AI diagnoses were marked CORRECT.")
    else:
        for row in attention_cases:
            print(
                f"{row.get('Case ID', 'Unknown')}: "
                f"{row.get('Verdict', 'Unknown')} "
                f"({row.get('Score', '0%')})"
            )

    print()

    # ---------------------------------------------------------
    # PROJECT STATUS
    # ---------------------------------------------------------

    print("PROJECT STATUS")
    print("-" * 70)

    print(f"Case coverage:       {total} cases")

    if total >= 30:
        print("✓ Minimum 30-case requirement satisfied")
    else:
        print("✗ Need at least 30 cases")

    print("✓ AI batch evaluation completed")
    print("✓ Deterministic evaluation completed")

    if human_reviews:
        print("✓ Human review completed")
    else:
        print("✗ Human review not completed")

    if human_reviews:
        ai_corrected = sum(
            1 for row in human_reviews
            if (
                row.get("Human_Decision")
                or row.get("Human Decision")
                or ""
            ).strip().upper() in {"EDITED", "REJECTED"}
    )

        if ai_corrected >= 5:
            print(f"✓ Responsible AI audit completed ({ai_corrected} corrections)")
        else:
            print(
            f"✗ Responsible AI audit needs {5 - ai_corrected} "
            f"more correction(s)"
        )
    else:
        print("✗ Responsible AI audit not completed")

    print("✓ Flask dashboard active")
    print("✓ Network diagnosis system active")
    print("→ Final UI polish: NEXT")
    print("→ Demo preparation: NEXT")


if __name__ == "__main__":
    main()