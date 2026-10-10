#!/usr/bin/env python3
"""收工交接：收集 git 事实，读写交接文件。叙述仍由代理来写。"""

import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path

HANDOFF_DIR = Path.home() / ".cursor" / "handoffs"
SECTIONS = ("做到哪", "卡在哪", "明天第一件", "别动")
ITEM_LINE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+\S")


def project_key(cwd: Path) -> str:
    return "-".join(part for part in cwd.resolve().parts if part not in ("/", ""))


def handoff_path(cwd: Path) -> Path:
    return HANDOFF_DIR / f"{project_key(cwd)}.md"


def previous_path(path: Path) -> Path:
    return path.with_name(path.name + ".prev")


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError:
        return 127, ""
    text = result.stdout if result.stdout.strip() else result.stderr
    return result.returncode, text.strip()


def run_raw(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError:
        return 127, ""
    return result.returncode, result.stdout


def is_git(cwd: Path) -> bool:
    code, text = run(["git", "rev-parse", "--is-inside-work-tree"], cwd)
    return code == 0 and text == "true"


def field(text: str, name: str) -> str:
    prefix = f"{name}："
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return ""


def section_body(text: str, name: str) -> str:
    parts = parse_sections(text)
    return parts.get(name, "").strip()


def parse_sections(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    current = ""
    chunks: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                found[current] = "\n".join(chunks).strip()
            current = line.removeprefix("## ").strip()
            chunks = []
            continue
        if current:
            chunks.append(line)
    if current:
        found[current] = "\n".join(chunks).strip()
    return found


def existing_date(path: Path) -> str:
    if not path.is_file():
        return "无"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "有"
    return field(text, "日期") or "有"


def uncommitted(cwd: Path) -> list[str]:
    code, text = run_raw(["git", "status", "--porcelain"], cwd)
    if code != 0 or not text:
        return []
    lines = []
    for line in text.splitlines():
        if len(line) < 4:
            continue
        status, name = line[:2], line[3:]
        if status == "??":
            kind = "未跟踪"
        elif status[0] not in (" ", "?") and status[1] not in (" ", "?"):
            kind = "已暂存且未暂存"
        elif status[0] not in (" ", "?"):
            kind = "已暂存"
        else:
            kind = "未暂存"
        lines.append(f"- {name}（{kind}）")
    return lines


def collect(cwd: Path) -> int:
    path = handoff_path(cwd)
    print(f"日期：{datetime.date.today().isoformat()}")
    print(f"项目：{cwd.resolve()}")
    print(f"交接文件：{path}")
    print(f"已有交接：{existing_date(path)}")
    if not is_git(cwd):
        print("git：不是 git 仓库")
        print("未提交文件：无")
        return 0
    print("git：是 git 仓库")
    pending = uncommitted(cwd)
    print("未提交文件：" + ("无" if not pending else ""))
    for line in pending:
        print(line)
    commands = [
        ("status", ["git", "status", "-sb"]),
        ("diff_stat", ["git", "diff", "--stat"]),
        ("cached_stat", ["git", "diff", "--cached", "--stat"]),
        ("log", ["git", "log", "-8", "--oneline"]),
    ]
    for label, cmd in commands:
        _, text = run(cmd, cwd)
        print(f"\n## {label}")
        print(text or "（空）")
    return 0


def show(cwd: Path) -> int:
    path = handoff_path(cwd)
    if not path.is_file():
        print("没有上次交接")
        return 1
    sys.stdout.write(path.read_text(encoding="utf-8"))
    return 0


def prev(cwd: Path) -> int:
    path = previous_path(handoff_path(cwd))
    if not path.is_file():
        print("没有上一份交接")
        return 1
    sys.stdout.write(path.read_text(encoding="utf-8"))
    return 0


def first_next_action(text: str) -> str:
    for line in section_body(text, "明天第一件").splitlines():
        line = line.strip()
        if line:
            return re.sub(r"^(?:[-*]|\d+[.)])\s+", "", line)
    return "（空）"


def list_handoffs(cwd: Path) -> int:
    del cwd
    files = sorted(HANDOFF_DIR.glob("*.md")) if HANDOFF_DIR.is_dir() else []
    if not files:
        print("没有交接")
        return 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            print(f"{path}\n日期：\n项目：\n明天第一件：（读不了）\n")
            continue
        print(path)
        print(f"日期：{field(text, '日期') or '无'}")
        print(f"项目：{field(text, '项目') or '无'}")
        print(f"明天第一件：{first_next_action(text)}")
        print()
    return 0


def validate(body: str, cwd: Path) -> str:
    stripped = body.strip()
    if not stripped.startswith("# 交接"):
        return "开头必须是「# 交接」"
    date = field(stripped, "日期")
    if date != datetime.date.today().isoformat():
        return "日期必须是今天，用 collect 打印的那一行"
    project = field(stripped, "项目")
    if not project:
        return "缺少「项目：」"
    try:
        same = Path(project).expanduser().resolve() == cwd.resolve()
    except OSError:
        same = False
    if not same:
        return "项目路径必须和 collect 打印的一致"
    parts = parse_sections(stripped)
    names = [line.removeprefix("## ").strip() for line in stripped.splitlines() if line.startswith("## ")]
    if names != list(SECTIONS):
        return "四个小节必须按顺序写：做到哪、卡在哪、明天第一件、别动"
    for name in SECTIONS:
        if not parts.get(name, "").strip():
            return f"「{name}」不能空，没有就写「无」"
    items = [line for line in parts["明天第一件"].splitlines() if ITEM_LINE.match(line)]
    if len(items) > 1:
        return "明天第一件只能有一件"
    return ""


def save(cwd: Path) -> int:
    body = sys.stdin.read()
    if not body.strip():
        print("没有内容可写", file=sys.stderr)
        return 1
    if not body.endswith("\n"):
        body += "\n"
    problem = validate(body, cwd)
    if problem:
        print(problem, file=sys.stderr)
        return 1
    path = handoff_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        shutil.copy2(path, previous_path(path))
    path.write_text(body, encoding="utf-8")
    print(path)
    return 0


def main() -> int:
    commands = {
        "collect": collect,
        "show": show,
        "prev": prev,
        "list": list_handoffs,
        "save": save,
    }
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        names = " | ".join(commands)
        print(f"用法: handoff.py {names}", file=sys.stderr)
        return 2
    return commands[sys.argv[1]](Path.cwd())


if __name__ == "__main__":
    sys.exit(main())
