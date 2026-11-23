#!/usr/bin/env python3
"""維護者用：改工具組在 GitHub 上的位置（帳號、repo、分支、資料夾），一次改完所有寫死的網址與安裝路徑。

用法：
  python3 tools/set_location.py                                  # 顯示目前位置（tools/location.json）
  python3 tools/set_location.py --folder spec-studio --dry-run    # 預覽會改哪些地方
  python3 tools/set_location.py --folder spec-studio --also "../捐款平台_全頁面示意圖"
  可改的項目：--owner、--repo、--branch、--folder（GitHub 上的資料夾，也是同事電腦上的安裝資料夾名稱）

會改：update_kit.py 的下載來源、安裝腳本、doctor.py、SETUP.md、README.md（更新紀錄不改）、使用手冊.html，
以及 --also 指定的示範專案的 規範/ 與 scripts/（規範來源在示範專案，改完執行 sync_kit.py 帶回工具組）。
工具名稱 screen-spec-kit 不改；入門頁 index.html 用相對路徑，不受影響。
改完後：已安裝的同事要重新執行新網址的安裝指令；舊的 ~/NewebDoc/<舊資料夾> 可刪除。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
STATE = KIT / "tools" / "location.json"
TEXT = {".md", ".py", ".sh", ".ps1", ".html", ".json"}
SKIP = {"FILES.txt", "location.json"}

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def pairs(old: dict, new: dict) -> list[tuple[str, str]]:
    """目前位置 → 新位置的字串對照（只換路徑或網址形式，不換工具名稱本身）。"""
    def forms(x):
        o, r, b, f, root = x["owner"], x["repo"], x["branch"], x["folder"], x["install_root"]
        return [
            f"https://raw.githubusercontent.com/{o}/{r}/{b}/{f}",
            f"https://{o}.github.io/{r}/{f}",
            f"https://github.com/{o}/{r}.git",
            f"`{o}/{r}` 的 `{f}/`",
            f"`{o}/{r}`",
            f"sparse-checkout set {f}",
            f"sparse-checkout add {f}",
            f"{root}/{f}",
            f"{root}\\{f}",
            f"Join-Path $Root '{f}'",
            f'KIT="$ROOT/{f}"',
        ]
    return [(a, b) for a, b in zip(forms(old), forms(new)) if a != b]


def files(also: list[Path]) -> list[Path]:
    out = [p for p in KIT.rglob("*") if p.is_file() and p.suffix in TEXT and p.name not in SKIP
           and not any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(KIT).parts)]
    for proj in also:
        out += [p for p in (proj / "規範").glob("*.md")] + [p for p in (proj / "scripts").glob("*.py")]
    return sorted(set(out))


def rewrite(path: Path, table: list[tuple[str, str]], dry: bool) -> int:
    text = path.read_text(encoding="utf-8")
    lines, n = [], 0
    for line in text.split("\n"):
        if path.name == "README.md" and line.startswith("- 0."):   # 更新紀錄保留原文
            lines.append(line)
            continue
        for a, b in table:
            if a in line:
                n += line.count(a)
                line = line.replace(a, b)
        lines.append(line)
    if n and not dry:
        path.write_text("\n".join(lines), encoding="utf-8")
    return n


def main() -> int:
    args = sys.argv[1:]
    cur = json.loads(STATE.read_text(encoding="utf-8"))
    new = dict(cur)
    for key in ("owner", "repo", "branch", "folder"):
        if f"--{key}" in args:
            new[key] = args[args.index(f"--{key}") + 1]
    also = [Path(args[args.index("--also") + 1]).resolve()] if "--also" in args else []
    if new == cur:
        print("目前位置：" + "、".join(f"{k}={v}" for k, v in cur.items() if not k.startswith("_")))
        print(f"入門頁：https://{cur['owner']}.github.io/{cur['repo']}/{cur['folder']}/")
        return 0
    table = pairs(cur, new)
    dry = "--dry-run" in args
    total = 0
    for p in files(also):
        n = rewrite(p, table, dry)
        if n:
            total += n
            print(f"  {'會改' if dry else '已改'} {n:>3} 處｜{p.relative_to(p.parents[1]) if also and str(p).startswith(str(also[0])) else p.relative_to(KIT)}")
    if not dry:
        STATE.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{'預覽' if dry else '完成'}｜共 {total} 處；新入門頁：https://{new['owner']}.github.io/{new['repo']}/{new['folder']}/")
    if not dry:
        print("下一步｜有 --also 時執行 sync_kit.py 把規範帶回工具組；已安裝的同事要重新執行新網址的安裝指令")
    return 0


if __name__ == "__main__":
    sys.exit(main())
