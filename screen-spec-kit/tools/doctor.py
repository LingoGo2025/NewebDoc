#!/usr/bin/env python3
"""環境檢查：列出 screen-spec-kit 需要的軟體是否就緒，缺少時附上這台電腦（macOS／Windows／Linux）的安裝指令。

用法：
  python3 tools/doctor.py                     # 檢查（Windows 用 python 或 py -3 代替 python3）
  python3 tools/doctor.py --install-plantuml  # 沒有套件管理工具可裝 PlantUML 時（Windows 常用）：
                                              # 下載官方 plantuml.jar 到 <工具組>/.bin/ 並建立 plantuml 指令

結束碼：必要軟體都就緒為 0，否則為 1。安裝後若仍顯示缺少，多半是終端機還沒讀到新的 PATH：重開 AI 工具再檢查。
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

from _kit import KIT, version

SYSTEM = {"Darwin": "mac", "Windows": "win"}.get(platform.system(), "linux")
BIN = KIT / ".bin"
PY = "python3" if SYSTEM != "win" else "python"

# 各系統的安裝指令（Windows 用 winget；macOS 用 Homebrew）
HINTS = {
    "git": {"mac": "xcode-select --install（或 brew install git）",
            "win": "winget install --id Git.Git -e",
            "linux": "sudo apt install git"},
    "python": {"mac": "brew install python",
               "win": "winget install --id Python.Python.3.12 -e",
               "linux": "sudo apt install python3"},
    "java": {"mac": "brew install openjdk（brew install plantuml 會一併安裝）",
             "win": "winget install --id EclipseAdoptium.Temurin.21.JRE -e",
             "linux": "sudo apt install default-jre"},
    "graphviz": {"mac": "brew install graphviz（brew install plantuml 會一併安裝）",
                 "win": "winget install --id Graphviz.Graphviz -e",
                 "linux": "sudo apt install graphviz"},
    "plantuml": {"mac": "brew install plantuml",
                 "win": f"{PY} tools/doctor.py --install-plantuml",
                 "linux": "sudo apt install plantuml（或 python3 tools/doctor.py --install-plantuml）"},
    "rsvg": {"mac": "brew install librsvg",
             "win": "（選用，可略過）",
             "linux": "sudo apt install librsvg2-bin"},
}

# Windows 用 winget 安裝後，舊的終端機還沒有新的 PATH；先到常見位置找
WIN_GUESS = {
    "dot": ["C:/Program Files/Graphviz/bin/dot.exe"],
    "java": ["C:/Program Files/Eclipse Adoptium/*/bin/java.exe", "C:/Program Files/Java/*/bin/java.exe"],
    "git": ["C:/Program Files/Git/cmd/git.exe"],
}

results: list[tuple[str, bool, bool, str]] = []   # (名稱, 必要, 就緒, 說明)


def run(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    """回傳（結束碼, 輸出）；無法執行時結束碼為 -1。"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""
    return r.returncode, (r.stdout + r.stderr).strip()


def find(name: str) -> str:
    """回傳執行檔完整路徑（Windows 的 .cmd 也要完整路徑才執行得到）；找不到回傳空字串。"""
    hit = shutil.which(name)
    if hit:
        return hit
    if SYSTEM == "win":
        for pattern in WIN_GUESS.get(name, []):
            found = sorted(Path("C:/").glob(pattern[3:]))
            if found:
                return str(found[-1])
    local = BIN / ("plantuml.cmd" if SYSTEM == "win" else "plantuml")
    if name == "plantuml" and local.exists():
        return str(local)
    return ""


def add(name: str, required: bool, ok: bool, detail: str) -> None:
    results.append((name, required, ok, detail))


def hint(key: str) -> str:
    return HINTS[key][SYSTEM]


def check_python() -> None:
    v = sys.version_info
    ok = v >= (3, 9)
    add("Python 3.9 以上", True, ok, f"{v.major}.{v.minor}.{v.micro}" + ("" if ok else f" → {hint('python')}"))
    if SYSTEM == "win":
        utf8 = os.environ.get("PYTHONUTF8") == "1"
        add("PYTHONUTF8=1（Windows 中文編碼）", True, utf8,
            "已設定" if utf8 else "未設定 → setx PYTHONUTF8 1（設定後重開 AI 工具）")


def check_simple(label: str, exe: str, args: list[str], key: str, required: bool = True) -> str:
    path = find(exe)
    if not path:
        add(label, required, False, f"找不到 → {hint(key)}")
        return ""
    code, text = run([path, *args])
    out = text.splitlines()
    first = out[0] if out else "（無版本資訊）"
    if code != 0:
        add(label, required, False, f"{path} 無法執行：{first[:80]} → {hint(key)}")
        return ""
    note = "" if shutil.which(exe) else f"（在 {Path(path).parent}，但不在 PATH：重開 AI 工具，或把該資料夾加入 PATH）"
    add(label, required, True, first[:80] + note)
    return path


def check_plantuml() -> None:
    """PlantUML 能執行就代表 Java 可用（Homebrew 版自帶 Java）；不能執行時才另外檢查 Java。"""
    path = find("plantuml")
    if not path:
        add("PlantUML（本機渲染）", True, False, f"找不到 → {hint('plantuml')}")
        check_simple("Java（PlantUML 需要）", "java", ["-version"], "java")
        return
    _, out = run([path, "-version"], timeout=120)
    m = re.search(r"PlantUML version ([\w.]+)", out)
    if not m:
        add("PlantUML（本機渲染）", True, False, f"{path} 無法執行（多半缺 Java）：{out[:120] or '無輸出'}")
        check_simple("Java（PlantUML 需要）", "java", ["-version"], "java")
        return
    note = ""
    if not shutil.which("plantuml"):
        note = f"（在 {Path(path).parent}，但不在 PATH → {path_hint(Path(path).parent)}）"
    add("PlantUML（本機渲染）", True, True, m.group(1) + note)


def path_hint(folder: Path) -> str:
    if SYSTEM == "win":
        return ('powershell -Command "[Environment]::SetEnvironmentVariable(\'Path\', '
                f'[Environment]::GetEnvironmentVariable(\'Path\',\'User\') + \';{folder}\', \'User\')"'
                "（之後重開 AI 工具）")
    return f'在 ~/.zshrc 加一行 export PATH="{folder}:$PATH"（之後重開終端機）'


def check_kit() -> None:
    git = find("git")
    detail = f"{version()}（{KIT}）"
    if git:   # 部分下載時 .git 在上層（~/NewebDoc），直接問 git
        code, log = run([git, "-C", str(KIT), "log", "-1", "--format=%h %cs"])
        if code == 0 and log:
            detail += f"，最後更新 {log}"
    add("screen-spec-kit 工具組", True, True, detail)


def install_plantuml() -> int:
    """下載 PlantUML 官方最新 jar（GitHub releases），建立 plantuml 指令到 <工具組>/.bin/。"""
    print("下載 PlantUML（官方 GitHub releases）…")
    api = "https://api.github.com/repos/plantuml/plantuml/releases/latest"
    req = urllib.request.Request(api, headers={"User-Agent": "screen-spec-kit-doctor", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    assets = [a for a in data.get("assets", []) if re.fullmatch(r"plantuml-[\d.]+\.jar", a["name"])]
    if not assets:
        print(f"錯誤｜找不到 plantuml jar（{data.get('tag_name')}）；請到 https://plantuml.com/download 手動下載")
        return 1
    asset = assets[0]
    BIN.mkdir(exist_ok=True)
    jar = BIN / "plantuml.jar"
    req = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "screen-spec-kit-doctor"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(jar, "wb") as f:
        shutil.copyfileobj(resp, f)
    if SYSTEM == "win":
        launcher = BIN / "plantuml.cmd"
        launcher.write_text('@echo off\r\njava -jar "%~dp0plantuml.jar" %*\r\n', encoding="ascii")
    else:
        launcher = BIN / "plantuml"
        launcher.write_text('#!/bin/sh\nexec java -jar "$(dirname "$0")/plantuml.jar" "$@"\n', encoding="ascii")
        launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"已下載｜{asset['name']} → {jar}")
    print(f"已建立｜{launcher}")
    if not shutil.which("plantuml"):
        print(f"下一步｜把 {BIN} 加入 PATH：{path_hint(BIN)}")
    print(f"然後再執行 {PY} tools/doctor.py 確認")
    return 0


def main() -> int:
    if "--install-plantuml" in sys.argv:
        return install_plantuml()
    name = {"mac": "macOS", "win": "Windows", "linux": "Linux"}[SYSTEM]
    print(f"環境檢查｜{name} {platform.release()}（{platform.machine()}）")
    check_python()
    check_simple("Git", "git", ["--version"], "git")
    check_simple("Graphviz（架構圖排版）", "dot", ["-V"], "graphviz")
    check_plantuml()
    check_simple("rsvg-convert（選用：預覽圖）", "rsvg-convert", ["--version"], "rsvg", required=False)
    check_kit()
    if SYSTEM == "mac" and not shutil.which("brew"):
        print("提醒｜沒有 Homebrew。請使用者自己在「終端機」App 貼上並輸入密碼（AI 不代輸密碼）：")
        print('  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
    missing = 0
    for label, required, ok, detail in results:
        tag = "OK  " if ok else ("缺少" if required else "略過")
        print(f"{tag}｜{label}：{detail}")
        missing += (required and not ok)
    print("環境：全部就緒" if not missing else f"環境：缺 {missing} 項必要軟體，依上面的指令安裝後再檢查一次")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
