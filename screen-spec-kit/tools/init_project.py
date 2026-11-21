#!/usr/bin/env python3
"""建立空白的畫面規格專案（範本＋引擎）。

用法：
  python3 tools/init_project.py <新資料夾> --name "<專案名稱>" [--subtitle "<頁首副標>"] [--footer "<頁尾說明>"]

會做的事：
  1. 複製 template/（規格、網站地圖、專案規則.md、project.json、架構圖骨架、screens/ flows/ assets/）與共用規範 規範/
  2. 複製 engine/scripts/ 到 scripts/，engine/index.template.html 成為 index.html
  3. 代入 {{name}} {{subtitle}} {{footer}} {{date}} {{engine_version}}
  4. 有本機 plantuml 時渲染架構圖（不送線上伺服器）
  5. 執行 ai_entry（產生 AGENTS.md、CLAUDE.md 等入口檔）、index_build、flow_sync、dev_notes、svg_bundle、inventory，最後 check.py
之後依 spec-new 訪談（questioning.md 第 3 節）逐步填入內容。
"""
from __future__ import annotations

import argparse
import os
import datetime
import shutil
import subprocess
import sys
from pathlib import Path

from _kit import ENGINE, KIT, RULES, TEMPLATE, run_tools, version

TEXT_SUFFIXES = {".md", ".json", ".puml", ".html"}


def kit_path(target: Path) -> str:
    """plugin 位置：工具組就在專案旁邊（同一個上層資料夾）時用相對路徑；放在家目錄（例如 ~/NewebDoc/screen-spec-kit）
    時用 ~ 開頭，專案搬家或換到同事電腦也找得到；其他情況用絕對路徑。一律用 / 分隔。"""
    try:
        rel = os.path.relpath(KIT, target)
    except ValueError:   # Windows 不同磁碟
        rel = ""
    if rel and rel.count("..") <= 1:
        return Path(rel).as_posix()
    try:
        return "~/" + KIT.relative_to(Path.home()).as_posix()
    except ValueError:
        return KIT.as_posix()


def main() -> int:
    ap = argparse.ArgumentParser(description="建立空白的畫面規格專案")
    ap.add_argument("target")
    ap.add_argument("--name", required=True)
    ap.add_argument("--subtitle", default="〔待訪談第 1 階段：一句話說明〕｜資訊架構與全頁面介面示意")
    ap.add_argument("--footer", default="依訪談內容整理；標示待確認者尚未定案。示意圖不是正式規格。")
    a = ap.parse_args()
    target = Path(a.target).resolve()
    if target.exists() and any(target.iterdir()):
        print(f"錯誤｜{target} 已存在且不是空資料夾，不覆蓋")
        return 1
    ver = version()
    values = {"{{name}}": a.name, "{{subtitle}}": a.subtitle, "{{footer}}": a.footer,
              "{{date}}": datetime.date.today().isoformat(), "{{engine_version}}": ver,
              "{{kit_path}}": kit_path(target)}
    shutil.copytree(TEMPLATE, target, dirs_exist_ok=True)
    shutil.copytree(ENGINE / "scripts", target / "scripts")
    shutil.copytree(RULES, target / "規範")
    shutil.copy2(ENGINE / "index.template.html", target / "index.html")
    for p in target.rglob("*"):
        if p.is_file() and p.suffix in TEXT_SUFFIXES:
            s = p.read_text(encoding="utf-8")
            for k, v in values.items():
                s = s.replace(k, v)
            p.write_text(s, encoding="utf-8")
    print(f"已建立｜{target}（screen-spec-kit {ver}）")
    plantuml = shutil.which("plantuml")   # 取完整路徑：Windows 的 plantuml.cmd 才執行得到
    if plantuml:
        r = subprocess.run([plantuml, "-tsvg", *[str(p) for p in sorted((target / "architecture").glob("*.puml"))]],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("  plantuml：" + ("架構圖已渲染" if r.returncode == 0 else "渲染失敗 " + r.stderr.strip()[:200]))
    else:
        print("  提醒：找不到本機 plantuml，架構圖 SVG 未產生；安裝後執行 plantuml -tsvg architecture/*.puml")
    ok = run_tools(target, ["ai_entry.py", "index_build.py", "flow_sync.py", "dev_notes.py", "svg_bundle.py", "inventory.py", "check.py"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
