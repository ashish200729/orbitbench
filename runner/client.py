"""
OpenAI-compatible API client.
Reads OPENAI_API_KEY and OPENAI_BASE_URL from environment.

ISOLATION WALL 1: only the task description + function signature are sent.
Test cases and expected outputs are NEVER included in the prompt.
"""
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )


def generate_solution(
    client: OpenAI,
    model: str,
    task_description: str,
    language: str,
    function_signature: str,
    temperature: float = 0.0,
    max_tokens: int = 16000,
    seed: int | None = None,
) -> str:
    system_prompt = (
        f"You are an expert {language} programmer. Solve the problem below.\n"
        "CRITICAL: Be extremely concise in your reasoning. Output ONLY the raw code.\n"
        "No explanation, no markdown fences, no commentary.\n"
        "Start your response directly with the code."
    )
    user_prompt = (
        f"Write a {language} function with this signature:\n{function_signature}\n\n"
        f"Description:\n{task_description}\n\n"
        "Return ONLY the raw code. No explanation. No backticks. No markdown."
    )
    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if seed is not None:
        kwargs["seed"] = seed

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as e:
        raise RuntimeError(f"API call failed: {e}") from e

    if not response.choices:
        raise RuntimeError("API returned no choices")

    choice = response.choices[0]
    content = (choice.message.content or "").strip()

    if choice.finish_reason == "length":
        print(
            f"  [WARN] response truncated (finish_reason=length) — "
            f"consider raising max_tokens above {max_tokens}",
            file=sys.stderr,
        )

    if not content:
        reasoning = getattr(choice.message, "reasoning_content", None) or ""
        if reasoning.strip():
            print(
                "  [INFO] content empty, falling back to reasoning_content for extraction",
                file=sys.stderr,
            )
            return reasoning

    return content
