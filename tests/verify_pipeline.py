"""
End-to-end pipeline test WITHOUT a real LLM. We stub only the network call
(generate_solution) with known-correct reference code, so the REAL orchestrator,
extractor, executor, scorer, isolated storage, and leaderboard are all exercised.
Run: python -m tests.verify_pipeline
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "dummy-key-not-used-offline")

import runner.benchmark as B
from tests.verify_executor import REFERENCE


def main():
    tasks = B.load_tasks()
    sig_to_id = {t["function_signature"]: t["id"] for t in tasks}

    def fake_generate(client, model, task_description, language, function_signature, **kw):
        # Returned as if it were a raw model response (extractor still runs on it).
        return REFERENCE[sig_to_id[function_signature]]

    B.generate_solution = fake_generate  # stub the only network boundary

    result = B.run_benchmark("reference-solver/v1", verbose=True)
    ok = result["final_score"] == 100.0
    print(f"PIPELINE {'OK' if ok else 'FAILED'}: {result['run_id']} -> {result['final_score']}/100")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
