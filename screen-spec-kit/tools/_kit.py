"""tools/ 共用：plugin 路徑、版本、執行專案工具。"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
ENGINE = KIT / "engine"
TEMPLATE = KIT / "template"
RULES = KIT / "規範"   # 共用設計規範（不綁定 AI；從示範專案匯出）
REGENERATE = ["ai_entry.py", "index_build.py", "flow_sync.py", "dev_notes.py", "svg_bundle.py", "inventory.py"]


def version() -> str:
    """工具組版本：VERSION（看得見的檔案）；沒有時讀 .claude-plugin/plugin.json。
    手動上傳到 GitHub 時以「.」開頭的資料夾常被略過，所以工具只依賴 VERSION。"""
    v = KIT / "VERSION"
    if v.exists():
        return v.read_text(encoding="utf-8").strip()
    return json.loads((KIT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


# Windows 的主控台與管線預設不是 UTF-8；子程序與本程序一律用 UTF-8
PY_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def run_py(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """以目前的 Python 執行，輸出以 UTF-8 解讀（Windows 也一樣）。"""
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=PY_ENV)


def run_tools(project: Path, tools: list[str]) -> bool:
    ok = True
    for tool in tools:
        r = run_py([f"scripts/{tool}"], cwd=project)
        out = (r.stdout + r.stderr).strip().splitlines()
        print(f"  {tool}：{out[-1] if out else '（無輸出）'}")
        ok &= r.returncode == 0
    return ok


def set_engine_version(project: Path, ver: str) -> None:
    p = project / "project.json"
    s = p.read_text(encoding="utf-8")
    if re.search(r'"engine_version":\s*"[^"]*"', s):
        s = re.sub(r'"engine_version":\s*"[^"]*"', f'"engine_version": "{ver}"', s, count=1)
    else:
        s = re.sub(r'(\n(\s*)"name":\s*"[^"]*",)', rf'\1\n\2"engine_version": "{ver}",', s, count=1)
    json.loads(s)
    p.write_text(s, encoding="utf-8")
