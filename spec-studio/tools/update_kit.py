#!/usr/bin/env python3
"""下載或更新工具組（不需要 Git）：依 FILES.txt 清單從 GitHub 逐檔下載。

用法：
  python3 tools/update_kit.py                 # 更新本工具組（Windows 用 python）
  python3 update_kit.py --dest <資料夾>       # 安裝腳本用：下載完整工具組到指定資料夾
  python3 tools/update_kit.py --check         # 只比對版本，不下載
  python3 tools/update_kit.py --force         # 版本相同或本機較新時仍重新下載
  python3 tools/update_kit.py --write-manifest  # 維護者：重產 FILES.txt（sync_kit.py 會自動執行）

說明：
- 先把所有檔案下載到暫存資料夾，全部成功才覆蓋，網路中斷不會留下一半的工具組。
- 一律依 FILES.txt 逐檔下載，不用 git pull（早期用 Git 部分下載的工具組也照樣覆蓋更新）。
- 只下載看得見的檔案；以「.」開頭的檔案（如 .claude-plugin/）不在清單內。
- 本機版本比 GitHub 新（維護者尚未上傳）時不覆蓋，除非加 --force。
- 版本一律由本工具直接連 GitHub（raw.githubusercontent.com）讀取，不經過 AI 工具的網頁搜尋或快取；
  最後一行固定是「版本｜本機 …、GitHub …：…」，AI 依這一行判斷。
- 連不上 GitHub 時結束代碼為 3，並印出給 AI 的處理方式（以允許連網的權限重跑，或請使用者自己在終端機執行）。
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

# 下載來源；SSK_RAW 可改成其他位置（測試用）
RAW = os.environ.get("SSK_RAW", "https://raw.githubusercontent.com/lingogo2025/NewebDoc/main/spec-studio").rstrip("/")
MANIFEST = "FILES.txt"
SKIP_DIRS = {"__pycache__", ".bin"}
SKIP_TOP = {"examples"}

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def kit_files(kit: Path) -> list[str]:
    """工具組內要發布的檔案（相對路徑，/ 分隔）：排除以「.」開頭的檔案或資料夾、__pycache__、FILES.txt。"""
    out = []
    for p in kit.rglob("*"):
        rel = p.relative_to(kit)
        if not p.is_file() or rel.as_posix() == MANIFEST:
            continue
        if any(part.startswith(".") or part in SKIP_DIRS for part in rel.parts):
            continue
        if rel.parts[0] in SKIP_TOP:   # 範例專案只放在入門頁展示，不下載到使用者電腦
            continue
        out.append(rel.as_posix())
    return sorted(out)


def write_manifest(kit: Path) -> int:
    files = kit_files(kit)
    (kit / MANIFEST).write_text("\n".join(files) + "\n", encoding="utf-8")
    print(f"已更新｜{MANIFEST}（{len(files)} 個檔案）")
    return 0


def fetch(path: str, tries: int = 4) -> bytes:
    """下載一個檔案；網路偶爾逾時或中斷時自動重試（間隔 2、4、8 秒）。"""
    import time
    url = RAW + "/" + urllib.parse.quote(path)
    req = urllib.request.Request(url, headers={"User-Agent": "screen-spec-kit-update", "Cache-Control": "no-cache"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("unreachable")


class Offline(Exception):
    """連不上 GitHub（離線、公司網路或 AI 工具沙盒擋住）。"""


def remote_version() -> str:
    try:
        return fetch("VERSION", tries=2).decode("utf-8").strip()
    except Exception as e:  # noqa: BLE001
        raise Offline(str(e)) from e


def offline_help(local: str, err: str) -> int:
    me = Path(__file__).resolve()
    cmd = f'"{sys.executable}" "{me}"' if os.name == "nt" else f"{Path(sys.executable).name} {me}"
    print(f"無法連線 GitHub（{err[:120]}）")
    print("給 AI：多半是 AI 工具的沙盒擋住網路。請用「允許連網／提升權限」重新執行同一個指令"
          "（Codex 會跳出核准視窗，請使用者按允許；Claude Code 會詢問是否允許）。")
    print(f"仍然不行時，請使用者自己在終端機（PowerShell／終端機 App）執行：{cmd}")
    print("不要改用網頁搜尋、快取或其他網址的版本，它們可能是已刪除的舊版。")
    print(f"版本｜本機 {local or '未安裝'}、GitHub 無法連線：未比對")
    return 3


def local_version(kit: Path) -> str:
    v = kit / "VERSION"
    return v.read_text(encoding="utf-8").strip() if v.exists() else ""


def ver_tuple(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return ()


def download(dest: Path, remote_version: str = "") -> int:
    remote_version = remote_version or fetch("VERSION").decode("utf-8").strip()
    files = [line.strip() for line in fetch(MANIFEST).decode("utf-8").splitlines() if line.strip()]
    print(f"下載工具組 {remote_version}（{len(files)} 個檔案）→ {dest}")
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "kit"
        for i, rel in enumerate(files, 1):
            target = stage / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                target.write_bytes(fetch(rel))
            except Exception as e:  # noqa: BLE001 — 任何下載錯誤都停止，不覆蓋
                print(f"錯誤｜下載失敗：{rel}（{e}）；工具組未變更")
                return 1
            if i % 20 == 0 or i == len(files):
                print(f"  {i}/{len(files)}")
        (stage / MANIFEST).write_text("\n".join(files) + "\n", encoding="utf-8")
        dest.mkdir(parents=True, exist_ok=True)
        # 移除清單外的舊檔（保留以「.」開頭的檔案與 .bin/）
        keep = set(files) | {MANIFEST}
        for old in kit_files(dest):
            if old not in keep:
                (dest / old).unlink()
        for rel in sorted(keep):
            src = stage / rel
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / rel)
    for d in sorted((p for p in dest.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(d.iterdir()) and not d.name.startswith("."):
            d.rmdir()
    print(f"完成｜工具組 {remote_version}")
    print(f"版本｜本機 {remote_version}、GitHub {remote_version}：已更新到最新")
    return 0


def main() -> int:
    args = sys.argv[1:]
    here = Path(__file__).resolve().parent
    kit = here.parent if here.name == "tools" else None
    if "--write-manifest" in args:
        return write_manifest(kit or Path.cwd())
    dest = Path(args[args.index("--dest") + 1]).expanduser().resolve() if "--dest" in args else kit
    if dest is None:
        print("錯誤｜請用 --dest 指定工具組資料夾")
        return 2
    local = local_version(dest) if dest.exists() else ""
    try:
        remote = remote_version()
    except Offline as e:
        return offline_help(local, str(e))
    if "--check" in args:
        state = ("已是最新" if local == remote else "本機較新（維護者尚未上傳？）" if local and ver_tuple(local) > ver_tuple(remote)
                 else "需要更新：執行 update_kit.py（不加 --check）")
        print(f"版本｜本機 {local or '未安裝'}、GitHub {remote}：{state}")
        return 0
    # 一律逐檔下載，不用 git pull：早期用 Git 下載的工具組常因「有未提交的變更」（例如 Windows 換行字元）而更新失敗
    if local and "--force" not in args:
        if ver_tuple(local) > ver_tuple(remote):
            print(f"版本｜本機 {local}、GitHub {remote}：本機較新（維護者尚未上傳？），不覆蓋；要覆蓋請加 --force")
            return 0
        if local == remote:
            print(f"版本｜本機 {local}、GitHub {remote}：已是最新")
            return 0
    try:
        return download(dest, remote)
    except Exception as e:  # noqa: BLE001 — 下載清單途中斷線
        return offline_help(local, str(e))


if __name__ == "__main__":
    sys.exit(main())
