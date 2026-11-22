#!/usr/bin/env python3
"""示範專案 → plugin 一鍵同步：示範專案（引擎開發來源）調整後，把變更帶回 plugin。

用法：
  python3 tools/sync_kit.py <示範專案資料夾> --dry-run   # 只列出會同步的項目
  python3 tools/sync_kit.py <示範專案資料夾>             # 同步
  python3 tools/sync_kit.py <示範專案資料夾> --bump      # 引擎沒變、只改了規則文件或範本時也升版
  python3 tools/sync_kit.py <示範專案資料夾> --minor     # 新功能：升次版號（例如 0.6.1 → 0.7.0），可與 --bump 併用

會做的事：
  1. 示範專案先跑 check.py，有錯誤就停止（不把壞掉的版本帶進 plugin）
  2. 比對引擎（scripts/*.py、規範/、index.html 內容區以外）；有差異就匯出到 plugin 的 engine/ 與 規範/（同 build_engine.py）
  3. 引擎有變更時 plugin 版本加一（修訂號，例如 0.5.0 → 0.5.1），示範專案 project.json › engine_version 同步
  4. 自我測試：在暫存資料夾用範本建一個空白專案並跑 check.py，確認範本與新引擎相容
  5. 重產 FILES.txt（安裝腳本與 update_kit.py 下載清單）
  6. 提醒：在 README「更新紀錄」寫一行；規則類變更另見 spec-change SKILL.md「示範專案與 plugin 同步」
共用規範在示範專案的 規範/ 修改後由本工具帶回；範本（template/）直接在 plugin 修改，再加 --bump。
"""
from __future__ import annotations

import filecmp
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import build_engine
import update_kit
from _kit import ENGINE, KIT, run_py, set_engine_version, version


def bump(ver: str) -> str:
    major, minor, patch = (int(x) for x in ver.split("."))
    if "--minor" in sys.argv:
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def engine_diff(project: Path) -> list[str]:
    template = build_engine.make_template((project / "index.html").read_text(encoding="utf-8"))
    diffs = [p.name for p in build_engine.engine_scripts(project)
             if not (ENGINE / "scripts" / p.name).exists() or not filecmp.cmp(p, ENGINE / "scripts" / p.name, shallow=False)]
    gone = sorted({p.name for p in (ENGINE / "scripts").glob("*.py")} - {p.name for p in build_engine.engine_scripts(project)})
    diffs += [f"{n}（專案已刪除）" for n in gone]
    tpl = ENGINE / "index.template.html"
    if not tpl.exists() or tpl.read_text(encoding="utf-8") != template:
        diffs.append("index.template.html")
    return diffs + build_engine.rules_diff(project)


def selftest() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "selftest"
        r = run_py([str(KIT / "tools" / "init_project.py"), str(target), "--name", "自我測試"])
        lines = (r.stdout + r.stderr).strip().splitlines()
        last = [x for x in lines if "check.py" in x][-1:] or lines[-1:] or ["（無輸出）"]
        print(f"  自我測試（空白專案）：{last[0].strip()}")
        return r.returncode == 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    project = Path(args[0]).resolve()
    dry = "--dry-run" in sys.argv
    r = run_py(["scripts/check.py", "--errors"], cwd=project)
    if r.returncode != 0:
        print("停止｜示範專案 check.py 有錯誤，先修正再同步：")
        print(r.stdout.strip())
        return 1
    diffs = engine_diff(project)
    old = version()
    print(f"引擎：{'、'.join(diffs) if diffs else '與 plugin 一致'}")
    if dry:
        if diffs:
            print(f"  將匯出並升版 {old} → {bump(old)}")
        return 0
    if diffs or "--bump" in sys.argv or "--minor" in sys.argv:
        if diffs:
            build_engine.main_export(project)
        new = bump(old)
        (KIT / "VERSION").write_text(new + "\n", encoding="utf-8")
        pj = KIT / ".claude-plugin" / "plugin.json"
        pj.write_text(re.sub(r'"version":\s*"[^"]+"', f'"version": "{new}"', pj.read_text(encoding="utf-8"), count=1), encoding="utf-8")
        set_engine_version(project, new)
        run_py(["scripts/ai_entry.py"], cwd=project)   # 入口檔標有版本號，升版後重產
        print(f"  {'已匯出並升版' if diffs else '已升版'}：{old} → {new}；示範專案 engine_version 已同步")
    update_kit.write_manifest(KIT)   # FILES.txt：安裝腳本與 update_kit.py 依它下載
    ok = selftest()
    if diffs or "--bump" in sys.argv or "--minor" in sys.argv:
        print(f"提醒｜在 {KIT.name}/README.md「更新紀錄」最上方寫一行 {version()}：改了什麼、為什麼；"
              "其他專案以 upgrade_project.py 升級。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
