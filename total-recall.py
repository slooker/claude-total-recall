#!/usr/bin/env python3
"""
total-recall: Zero-dependency context recall for Claude Code.
Reads ~/.claude/projects/<cwd>/*.jsonl and returns a compact
JSON summary so Claude Code re-orients in ~50 tokens instead
of burning 10k+ on blind grep/find searches.

Usage:
  total-recall             # auto-detect project from cwd
  total-recall --days 7    # look back N days (default: 3)
  total-recall --limit 5   # max sessions to scan (default: 3)
  total-recall --json      # output raw JSON (default)
  total-recall --text      # human-readable text output
  total-recall health      # check setup and data freshness
"""

import json
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── helpers ──────────────────────────────────────────────────────────────────

def encode_path(path: str) -> str:
    """Mirrors Claude Code's path encoding: replace non-alphanumeric with '-'"""
    return "".join(c if c.isalnum() else "-" for c in path)

def find_project_dir(cwd: str) -> Path | None:
    """Find the ~/.claude/projects/<encoded-cwd> directory."""
    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        return None
    encoded = encode_path(cwd)
    candidate = base / encoded
    if candidate.exists():
        return candidate
    # Walk up the directory tree in case cwd is a subdirectory
    parts = Path(cwd).parts
    for i in range(len(parts), 0, -1):
        partial = str(Path(*parts[:i]))
        candidate = base / encode_path(partial)
        if candidate.exists():
            return candidate
    return None

def parse_jsonl(filepath: Path) -> list[dict]:
    """Parse a JSONL file, skipping malformed lines."""
    records = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except (IOError, OSError):
        pass
    return records

def extract_session_data(records: list[dict]) -> dict:
    """Extract the useful bits from a session's JSONL records."""
    user_prompts = []
    files_read = set()
    files_modified = set()
    summary = None
    timestamps = []
    session_id = None

    for r in records:
        rtype = r.get("type", "")
        ts = r.get("timestamp")
        if ts:
            timestamps.append(ts)

        if not session_id:
            session_id = r.get("sessionId")

        # Capture summary records (Claude Code writes these on compaction)
        if rtype == "summary":
            summary = r.get("summary", "")
            continue

        # User messages → prompts
        if rtype == "user":
            msg = r.get("message", {})
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                user_prompts.append(content.strip()[:200])
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text:
                            user_prompts.append(text[:200])

        # Tool use → file tracking
        if rtype in ("tool_use", "assistant"):
            msg = r.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    tool = block.get("name", "")
                    inp = block.get("input", {})
                    fp = inp.get("file_path") or inp.get("path", "")
                    if fp:
                        if tool in ("Read", "Glob", "Grep"):
                            files_read.add(fp)
                        elif tool in ("Write", "Edit", "MultiEdit"):
                            files_modified.add(fp)

    started = min(timestamps) if timestamps else None
    ended = max(timestamps) if timestamps else None

    return {
        "session_id": session_id,
        "started": started,
        "ended": ended,
        "user_prompts": user_prompts[:5],  # first 5 prompts only
        "files_read": sorted(files_read)[:20],
        "files_modified": sorted(files_modified)[:20],
        "summary": summary,
    }

def gather_sessions(project_dir: Path, days: int, limit: int) -> list[dict]:
    """Find, sort, and parse recent session files."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    jsonl_files = sorted(
        project_dir.glob("*.jsonl"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    results = []
    for f in jsonl_files:
        if len(results) >= limit:
            break
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            break
        records = parse_jsonl(f)
        if not records:
            continue
        data = extract_session_data(records)
        data["file"] = f.name
        data["age_hours"] = round((datetime.now(timezone.utc) - mtime).total_seconds() / 3600, 1)
        results.append(data)

    return results

# ── output formatters ─────────────────────────────────────────────────────────

def format_json(sessions: list[dict], cwd: str) -> str:
    out = {
        "project": cwd,
        "generated": datetime.now(timezone.utc).isoformat(),
        "sessions": sessions,
    }
    return json.dumps(out, indent=2)

def rel(path: str, cwd: str) -> str:
    """Return path relative to cwd, falling back to basename."""
    try:
        return str(Path(path).relative_to(cwd)).replace("\\", "/")
    except ValueError:
        return Path(path).name

def format_text(sessions: list[dict], cwd: str) -> str:
    if not sessions:
        return f"=== Total Recall: {Path(cwd).name} ===\nNo recent sessions found."

    lines = [f"=== Total Recall: {Path(cwd).name} ==="]
    for i, s in enumerate(sessions, 1):
        age = s.get("age_hours", "?")
        lines.append(f"── Session {i} ({age}h ago) ──")
        raw = s.get("summary") or (s["user_prompts"][0] if s.get("user_prompts") else "")
        hint = " ".join(raw.split())
        if len(hint) > 80:
            hint = hint[:80].rsplit(" ", 1)[0]
        if hint:
            lines.append(f"Task: {hint}")
        if s.get("files_modified"):
            short = [rel(f, cwd) for f in s["files_modified"][:8]]
            lines.append(f"Modified: {', '.join(short)}")
        if s.get("files_read"):
            short = [rel(f, cwd) for f in s["files_read"][:8]]
            lines.append(f"Read: {', '.join(short)}")

    return "\n".join(lines)

# ── health check ──────────────────────────────────────────────────────────────

def cmd_health(cwd: str) -> int:
    print("total-recall health check")
    print("-" * 50)

    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        print("❌ ~/.claude/projects not found — has Claude Code been run yet?")
        return 1
    print(f"✅ ~/.claude/projects exists")

    project_dir = find_project_dir(cwd)
    if not project_dir:
        print(f"⚠️  No session directory for: {cwd}")
        print(f"   Expected: {base / encode_path(cwd)}")
        return 1
    print(f"✅ Project dir: {project_dir}")

    files = list(project_dir.glob("*.jsonl"))
    print(f"✅ Session files: {len(files)}")

    if files:
        newest = max(files, key=lambda f: f.stat().st_mtime)
        age_h = (datetime.now().timestamp() - newest.stat().st_mtime) / 3600
        print(f"✅ Newest session: {age_h:.1f}h ago ({newest.name})")
        records = parse_jsonl(newest)
        print(f"✅ Records in newest session: {len(records)}")
    else:
        print("⚠️  No .jsonl files found yet")

    print("\nAll good — total-recall is ready.")
    return 0

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Compact context recall for Claude Code sessions"
    )
    parser.add_argument("command", nargs="?", help="'health' for diagnostics")
    parser.add_argument("--days", type=int, default=3, help="Look back N days (default: 3)")
    parser.add_argument("--limit", type=int, default=3, help="Max sessions (default: 3)")
    parser.add_argument("--text", action="store_true", help="Human-readable output")
    parser.add_argument("--cwd", type=str, default=None, help="Override working directory")
    args = parser.parse_args()

    cwd = args.cwd or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    if args.command == "health":
        sys.exit(cmd_health(cwd))

    project_dir = find_project_dir(cwd)
    if not project_dir:
        # Graceful no-op — don't burn tokens on error text
        if args.text:
            print(f"No session history found for {cwd}")
        else:
            print(json.dumps({"project": cwd, "sessions": [], "note": "No history found"}))
        return

    sessions = gather_sessions(project_dir, days=args.days, limit=args.limit)

    if args.text:
        print(format_text(sessions, cwd))
    else:
        print(format_json(sessions, cwd))

if __name__ == "__main__":
    main()
