"""
Sandboxed code execution + hidden test runner.

Each generated solution is combined with a language-specific harness that runs
one hidden test case and prints a single JSON line:
    {"passed": bool, "result": "...", "expected": "...", "error": "..."}
Execution happens in a subprocess with a timeout. Test cases and expected
outputs are injected here ONLY — they never reach the model.

Supported: python, javascript, typescript (Node native type-stripping), go, rust.
"""
import json
import os
import re
import subprocess
import tempfile

TIMEOUT_SECONDS = int(os.environ.get("EXECUTION_TIMEOUT", "10"))


# --------------------------------------------------------------------------- #
# Source-embedding helper
# --------------------------------------------------------------------------- #
def _emit(value) -> str:
    """Return a source literal that json.loads / JSON.parse turns back into value."""
    return json.dumps(json.dumps(value))


def _names(pattern: str, signature: str) -> list[str]:
    return re.findall(pattern, signature)


# --------------------------------------------------------------------------- #
# Subprocess plumbing
# --------------------------------------------------------------------------- #
def _extract_json(stdout: str) -> dict | None:
    for line in reversed((stdout or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def _finalize(tc: dict, proc) -> dict:
    data = _extract_json(proc.stdout)
    if data is not None:
        return {
            "test_case_id": tc["id"],
            "passed": bool(data.get("passed", False)),
            "result": data.get("result"),
            "expected": data.get("expected", str(tc["expected_output"])),
            "error": data.get("error"),
        }
    err = (proc.stderr or "").strip()
    from runner.extractor import strip_ansi
    err = strip_ansi(err) or "Runtime error (no output)"
    return {"test_case_id": tc["id"], "passed": False, "error": err[:500]}


def _run_proc(cmd: list[str], tc: dict, cwd: str | None = None) -> dict:
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, cwd=cwd
        )
    except subprocess.TimeoutExpired:
        return {"test_case_id": tc["id"], "passed": False, "error": "Timeout exceeded"}
    except FileNotFoundError as e:
        return {"test_case_id": tc["id"], "passed": False, "error": f"Toolchain not found: {e}"}
    return _finalize(tc, proc)


def _run_script(source: str, cmd_prefix: list[str], suffix: str, tc: dict) -> dict:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w") as f:
        f.write(source)
    try:
        return _run_proc(cmd_prefix + [path], tc)
    finally:
        os.unlink(path)


# --------------------------------------------------------------------------- #
# Python
# --------------------------------------------------------------------------- #
_PY_FUNC = """import json
__CODE__

def _run():
    test_input = json.loads(__INPUT__)
    expected = json.loads(__EXPECTED__)
    fn = __ENTRY__
    result = fn(**test_input) if isinstance(test_input, dict) else fn(test_input)
    print(json.dumps({"passed": result == expected,
                      "result": str(result)[:300], "expected": str(expected)[:300]}))

try:
    _run()
except Exception as e:
    print(json.dumps({"passed": False, "error": repr(e)[:300]}))
"""

# For Python class-based tasks: capacity + operations -> list of get results
_PY_CLASS = """import json
__CODE__

def _run():
    test_input = json.loads(__INPUT__)
    expected = json.loads(__EXPECTED__)
    capacity = test_input["capacity"]
    operations = test_input["operations"]
    obj = __CLASS__(capacity)
    out = []
    for op in operations:
        method = op[0]
        args = op[1:]
        r = getattr(obj, method)(*args)
        if r is not None:
            out.append(r)
    print(json.dumps({"passed": out == expected,
                      "result": str(out)[:300], "expected": str(expected)[:300]}))

try:
    _run()
except Exception as e:
    print(json.dumps({"passed": False, "error": repr(e)[:300]}))
"""

_PY_TREE = """import json
__CODE__

def _build_tree(vals):
    if not vals:
        return None
    it = iter(vals)
    root = TreeNode(next(it))
    q = [root]
    while q:
        node = q.pop(0)
        try:
            v = next(it)
        except StopIteration:
            break
        if v is not None:
            node.left = TreeNode(v); q.append(node.left)
        try:
            v = next(it)
        except StopIteration:
            break
        if v is not None:
            node.right = TreeNode(v); q.append(node.right)
    return root

def _to_list(root):
    out, q = [], [root]
    while q:
        n = q.pop(0)
        if n is None:
            out.append(None); continue
        out.append(n.val); q.append(n.left); q.append(n.right)
    while out and out[-1] is None:
        out.pop()
    return out

def _run():
    data = json.loads(__INPUT__)
    expected = json.loads(__EXPECTED__)
    s = serialize(_build_tree(data["tree"]))
    if not isinstance(s, str):
        raise TypeError("serialize must return a string")
    result = _to_list(deserialize(s))
    print(json.dumps({"passed": result == expected,
                      "result": str(result)[:300], "expected": str(expected)[:300]}))

try:
    _run()
except Exception as e:
    print(json.dumps({"passed": False, "error": repr(e)[:300]}))
"""


def run_python_tests(code: str, test_cases: list[dict], signature: str) -> list[dict]:
    entries = _names(r"def\s+(\w+)\s*\(", signature)
    classes = _names(r"class\s+(\w+)", signature)
    tree_mode = "serialize" in entries and "deserialize" in entries
    class_mode = bool(classes) and not tree_mode and all(
        "capacity" in tc.get("input", {}) for tc in test_cases
    )

    if tree_mode:
        template = _PY_TREE
        entry = entries[0] if entries else "solution"
    elif class_mode:
        template = _PY_CLASS
        entry = classes[0]
    else:
        template = _PY_FUNC
        entry = entries[0] if entries else "solution"

    results = []
    for tc in test_cases:
        source = (
            template.replace("__CODE__", code)
            .replace("__CLASS__", entry)
            .replace("__ENTRY__", entry)
            .replace("__INPUT__", _emit(tc["input"]))
            .replace("__EXPECTED__", _emit(tc["expected_output"]))
        )
        results.append(_run_script(source, ["python3"], ".py", tc))
    return results


# --------------------------------------------------------------------------- #
# JavaScript / TypeScript  (Node 18+; Node 22.6+ strips TS types natively)
# --------------------------------------------------------------------------- #
_JS_HARNESS = """
__CODE__

;(function () {
  try {
    var input = JSON.parse(__INPUT__);
    var expected = JSON.parse(__EXPECTED__);
    var out;
    if (input && input.operations) {
      var inst = (input.capacity !== undefined) ? new __CLASS__(input.capacity) : new __CLASS__();
      out = [];
      for (var i = 0; i < input.operations.length; i++) {
        var op = input.operations[i];
        var r = inst[op[0]].apply(inst, op.slice(1));
        if (r !== undefined) out.push(r);
      }
    } else {
      out = __ENTRY__.apply(null, Object.values(input));
    }
    var passed = JSON.stringify(out) === JSON.stringify(expected);
    console.log(JSON.stringify({ passed: passed,
      result: JSON.stringify(out), expected: JSON.stringify(expected) }));
  } catch (e) {
    console.log(JSON.stringify({ passed: false, error: String((e && e.message) || e).slice(0, 300) }));
  }
})();
"""


_JS_RESERVED = {"constructor", "get", "put", "postTweet", "getNewsFeed", "follow", "unfollow"}

def _run_node_tests(code, test_cases, signature, suffix):
    cls = _names(r"class\s+(\w+)", signature)
    fn = [f for f in (_names(r"function\s+(\w+)", signature) or []) if f not in _JS_RESERVED]
    if not fn:
        fn = [f for f in (_names(r"(\w+)\s*\(", signature) or []) if f not in _JS_RESERVED]
    class_name = cls[0] if cls else (fn[0] if fn else "Solution")
    entry = class_name if cls else (fn[0] if fn else class_name)
    results = []
    for tc in test_cases:
        source = (
            _JS_HARNESS.replace("__CODE__", code)
            .replace("__CLASS__", class_name)
            .replace("__ENTRY__", entry)
            .replace("__INPUT__", _emit(tc["input"]))
            .replace("__EXPECTED__", _emit(tc["expected_output"]))
        )
        results.append(_run_script(source, ["node"], suffix, tc))
    return results


def run_javascript_tests(code, test_cases, signature):
    return _run_node_tests(code, test_cases, signature, ".js")


def run_typescript_tests(code, test_cases, signature):
    return _run_node_tests(code, test_cases, signature, ".ts")


# --------------------------------------------------------------------------- #
# Go  (signature-driven: json.Unmarshal each arg into its declared type,
#      compare with reflect.DeepEqual. The solution lives in its own file so a
#      model may bring its own imports without clashing with the harness.)
# --------------------------------------------------------------------------- #
_GO_MAIN = """package main

import (
\t"encoding/json"
\t"fmt"
\t"reflect"
)

func main() {
__DECLS__
\tresult := __ENTRY__(__ARGS__)
\tvar expected __RET__
\t_ = json.Unmarshal([]byte(`__EXPECTED__`), &expected)
\tpassed := reflect.DeepEqual(result, expected)
\tfmt.Printf("{\\"passed\\": %v, \\"result\\": %q, \\"expected\\": %q}\\n", passed, fmt.Sprint(result), fmt.Sprint(expected))
}
"""


def _parse_go_sig(signature: str):
    m = re.search(r"func\s+(\w+)\s*\((.*)\)\s*([^\{]*)", signature.strip())
    name = m.group(1)
    params = []
    raw = m.group(2).strip()
    if raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        i = 0
        while i < len(parts):
            toks = parts[i].split()
            if len(toks) > 1:
                params.append((toks[0], " ".join(toks[1:])))
                i += 1
            else:
                nameless = [toks[0]]
                i += 1
                while i < len(parts):
                    ntoks = parts[i].split()
                    if len(ntoks) > 1:
                        ptype = " ".join(ntoks[1:])
                        for n in nameless:
                            params.append((n, ptype))
                        params.append((ntoks[0], ptype))
                        break
                    else:
                        nameless.append(ntoks[0])
                    i += 1
                i += 1
    ret = m.group(3).strip()
    return name, params, ret


def run_go_tests(code, test_cases, signature):
    name, params, ret = _parse_go_sig(signature)
    code = re.sub(r"^\s*package\s+\w+\s*$", "", code, flags=re.M)
    results = []
    for tc in test_cases:
        decls = "\n".join(
            f"\tvar {p} {t}\n\t_ = json.Unmarshal([]byte(`{json.dumps(tc['input'].get(p))}`), &{p})"
            for p, t in params
        )
        main_src = (
            _GO_MAIN.replace("__DECLS__", decls)
            .replace("__ENTRY__", name)
            .replace("__ARGS__", ", ".join(p for p, _ in params))
            .replace("__RET__", ret)
            .replace("__EXPECTED__", json.dumps(tc["expected_output"]))
        )
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "solution.go"), "w") as f:
                f.write("package main\n\n" + code)
            with open(os.path.join(d, "main.go"), "w") as f:
                f.write(main_src)
            results.append(_run_proc(["go", "run", "solution.go", "main.go"], tc, cwd=d))
    return results


# --------------------------------------------------------------------------- #
# Rust  (signature-driven: emit typed literals for each arg/expected from the
#        parsed parameter types, compare with == or an epsilon for floats.)
# --------------------------------------------------------------------------- #
_RUST_HARNESS = """__CODE__

fn main() {
__LETS__
    let expected: __RET__ = __EXPECTED__;
    let result = __ENTRY__(__ARGS__);
    let passed = __CMP__;
    println!("{{\\"passed\\": {}, \\"result\\": \\"{:?}\\", \\"expected\\": \\"{:?}\\"}}", passed, result, expected);
}
"""


def _parse_rust_sig(signature: str):
    m = re.search(r"(?:pub\s+)?fn\s+(\w+)\s*\((.*?)\)\s*(?:->\s*([^\{]+))?", signature.strip())
    name = m.group(1)
    params = []
    raw = (m.group(2) or "").strip()
    if raw:
        for part in raw.split(","):
            pn, pt = part.split(":", 1)
            params.append((pn.strip(), pt.strip()))
    ret = (m.group(3) or "()").strip()
    return name, params, ret


def _rust_lit(value, rtype: str) -> str:
    rtype = rtype.strip()
    if rtype.startswith("Vec<"):
        inner = rtype[4:-1]
        return "vec![" + ", ".join(_rust_lit(x, inner) for x in value) + "]"
    if rtype in ("i8", "i16", "i32", "i64", "u32", "u64", "usize", "isize"):
        return str(int(value))
    if rtype in ("f64", "f32"):
        return repr(float(value))
    if rtype == "bool":
        return "true" if value else "false"
    if rtype == "String":
        return f"{json.dumps(value)}.to_string()"
    if rtype == "char":
        return f"'{value}'"
    return json.dumps(value)  # &str and fallback


def run_rust_tests(code, test_cases, signature):
    name, params, ret = _parse_rust_sig(signature)
    cmp = "(result - expected).abs() < 1e-6" if ret in ("f64", "f32") else "result == expected"
    results = []
    for tc in test_cases:
        lets = "\n".join(
            f"    let {p}: {t} = {_rust_lit(tc['input'].get(p), t)};" for p, t in params
        )
        source = (
            _RUST_HARNESS.replace("__CODE__", code)
            .replace("__LETS__", lets)
            .replace("__ENTRY__", name)
            .replace("__ARGS__", ", ".join(p for p, _ in params))
            .replace("__RET__", ret)
            .replace("__CMP__", cmp)
            .replace("__EXPECTED__", _rust_lit(tc["expected_output"], ret))
        )
        results.append(_compile_run_rust(source, tc))
    return results


def _compile_run_rust(source: str, tc: dict) -> dict:
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "main.rs")
        binp = os.path.join(d, "main_bin")
        with open(src, "w") as f:
            f.write(source)
        try:
            comp = subprocess.run(
                ["rustc", "-O", src, "-o", binp],
                capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return {"test_case_id": tc["id"], "passed": False, "error": "Compile timeout"}
        except FileNotFoundError:
            return {"test_case_id": tc["id"], "passed": False, "error": "rustc not found"}
        if comp.returncode != 0:
            return {"test_case_id": tc["id"], "passed": False, "error": comp.stderr[:500]}
        return _run_proc([binp], tc, cwd=d)


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #
_DISPATCH = {
    "python": run_python_tests,
    "javascript": run_javascript_tests,
    "typescript": run_typescript_tests,
    "go": run_go_tests,
    "rust": run_rust_tests,
}


def execute_task(task: dict, generated_code: str) -> list[dict]:
    """Route to the language runner and return per-test-case results."""
    runner = _DISPATCH.get(task["language"])
    if not runner:
        return [
            {"test_case_id": tc["id"], "passed": False,
             "error": f"Language {task['language']} executor not implemented"}
            for tc in task["test_cases"]
        ]
    if not (generated_code or "").strip():
        return [
            {"test_case_id": tc["id"], "passed": False, "error": "Empty solution"}
            for tc in task["test_cases"]
        ]
    return runner(generated_code, task["test_cases"], task["function_signature"])
