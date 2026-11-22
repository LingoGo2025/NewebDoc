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
- 工具組若是 Git 部分下載（上層有 .git），改用 git pull。
- 只下載看得見的檔案；以「.」開頭的檔案（如 .claude-plugin/）不在清單內。
- 本機版本比 GitHub 新（維護者尚未上傳）時不覆蓋，除非加 --force。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

# 下載來源；SSK_RAW 可改成其他位置（測試用）
RAW = os.environ.get("SSK_RAW", "https://raw.githubusercontent.com/lingogo2025/NewebDoc/main/screen-spec-kit").rstrip("/")
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


def fetch(path: str) -> bytes:
    url = RAW + "/" + urllib.parse.quote(path)
    req = urllib.request.Request(url, headers={"User-Agent": "screen-spec-kit-update", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def local_version(kit: Path) -> str:
    v = kit / "VERSION"
    return v.read_text(encoding="utf-8").strip() if v.exists() else ""


def ver_tuple(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return ()


def git_update(kit: Path) -> int | None:
    """工具組是 NewebDoc 的 Git 下載時用 git pull；回傳 None 表示不是。"""
    git = shutil.which("git")
    if not git:
        return None
    r = subprocess.run([git, "-C", str(kit), "remote", "get-url", "origin"], capture_output=True, text=True)
    if r.returncode != 0 or "NewebDoc" not in r.stdout:
        return None
    print("工具組是 Git 下載的，改用 git pull …")
    r = subprocess.run([git, "-C", str(kit), "pull"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print((r.stdout + r.stderr).strip())
    return r.returncode


def download(dest: Path) -> int:
    remote_version = fetch("VERSION").decode("utf-8").strip()
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
    if "--check" in args:
        remote = fetch("VERSION").decode("utf-8").strip()
        local = local_version(dest)
        print(f"工具組｜本機 {local or '未安裝'}、GitHub {remote}" + ("（已是最新）" if local == remote else "（可更新）"))
        return 0
    if dest.exists():
        code = git_update(dest)
        if code is not None:
            return code
        local, remote = local_version(dest), fetch("VERSION").decode("utf-8").strip()
        if local and "--force" not in args:
            if ver_tuple(local) > ver_tuple(remote):
                print(f"略過｜本機工具組 {local} 比 GitHub {remote} 新（維護者尚未上傳？）；要覆蓋請加 --force")
                return 0
            if local == remote:
                print(f"工具組已是最新（{local}）")
                return 0
    return download(dest)


if __name__ == "__main__":
    sys.exit(main())
