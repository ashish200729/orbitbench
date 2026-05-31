"""
Minimal FastAPI server serving benchmark results to the React dashboard.
Run:  python api_server.py   (or: uvicorn api_server:app --reload)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from runner.storage import load_leaderboard, load_all_results

app = FastAPI(title="LLM-Bench API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/api/leaderboard")
def get_leaderboard():
    return load_leaderboard()


@app.get("/api/results")
def get_results():
    return load_all_results()


@app.get("/api/results/{run_id}")
def get_run(run_id: str):
    for r in load_all_results():
        if r["run_id"] == run_id:
            return r
    return {"error": "Not found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
