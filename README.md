# LLM-Bench

An automated, multi-language code-generation benchmark for LLMs. It sends each
task to a model (via any OpenAI-compatible API), extracts the generated code,
runs it against **hidden** test cases in an isolated subprocess, and produces a
final score out of 100 — using **pass@1**, the same methodology as HumanEval and
LiveCodeBench.

To benchmark a model you only set three things: **API key**, **base URL**, and
**model name**. Runs can be triggered from the **CLI** or the **web dashboard**.

## How it works

1. Tasks live in `tasks/` — each has a description and hidden test cases.
2. The model receives **only** the task description + function signature.
3. The generated code is extracted and run against the test cases.
4. Every attempt is saved in isolation under `attempts/{model_id}/`.
5. Score per task = `tests_passed / total_tests * 100`.
   Final score = average of all task scores, out of 100.

## The three isolation walls

- **Wall 1 — Hidden answers.** Only the task description and function signature
  are sent to the model (`runner/client.py`). Test cases and expected outputs
  are injected only inside the executor and never appear in any prompt.
- **Wall 2 — Per-model isolation.** Each model's attempts are written to
  `attempts/{model_id}/` and are never read by another model.
- **Wall 3 — Fresh runs.** Attempts are append-only and are never fed back into a
  prompt. Each run is fully independent.

## Task bank (8 hard tasks, ~103 hidden tests)

These are deliberately **correctness-brutal** problems, not the most-practiced
canonical ones. The most-solved problems on the internet (Two Sum, Max Subarray,
LRU, etc.) are heavily memorized by models, so they measure recall, not ability.
Here the difficulty lives in the **edge cases** (operator precedence and
truncating division, `a*` matching empty, DP base-case initialization, duplicate
chars in sliding window, same-char interval merging), and each task ships with an
exhaustive hidden test suite that catches sloppy or partial solutions.

| ID | Title | Language | Difficulty | Source |
|----|-------|----------|------------|--------|
| 001 | Expression Evaluator (precedence + unary, trunc division) | Python | hard | LeetCode #772 variant |
| 002 | LRU Cache with TTL Expiry | Python | hard | Custom — LRU + TTL combined |
| 003 | LFU Cache | JavaScript | hard | LeetCode #460 |
| 004 | Design Twitter | TypeScript | hard | LeetCode #355 |
| 005 | Edit Distance on RLE-Encoded Strings | Python | hard | Custom — edit distance + RLE |
| 006 | Sliding Window Median | Python | hard | LeetCode #480 variant |
| 007 | Weighted Job Scheduling with Cooldown | Python | hard | Custom — job scheduling + cooldown |
| 008 | Matrix Chain with Forbidden Splits | Python | hard | Custom — matrix chain + constraints |

> Tasks 002/005/007/008 are **custom multi-constraint problems** not found verbatim
> on any competitive programming platform — they combine two well-known algorithms
> in non-obvious ways, requiring genuine reasoning rather than pattern recall.
> For full contamination resistance over time, rotate in fresh problems published
> after a model's training cutoff (the LiveCodeBench approach).

## Requirements

- Python 3.10+
- Language toolchains for the tasks you want to run:
  - `node` 22.6+ (runs JavaScript **and** TypeScript directly via native type-stripping — no `tsc`/`ts-node` needed)
  - `go`
  - `rustc`

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in OPENAI_API_KEY and OPENAI_BASE_URL in .env
```

`.env`:

```env
OPENAI_API_KEY=your_private_api_key_here
OPENAI_BASE_URL=https://your-custom-base-url/v1
EXECUTION_TIMEOUT=10   # optional, seconds per test case
```

## Run a benchmark (CLI)

```bash
python3 -m cli.main run --model gpt-4o
python3 -m cli.main leaderboard
python3 -m cli.main results
```

## Web dashboard

Start the API, then the dashboard:

```bash
python api_server.py                 # http://localhost:8000
cd dashboard && npm install && npm run dev   # http://localhost:5173
```

The dashboard shows the final ScoreCard, Leaderboard, per-task breakdown, and run
history. It polls the API every 5 seconds, so scores appear live as a run
progresses.

## Scoring example

```
Task 001  8/8  -> 100.0     Task 005  3/3  -> 100.0
Task 002  5/7  ->  71.4     Task 006  4/5  ->  80.0
Task 003  2/3  ->  66.7     Task 007  3/5  ->  60.0
Task 004  6/7  ->  85.7     Task 008  5/6  ->  83.3
Final = average = 80.9 / 100
```

## Project structure

```
runner/      client, extractor, executor, scorer, storage, benchmark
cli/         CLI entry point
tasks/       8 task definitions with hidden test cases
attempts/    per-model, append-only attempt records (generated)
results/     per-run results + leaderboard.json (generated)
dashboard/   React + Vite dashboard (4 components)
tests/       executor + pipeline self-tests
api_server.py
```

## Tests

These prove the harness and pipeline work without spending API credits — they run
known-correct reference solutions through the **real** executor and orchestrator:

```bash
python -m tests.verify_executor   # all 5 languages -> 100/100
python -m tests.verify_pipeline   # full orchestrator + isolated storage -> 100/100
```

## Adding a model to compare

No code changes — just run again with a different `--model`. Each model is scored
independently and ranked on the leaderboard.
# orbitbench
