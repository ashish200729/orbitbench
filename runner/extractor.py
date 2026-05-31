"""
Extracts clean, executable code from a raw model response.
Handles: fenced markdown blocks, raw code, prose+code, reasoning model
<think> blocks (DeepSeek R1, o1-style), and truncated responses.
"""
import re

_FENCE = re.compile(
    r"```(?:python|py|javascript|js|typescript|ts|go|golang|rust|rs|cpp|java)?\s*\n?([\s\S]*?)```",
    re.IGNORECASE,
)
_LAST_FENCE = re.compile(
    r"```(?:python|py|javascript|js|typescript|ts|go|golang|rust|rs|cpp|java)?\s*\n?([\s\S]*?)```",
    re.IGNORECASE,
)
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_THINK = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)

_CODE_START = re.compile(
    r"^\s*(def |class |function |fn |pub fn|import |from |package |#!|#include|@|async def)",
)
_CODE_DEF = re.compile(
    r"^(def |class |function |fn |pub fn|import |from |package )",
)


def _strip_think(text: str) -> str:
    stripped = _THINK.sub("", text).strip()
    if stripped:
        return stripped
    return text


def _strip_trailing_tags(code: str) -> str:
    lines = code.splitlines()
    result = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^</?\w+>$", stripped):
            continue
        result.append(line)
    return "\n".join(result).strip()


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text)


def _find_last_fence(text: str) -> str | None:
    matches = list(_LAST_FENCE.finditer(text))
    if not matches:
        return None
    return matches[-1].group(1).strip()


def _find_last_code_def(text: str) -> str | None:
    lines = text.strip().split("\n")
    best = -1
    for i, line in enumerate(lines):
        if _CODE_DEF.match(line):
            best = i
    if best >= 0:
        return "\n".join(lines[best:]).strip()
    return None


def extract_code(raw_response: str, language: str) -> str:
    if not raw_response or not raw_response.strip():
        return ""

    text = _strip_think(raw_response)

    matches = _FENCE.findall(text)
    if matches:
        code = max(matches, key=len).strip()
        return _strip_trailing_tags(code)

    code = _find_last_fence(text)
    if code:
        return _strip_trailing_tags(code)

    code = _find_last_code_def(text)
    if code:
        return _strip_trailing_tags(code)

    lines = text.strip().split("\n")
    for i, line in enumerate(lines):
        if _CODE_START.match(line):
            code = "\n".join(lines[i:]).strip()
            return _strip_trailing_tags(code)

    return text.strip()
