#!/usr/bin/env python3
"""把專案的引擎升級到目前 plugin 版本（scripts/ 與 index.html 引擎部分）。

用法：
  python3 tools/upgrade_project.py <專案資料夾> --dry-run   # 只列出會變的檔案
  python3 tools/upgrade_project.py <專案資料夾>             # 備份後升級

會做的事：
  1. 備份 scripts/、index.html、project.json 到 <專案>/.engine_backup/<舊版>-to-<新版>-<時間>/
  2. 以 engine/scripts/ 覆蓋同名工具（專案自己多出的工具保留並列出）
  3. 規範/ 整份換成 plugin 的共用規範；舊版專案沒有 專案規則.md 時，把原本的 AGENTS.md 改名為 專案規則.md（之後由 ai_entry.py 產生入口檔）
  3b. index.html 換成新版範本，保留內容區（<!-- [slot:…] -->）與產生區（網站地圖、專案設定、流程資料）
  4. project.json › engine_version 改成新版
  5. 重跑 index_build、flow_sync、dev_notes、svg_bundle、inventory，最後 check.py
專案的 Markdown、SVG、流程、架構圖都不會動。
"""
from __future__ import annotations

import datetime
import filecmp
import json
import shutil
import sys
from pathlib import Path

import slots
from _kit import ENGINE, REGENERATE, RULES, run_tools, set_engine_version, version


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    project = Path(args[0]).resolve()
    dry = "--dry-run" in sys.argv
    if not (project / "project.json").exists() or not (project / "index.html").exists():
        print(f"錯誤｜{project} 不是畫面規格專案（缺 project.json 或 index.html）")
        return 1
    old = json.loads((project / "project.json").read_text(encoding="utf-8")).get("engine_version", "未標示")
    new = version()
    engine_files = sorted((ENGINE / "scripts").glob("*.py"))
    changed = [p.name for p in engine_files
               if not (project / "scripts" / p.name).exists() or not filecmp.cmp(p, project / "scripts" / p.name, shallow=False)]
    extras = sorted({p.name for p in (project / "scripts").glob("*.py")} - {p.name for p in engine_files})
    index_old = (project / "index.html").read_text(encoding="utf-8")
    index_new, notes = slots.merge((ENGINE / "index.template.html").read_text(encoding="utf-8"), index_old)
    print(f"引擎版本：{old} → {new}")
    print(f"  工具：{'、'.join(changed) if changed else '無變更'}")
    mine = {q.name: q for q in (project / "規範").glob("*.md")} if (project / "規範").exists() else {}
    added = sorted(q.name for q in RULES.glob("*.md") if q.name not in mine)
    updated = sorted(q.name for q in RULES.glob("*.md") if q.name in mine and not filecmp.cmp(q, mine[q.name], shallow=False))
    removed = sorted(set(mine) - {q.name for q in RULES.glob("*.md")})
    parts = [f"新增 {len(added)} 份" if added else "", f"更新 {'、'.join(updated)}" if updated else "", f"移除 {'、'.join(removed)}" if removed else ""]
    print(f"  規範：{'；'.join(x for x in parts if x) or '無變更'}")
    print(f"  index.html：{'引擎部分有變更' if index_new != index_old else '無變更'}")
    for n in notes:
        print("  提醒｜" + n)
    if extras:
        print(f"  保留專案自有工具：{'、'.join(extras)}")
    if dry:
        return 0
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = project / ".engine_backup" / f"{old}-to-{new}-{stamp}"
    backup.mkdir(parents=True)
    shutil.copytree(project / "scripts", backup / "scripts")
    shutil.copy2(project / "index.html", backup / "index.html")
    shutil.copy2(project / "project.json", backup / "project.json")
    for name in ("規範", ".github"):
        if (project / name).exists():
            shutil.copytree(project / name, backup / name)
    for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "專案規則.md"):
        if (project / name).exists():
            shutil.copy2(project / name, backup / name)
    print(f"  已備份到 {backup}")
    for p in engine_files:
        shutil.copy2(p, project / "scripts" / p.name)
    (project / "index.html").write_text(index_new, encoding="utf-8")
    if (project / "規範").exists():
        shutil.rmtree(project / "規範")
    shutil.copytree(RULES, project / "規範")
    agents = project / "AGENTS.md"
    if not (project / "專案規則.md").exists() and agents.exists() and "由 scripts/ai_entry.py 產生" not in agents.read_text(encoding="utf-8"):
        agents.rename(project / "專案規則.md")
        print("  已把原本的 AGENTS.md 改名為 專案規則.md；請刪掉其中「載入 skill」等通用規則段落（已在 規範/）")
    set_engine_version(project, new)
    ok = run_tools(project, REGENERATE + ["check.py"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
