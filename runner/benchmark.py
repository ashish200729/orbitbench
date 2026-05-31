"""
Main benchmark orchestrator.

ISOLATION GUARANTEES
  Wall 1: only task description + function signature are sent to the model.
  Wall 2: each model's attempts are saved under attempts/{model_id}/ only.
  Wall 3: each run is fresh; no prior attempt is ever fed back to the model.
"""
import json
import os
import uuid
from datetime import datetime

from runner.client import get_client, generate_solution
from runner.extractor import extract_code
from runner.executor import execute_task
from runner.scorer import score_task, calculate_benchmark_score
from runner.storage import save_attempt, save_run_results


def _config() -> dict:
    try:
        with open("config.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _cfg(key: str, default):
    cfg = _config()
    return os.environ.get(key.upper()) or cfg.get(key, default)


def load_tasks() -> list[dict]:
    tasks_dir = _cfg("tasks_dir", "tasks")
    tasks = []
    for fname in sorted(os.listdir(tasks_dir)):
        if fname.endswith(".json"):
            with open(os.path.join(tasks_dir, fname)) as f:
                tasks.append(json.load(f))
    return tasks


def _empty_score(task: dict) -> dict:
    n = len(task["test_cases"])
    return {"passed": 0, "total": n, "score": 0.0, "pass_rate": f"0/{n}"}


def run_benchmark(model_id: str, verbose: bool = True) -> dict:
    cfg = _config()
    client = get_client()
    tasks = load_tasks()
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    seed = cfg.get("seed")

    if verbose:
        print(f"\n{'=' * 60}\nOrbitBench Run: {run_id}")
        print(f"Model: {model_id}")
        print(f"Seed: {seed}  |  Temp: {cfg.get('default_temperature', 0.0)}")
        print(f"Tasks: {len(tasks)}\n{'=' * 60}\n")

    all_task_results = []
    for i, task in enumerate(tasks, 1):
        if verbose:
            print(f"[{i}/{len(tasks)}] {task['id']} — {task['title']} ({task['language']}, {task['difficulty']})")

        try:
            raw = generate_solution(
                client=client,
                model=model_id,
                task_description=task["description"],
                language=task["language"],
                function_signature=task["function_signature"],
                temperature=cfg.get("default_temperature", 0.0),
                max_tokens=cfg.get("max_tokens", 16000),
                seed=seed,
            )
            generated_code = extract_code(raw, task["language"])
            test_results = execute_task(task, generated_code)
            task_score = score_task(test_results)
        except Exception as e:
            if verbose:
                print(f"  ERROR: {e}")
            all_task_results.append({
                "task_id": task["id"], "task_title": task["title"],
                "language": task["language"], "difficulty": task["difficulty"],
                "generated_code": "", "test_results": [],
                "task_score": _empty_score(task), "error": str(e),
            })
            continue

        if verbose:
            print(f"  Score: {task_score['score']}/100 ({task_score['pass_rate']} tests passed)")

        save_attempt(model_id, task["id"], run_id, generated_code, test_results, task_score)
        all_task_results.append({
            "task_id": task["id"], "task_title": task["title"],
            "language": task["language"], "difficulty": task["difficulty"],
            "generated_code": generated_code, "test_results": test_results,
            "task_score": task_score,
        })

    final_score = calculate_benchmark_score([t["task_score"] for t in all_task_results])
    if verbose:
        print(f"\n{'=' * 60}\nFINAL BENCHMARK SCORE: {final_score}/100\n{'=' * 60}\n")

    save_run_results(run_id, model_id, all_task_results, final_score)
    return {
        "run_id": run_id,
        "model_id": model_id,
        "final_score": final_score,
        "task_results": all_task_results,
    }
