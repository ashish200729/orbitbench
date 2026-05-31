"""
File I/O for attempts and results.

ISOLATION WALL 2: each model's attempts live under attempts/{model_id}/ only.
ISOLATION WALL 3: attempts are append-only and never read back into a prompt.
"""
import json
import os
from datetime import datetime, timezone

ATTEMPTS_DIR = "attempts"
RESULTS_DIR = "results"


def _sanitize(name: str) -> str:
    return name.replace("/", "_").replace(":", "_").replace(" ", "_")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_attempt(model_id, task_id, run_id, generated_code, test_results, task_score) -> str:
    model_dir = os.path.join(ATTEMPTS_DIR, _sanitize(model_id))
    os.makedirs(model_dir, exist_ok=True)
    attempt = {
        "task_id": task_id,
        "model_id": model_id,
        "run_id": run_id,
        "timestamp": _now(),
        "generated_code": generated_code,
        "test_results": test_results,
        "task_score": task_score,
    }
    path = os.path.join(model_dir, f"{task_id}_{run_id}.json")
    with open(path, "w") as f:
        json.dump(attempt, f, indent=2)
    return path


def save_run_results(run_id, model_id, task_results, final_score) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    result = {
        "run_id": run_id,
        "model_id": model_id,
        "timestamp": _now(),
        "final_score": final_score,
        "task_results": task_results,
        "summary": {
            "total_tasks": len(task_results),
            "tasks_passed_all": sum(1 for t in task_results if t["task_score"]["score"] == 100),
            "tasks_passed_some": sum(1 for t in task_results if 0 < t["task_score"]["score"] < 100),
            "tasks_failed_all": sum(1 for t in task_results if t["task_score"]["score"] == 0),
        },
    }
    path = os.path.join(RESULTS_DIR, f"{run_id}_results.json")
    with open(path, "w") as f:
        json.dump(result, f, indent=2)
    _update_leaderboard(model_id, run_id, final_score)
    return path


def _update_leaderboard(model_id, run_id, score):
    lb_path = os.path.join(RESULTS_DIR, "leaderboard.json")
    if os.path.exists(lb_path):
        with open(lb_path) as f:
            lb = json.load(f)
    else:
        lb = {"entries": []}
    lb["entries"].append(
        {"model_id": model_id, "run_id": run_id, "score": score, "timestamp": _now()}
    )
    lb["entries"].sort(key=lambda x: (-x["score"], x["timestamp"]))
    with open(lb_path, "w") as f:
        json.dump(lb, f, indent=2)


def load_leaderboard() -> dict:
    lb_path = os.path.join(RESULTS_DIR, "leaderboard.json")
    if not os.path.exists(lb_path):
        return {"entries": []}
    with open(lb_path) as f:
        return json.load(f)


def load_all_results() -> list:
    if not os.path.exists(RESULTS_DIR):
        return []
    results = []
    for fname in os.listdir(RESULTS_DIR):
        if fname.endswith("_results.json"):
            with open(os.path.join(RESULTS_DIR, fname)) as f:
                results.append(json.load(f))
    return sorted(results, key=lambda x: x["timestamp"], reverse=True)
