#!/usr/bin/env python3
"""Persistent mini-REPL for RLM-style workflows in OpenCode.

This script provides a *stateful* Python environment across invocations by
saving a pickle file to disk. It is intentionally small and dependency-free.

Designed for SRE/DevOps workflows: analyzing logs, configs, manifests, etc.

Typical flow:
  1) Initialize context:
       python rlm_repl.py init path/to/large-file.log
  2) Execute code repeatedly (state persists):
       python rlm_repl.py exec -c 'print(len(content))'
       python rlm_repl.py exec <<'PYCODE'
       # multi-line code
       hits = grep('ERROR')
       print(hits[:3])
       PYCODE

The script injects these variables into the exec environment:
  - context: dict with keys {path, loaded_at, content}
  - content: string alias for context['content']
  - buffers: list[str] for storing intermediate text results

It also injects helpers:
  - peek(start=0, end=1000) -> str
  - grep(pattern, max_matches=20, window=120, flags=0) -> list[dict]
  - grep_count(pattern, flags=0) -> int
  - chunk_indices(size=200000, overlap=0) -> list[(start,end)]
  - write_chunks(out_dir, size=200000, overlap=0, prefix='chunk') -> list[str]
  - add_buffer(text: str) -> None
  - find_lines(pattern, max_matches=100) -> list[dict]
  - extract_json_objects(max_objects=50) -> list[dict]
  - extract_yaml_documents(max_docs=50) -> list[str]
  - time_range() -> dict (for log analysis)

Security note:
  This runs arbitrary Python via exec. Treat it like running code you wrote.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import pickle
import re
import sys
import textwrap
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_STATE_PATH = Path(".opencode/rlm_state/state.pkl")
DEFAULT_MAX_OUTPUT_CHARS = 8000


class RlmReplError(RuntimeError):
    pass


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_state(state_path: Path) -> Dict[str, Any]:
    if not state_path.exists():
        raise RlmReplError(
            f"No state found at {state_path}. Run: python rlm_repl.py init <context_path>"
        )
    with state_path.open("rb") as f:
        state = pickle.load(f)
    if not isinstance(state, dict):
        raise RlmReplError(f"Corrupt state file: {state_path}")
    return state


def _save_state(state: Dict[str, Any], state_path: Path) -> None:
    _ensure_parent_dir(state_path)
    tmp_path = state_path.with_suffix(state_path.suffix + ".tmp")
    with tmp_path.open("wb") as f:
        pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp_path.replace(state_path)


def _read_text_file(path: Path, max_bytes: int | None = None) -> str:
    if not path.exists():
        raise RlmReplError(f"Context file does not exist: {path}")
    data: bytes
    with path.open("rb") as f:
        data = f.read() if max_bytes is None else f.read(max_bytes)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        # Fall back to a lossy decode that will not crash.
        return data.decode("utf-8", errors="replace")


def _truncate(s: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + f"\n... [truncated to {max_chars} chars] ...\n"


def _is_pickleable(value: Any) -> bool:
    try:
        pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        return True
    except Exception:
        return False


def _filter_pickleable(d: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    kept: Dict[str, Any] = {}
    dropped: List[str] = []
    for k, v in d.items():
        if _is_pickleable(v):
            kept[k] = v
        else:
            dropped.append(k)
    return kept, dropped


def _make_helpers(context_ref: Dict[str, Any], buffers_ref: List[str]):
    """Create helper functions that close over context_ref/buffers_ref."""
    
    def peek(start: int = 0, end: int = 1000) -> str:
        """Return a slice of the content."""
        content = context_ref.get("content", "")
        return content[start:end]

    def grep(
        pattern: str,
        max_matches: int = 20,
        window: int = 120,
        flags: int = 0,
    ) -> List[Dict[str, Any]]:
        """Search for pattern in content, return matches with context."""
        content = context_ref.get("content", "")
        out: List[Dict[str, Any]] = []
        for m in re.finditer(pattern, content, flags):
            start, end = m.span()
            snippet_start = max(0, start - window)
            snippet_end = min(len(content), end + window)
            out.append(
                {
                    "match": m.group(0),
                    "span": (start, end),
                    "snippet": content[snippet_start:snippet_end],
                }
            )
            if len(out) >= max_matches:
                break
        return out

    def grep_count(pattern: str, flags: int = 0) -> int:
        """Count occurrences of pattern in content."""
        content = context_ref.get("content", "")
        return len(re.findall(pattern, content, flags))

    def find_lines(
        pattern: str,
        max_matches: int = 100,
        flags: int = 0,
    ) -> List[Dict[str, Any]]:
        """Find lines matching pattern, return with line numbers."""
        content = context_ref.get("content", "")
        lines = content.splitlines()
        out: List[Dict[str, Any]] = []
        regex = re.compile(pattern, flags)
        for i, line in enumerate(lines, 1):
            if regex.search(line):
                out.append({
                    "line_number": i,
                    "content": line,
                })
                if len(out) >= max_matches:
                    break
        return out

    def chunk_indices(size: int = 200_000, overlap: int = 0) -> List[Tuple[int, int]]:
        """Calculate chunk boundaries for the content."""
        if size <= 0:
            raise ValueError("size must be > 0")
        if overlap < 0:
            raise ValueError("overlap must be >= 0")
        if overlap >= size:
            raise ValueError("overlap must be < size")

        content = context_ref.get("content", "")
        n = len(content)
        spans: List[Tuple[int, int]] = []
        step = size - overlap
        for start in range(0, n, step):
            end = min(n, start + size)
            spans.append((start, end))
            if end >= n:
                break
        return spans

    def write_chunks(
        out_dir: str | os.PathLike,
        size: int = 200_000,
        overlap: int = 0,
        prefix: str = "chunk",
        encoding: str = "utf-8",
    ) -> List[str]:
        """Write content chunks to files and return paths."""
        content = context_ref.get("content", "")
        spans = chunk_indices(size=size, overlap=overlap)
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        paths: List[str] = []
        for i, (s, e) in enumerate(spans):
            p = out_path / f"{prefix}_{i:04d}.txt"
            p.write_text(content[s:e], encoding=encoding)
            paths.append(str(p))
        return paths

    def add_buffer(text: str) -> None:
        """Add text to the buffers list for later synthesis."""
        buffers_ref.append(str(text))

    def extract_json_objects(max_objects: int = 50) -> List[Dict[str, Any]]:
        """Extract JSON objects from content (useful for JSONL logs)."""
        content = context_ref.get("content", "")
        objects: List[Dict[str, Any]] = []
        # Try line-by-line first (JSONL format)
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    obj = json.loads(line)
                    objects.append(obj)
                    if len(objects) >= max_objects:
                        break
                except json.JSONDecodeError:
                    continue
        return objects

    def extract_yaml_documents(max_docs: int = 50) -> List[str]:
        """Split YAML content into documents (separated by ---)."""
        content = context_ref.get("content", "")
        docs = re.split(r'^---\s*$', content, flags=re.MULTILINE)
        return [d.strip() for d in docs[:max_docs] if d.strip()]

    def time_range() -> Dict[str, Optional[str]]:
        """Try to extract time range from log content."""
        content = context_ref.get("content", "")
        # Common timestamp patterns
        patterns = [
            r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',  # ISO format
            r'\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}',    # Apache format
            r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}',    # Syslog format
        ]
        
        first_ts = None
        last_ts = None
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            if matches:
                first_ts = matches[0]
                last_ts = matches[-1]
                break
        
        return {"first": first_ts, "last": last_ts}

    def stats() -> Dict[str, Any]:
        """Return basic statistics about the loaded content."""
        content = context_ref.get("content", "")
        lines = content.splitlines()
        return {
            "total_chars": len(content),
            "total_lines": len(lines),
            "avg_line_length": len(content) // max(len(lines), 1),
            "error_count": len(re.findall(r'\b(ERROR|FATAL|CRITICAL)\b', content, re.I)),
            "warning_count": len(re.findall(r'\bWARN(ING)?\b', content, re.I)),
        }

    return {
        "peek": peek,
        "grep": grep,
        "grep_count": grep_count,
        "find_lines": find_lines,
        "chunk_indices": chunk_indices,
        "write_chunks": write_chunks,
        "add_buffer": add_buffer,
        "extract_json_objects": extract_json_objects,
        "extract_yaml_documents": extract_yaml_documents,
        "time_range": time_range,
        "stats": stats,
    }


def cmd_init(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    ctx_path = Path(args.context)

    content = _read_text_file(ctx_path, max_bytes=args.max_bytes)
    state: Dict[str, Any] = {
        "version": 1,
        "context": {
            "path": str(ctx_path),
            "loaded_at": time.time(),
            "content": content,
        },
        "buffers": [],
        "globals": {},
    }
    _save_state(state, state_path)

    print(f"Initialized RLM REPL state at: {state_path}")
    print(f"Loaded context: {ctx_path} ({len(content):,} chars)")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = _load_state(Path(args.state))
    ctx = state.get("context", {})
    content = ctx.get("content", "")
    buffers = state.get("buffers", [])
    g = state.get("globals", {})

    print("RLM REPL status")
    print(f"  State file: {args.state}")
    print(f"  Context path: {ctx.get('path')}")
    print(f"  Context chars: {len(content):,}")
    print(f"  Context lines: {len(content.splitlines()):,}")
    print(f"  Buffers: {len(buffers)}")
    print(f"  Persisted vars: {len(g)}")
    if args.show_vars and g:
        for k in sorted(g.keys()):
            print(f"    - {k}")
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    if state_path.exists():
        state_path.unlink()
        print(f"Deleted state: {state_path}")
    else:
        print(f"No state to delete at: {state_path}")
    
    # Also clean up chunks directory
    chunks_dir = state_path.parent / "chunks"
    if chunks_dir.exists():
        import shutil
        shutil.rmtree(chunks_dir)
        print(f"Deleted chunks directory: {chunks_dir}")
    return 0


def cmd_export_buffers(args: argparse.Namespace) -> int:
    state = _load_state(Path(args.state))
    buffers = state.get("buffers", [])
    out_path = Path(args.out)
    _ensure_parent_dir(out_path)
    out_path.write_text("\n\n".join(str(b) for b in buffers), encoding="utf-8")
    print(f"Wrote {len(buffers)} buffers to: {out_path}")
    return 0


def cmd_exec(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    state = _load_state(state_path)

    ctx = state.get("context")
    if not isinstance(ctx, dict) or "content" not in ctx:
        raise RlmReplError("State is missing a valid 'context'. Re-run init.")

    buffers = state.setdefault("buffers", [])
    if not isinstance(buffers, list):
        buffers = []
        state["buffers"] = buffers

    persisted = state.setdefault("globals", {})
    if not isinstance(persisted, dict):
        persisted = {}
        state["globals"] = persisted

    code = args.code
    if code is None:
        code = sys.stdin.read()

    # Build execution environment.
    # Start from persisted variables, then inject context, buffers and helpers.
    env: Dict[str, Any] = dict(persisted)
    env["context"] = ctx
    env["content"] = ctx.get("content", "")
    env["buffers"] = buffers

    helpers = _make_helpers(ctx, buffers)
    env.update(helpers)

    # Capture output.
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    try:
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            exec(code, env, env)
    except Exception:
        traceback.print_exc(file=stderr_buf)

    # Pull back possibly mutated context/buffers.
    maybe_ctx = env.get("context")
    if isinstance(maybe_ctx, dict) and "content" in maybe_ctx:
        state["context"] = maybe_ctx
        ctx = maybe_ctx

    maybe_buffers = env.get("buffers")
    if isinstance(maybe_buffers, list):
        state["buffers"] = maybe_buffers
        buffers = maybe_buffers

    # Persist any new variables, excluding injected keys.
    injected_keys = {
        "__builtins__",
        "context",
        "content",
        "buffers",
        *helpers.keys(),
    }
    to_persist = {k: v for k, v in env.items() if k not in injected_keys}
    filtered, dropped = _filter_pickleable(to_persist)
    state["globals"] = filtered

    _save_state(state, state_path)

    out = stdout_buf.getvalue()
    err = stderr_buf.getvalue()

    if dropped and args.warn_unpickleable:
        msg = "Dropped unpickleable variables: " + ", ".join(dropped)
        err = (err + ("\n" if err else "") + msg + "\n")

    if out:
        sys.stdout.write(_truncate(out, args.max_output_chars))

    if err:
        sys.stderr.write(_truncate(err, args.max_output_chars))

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rlm_repl",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            Persistent mini-REPL for RLM-style workflows in OpenCode.
            Designed for SRE/DevOps: analyzing logs, configs, manifests.

            Examples:
              python rlm_repl.py init application.log
              python rlm_repl.py status
              python rlm_repl.py exec -c "print(stats())"
              python rlm_repl.py exec -c "print(grep('ERROR', max_matches=10))"
              python rlm_repl.py exec <<'PY'
              print(peek(0, 2000))
              PY
            """
        ),
    )
    p.add_argument(
        "--state",
        default=str(DEFAULT_STATE_PATH),
        help=f"Path to state pickle (default: {DEFAULT_STATE_PATH})",
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize state from a context file")
    p_init.add_argument("context", help="Path to the context file (logs, configs, etc.)")
    p_init.add_argument(
        "--max-bytes",
        type=int,
        default=None,
        help="Optional cap on bytes read from the context file",
    )
    p_init.set_defaults(func=cmd_init)

    p_status = sub.add_parser("status", help="Show current state summary")
    p_status.add_argument(
        "--show-vars", action="store_true", help="List persisted variable names"
    )
    p_status.set_defaults(func=cmd_status)

    p_reset = sub.add_parser("reset", help="Delete the current state file and chunks")
    p_reset.set_defaults(func=cmd_reset)

    p_export = sub.add_parser(
        "export-buffers", help="Export buffers list to a text file"
    )
    p_export.add_argument("out", help="Output file path")
    p_export.set_defaults(func=cmd_export_buffers)

    p_exec = sub.add_parser("exec", help="Execute Python code with persisted state")
    p_exec.add_argument(
        "-c",
        "--code",
        default=None,
        help="Inline code string. If omitted, reads code from stdin.",
    )
    p_exec.add_argument(
        "--max-output-chars",
        type=int,
        default=DEFAULT_MAX_OUTPUT_CHARS,
        help=f"Truncate stdout/stderr to this many characters (default: {DEFAULT_MAX_OUTPUT_CHARS})",
    )
    p_exec.add_argument(
        "--warn-unpickleable",
        action="store_true",
        help="Warn on stderr when variables could not be persisted",
    )
    p_exec.set_defaults(func=cmd_exec)

    return p


def main(argv: List[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return int(args.func(args))
    except RlmReplError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
