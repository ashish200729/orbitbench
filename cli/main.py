"""
CLI entry point for LLM-Bench.

  python -m cli.main run --model gpt-4o
  python -m cli.main leaderboard
  python -m cli.main results
"""
import argparse

from runner.benchmark import run_benchmark
from runner.storage import load_leaderboard, load_all_results


def cmd_run(args):
    result = run_benchmark(model_id=args.model, verbose=True)
    print(f"Run complete. Score: {result['final_score']}/100")


def cmd_leaderboard(args):
    lb = load_leaderboard()
    if not lb["entries"]:
        print("No runs yet.")
        return
    print(f"\n{'Rank':<6}{'Model':<32}{'Score':<10}{'Run ID'}")
    print("-" * 70)
    for i, e in enumerate(lb["entries"], 1):
        print(f"{i:<6}{e['model_id']:<32}{e['score']:<10}{e['run_id']}")


def cmd_results(args):
    results = load_all_results()
    if not results:
        print("No results yet.")
        return
    for r in results[:5]:
        print(f"\nRun: {r['run_id']}")
        print(f"Model: {r['model_id']} | Score: {r['final_score']}/100")
        for t in r["task_results"]:
            score = t["task_score"]["score"]
            filled = int(score / 10)
            bar = "#" * filled + "-" * (10 - filled)
            print(f"  {t['task_id']} [{bar}] {score:>5}/100 ({t['language']}, {t['difficulty']})")


def main():
    parser = argparse.ArgumentParser(description="LLM-Bench: Code Generation Benchmark")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="Run benchmark on a model")
    p_run.add_argument("--model", required=True, help="Model ID (e.g. gpt-4o)")
    p_run.set_defaults(func=cmd_run)

    sub.add_parser("leaderboard", help="Show leaderboard").set_defaults(func=cmd_leaderboard)
    sub.add_parser("results", help="Show recent results").set_defaults(func=cmd_results)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
