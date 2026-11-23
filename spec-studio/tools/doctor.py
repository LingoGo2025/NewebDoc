#!/usr/bin/env python3
"""環境檢查：列出 screen-spec-kit 需要的軟體是否就緒，缺少時附上這台電腦（macOS／Windows／Linux）的補救方式。

必要：Python 3.9 以上（Windows 另需 PYTHONUTF8=1）、PlantUML（本機渲染）。缺少時最簡單的做法是讓使用者
自己執行安裝腳本（setup-windows.ps1／setup-mac.sh，見 SETUP_CMD）：免安裝版 Python 與 PlantUML 放在
~/NewebDoc/env，不需要系統管理員權限、winget 或 Homebrew。選用：Git（更新工具組）、rsvg-convert（預覽圖）。

用法：
  python3 tools/doctor.py                     # 檢查（Windows 用 python 或 py -3 代替 python3）
  python3 tools/doctor.py --offline           # 不連 GitHub 比對工具組版本
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

from _kit import ENV, KIT, find_tool, version

SYSTEM = {"Darwin": "mac", "Windows": "win"}.get(platform.system(), "linux")
BIN = KIT / ".bin"
PY = "python3" if SYSTEM != "win" else "python"

# 安裝腳本（使用者自己在 PowerShell／終端機執行；不經過 AI 的沙盒）
PAGES = "https://lingogo2025.github.io/NewebDoc/spec-studio"
SETUP_CMD = {
    "win": ("[Net.ServicePointManager]::SecurityProtocol=3072; $w=New-Object Net.WebClient; "
            f"$w.Encoding=[Text.Encoding]::UTF8; iex $w.DownloadString('{PAGES}/setup-windows.ps1')"),
    "mac": f"curl -fsSL {PAGES}/setup-mac.sh | bash",
    "linux": "sudo apt install python3 plantuml",
}
SETUP_WHERE = {"win": "PowerShell", "mac": "「終端機」App", "linux": "終端機"}

# 個別軟體的手動安裝方式（安裝腳本無法使用時的備案）
HINTS = {
    "git": {"mac": "xcode-select --install（或 brew install git）",
            "win": "（選用，可略過）",
            "linux": "sudo apt install git"},
    "python": {"mac": "執行安裝腳本（或 brew install python）",
               "win": "執行安裝腳本（或 winget install --id Python.Python.3.12 -e）",
               "linux": "sudo apt install python3"},
    "java": {"mac": "brew install openjdk（brew install plantuml 會一併安裝）",
             "win": "執行安裝腳本（ARM64 會自動下載免安裝版 Java）",
             "linux": "sudo apt install default-jre"},
    "graphviz": {"mac": "brew install graphviz（brew install plantuml 會一併安裝）",
                 "win": "winget install --id Graphviz.Graphviz -e",
                 "linux": "sudo apt install graphviz"},
    "plantuml": {"mac": "執行安裝腳本（或 brew install plantuml）",
                 "win": "執行安裝腳本（或 winget 裝 Java 後執行 python tools/doctor.py --install-plantuml）",
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
    """回傳執行檔完整路徑（Windows 的 .cmd 也要完整路徑才執行得到）；找不到回傳空字串。
    依序找 PATH、安裝腳本的 ~/NewebDoc/env/bin、Windows 常見安裝位置、doctor 下載的 .bin/。"""
    hit = find_tool(name)
    if hit:
        return hit
    if SYSTEM == "win":
        for pattern in WIN_GUESS.get(name, []):
            found = sorted(Path("C:/").glob(pattern[3:]))
            if found:
                return str(found[-1])
    if name == "java":   # 安裝腳本的免安裝版 Java
        for cand in (ENV / "java" / "bin" / "java.exe", ENV / "java" / "Contents" / "Home" / "bin" / "java"):
            if cand.exists():
                return str(cand)
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
            "已設定" if utf8 else "未設定 → 執行安裝腳本，或 setx PYTHONUTF8 1（設定後重開 AI 工具；"
            "未重開前可在指令前加 $env:PYTHONUTF8=1;）")


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
        note = f"（在 {Path(path).parent}，還不在 PATH：重開 AI 工具即可；在那之前用完整路徑 {path}）"
    add("PlantUML（本機渲染）", True, True, m.group(1) + note)


def path_hint(folder: Path) -> str:
    if SYSTEM == "win":
        return ('powershell -Command "[Environment]::SetEnvironmentVariable(\'Path\', '
                f'[Environment]::GetEnvironmentVariable(\'Path\',\'User\') + \';{folder}\', \'User\')"'
                "（之後重開 AI 工具）")
    return f'在 ~/.zshrc 加一行 export PATH="{folder}:$PATH"（之後重開終端機）'


KIT_OUTDATED = False


def remote_version() -> str:
    """GitHub 上的工具組版本；連不上（離線、沙盒擋網路）時回傳空字串。"""
    import update_kit
    try:
        req = urllib.request.Request(update_kit.RAW + "/VERSION",
                                     headers={"User-Agent": "screen-spec-kit-doctor", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception:  # noqa: BLE001
        return ""


def ver_tuple(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v))


def check_kit() -> None:
    global KIT_OUTDATED
    local = version()
    detail = f"{local}（{KIT}）"
    git = find("git")
    if git:   # 部分下載時 .git 在上層（~/NewebDoc），直接問 git
        code, log = run([git, "-C", str(KIT), "log", "-1", "--format=%h %cs"])
        if code == 0 and log:
            detail += f"，最後更新 {log}"
    remote = "" if "--offline" in sys.argv else remote_version()
    if remote and ver_tuple(remote) > ver_tuple(local):
        KIT_OUTDATED = True
        add("screen-spec-kit 工具組", True, False,
            f"{local}，GitHub 已有 {remote}：舊版缺少新功能（例如全自動起稿），建立專案前要先更新")
        return
    detail += "（已是最新）" if remote else "（無法連線 GitHub 比對版本：請以允許連網的權限執行 tools/update_kit.py 比對）"
    add("screen-spec-kit 工具組", True, True, detail)
    if ENV.exists():
        add("安裝腳本環境", False, True, str(ENV))


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
    print(f"Python｜{sys.executable}")
    check_python()
    check_plantuml()
    check_simple("Git（選用：更新工具組）", "git", ["--version"], "git", required=False)
    check_simple("rsvg-convert（選用：預覽圖）", "rsvg-convert", ["--version"], "rsvg", required=False)
    check_kit()
    missing = 0
    for label, required, ok, detail in results:
        tag = "OK  " if ok else ("缺少" if required else "略過")
        print(f"{tag}｜{label}：{detail}")
        missing += (required and not ok)
    if missing == 1 and KIT_OUTDATED:
        print("環境：工具組需要更新。執行下面這行（只下載工具組的文字檔，不安裝軟體）；失敗時請使用者重新執行安裝腳本：")
        print(f"  {PY} \"{KIT / 'tools' / 'update_kit.py'}\"")
    elif missing:
        if KIT_OUTDATED:
            print("提醒｜工具組也需要更新：重新執行安裝腳本會一併更新。")
        print(f"環境：缺 {missing} 項必要軟體。最簡單的做法：請使用者自己在{SETUP_WHERE[SYSTEM]}貼上並執行"
              "（免安裝、不需管理員權限；AI 工具的沙盒可能無法安裝軟體）：")
        print(f"  {SETUP_CMD[SYSTEM]}")
    else:
        print("環境：全部就緒")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
