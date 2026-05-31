"""
Score calculation. Per-task score = tests_passed / total_tests * 100.
Final benchmark score = average of all task scores (out of 100). This is pass@1.
"""


def score_task(test_results: list[dict]) -> dict:
    total = len(test_results)
    if total == 0:
        return {"passed": 0, "total": 0, "score": 0.0, "pass_rate": "0/0"}
    passed = sum(1 for r in test_results if r.get("passed", False))
    return {
        "passed": passed,
        "total": total,
        "score": round((passed / total) * 100, 2),
        "pass_rate": f"{passed}/{total}",
    }


def calculate_benchmark_score(task_scores: list[dict]) -> float:
    if not task_scores:
        return 0.0
    return round(sum(t["score"] for t in task_scores) / len(task_scores), 2)
