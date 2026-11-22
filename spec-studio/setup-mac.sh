#!/bin/bash
# screen-spec-kit 安裝腳本（macOS）
#
# 在「終端機」App 執行：
#   curl -fsSL https://lingogo2025.github.io/NewebDoc/spec-studio/setup-mac.sh | bash
#
# 會做的事（全部放在 ~/NewebDoc，不需要密碼、Homebrew 或系統管理員權限；可重複執行，已裝好的會略過）：
#   1. Python：電腦已有 3.9 以上就沿用；沒有就下載免安裝版（python-build-standalone）到 ~/NewebDoc/env/python
#   2. 工具組：下載或更新到 ~/NewebDoc/spec-studio（不需要 Git）
#   3. PlantUML：已有就沿用；Apple 晶片下載官方免安裝版（不需要 Java、Graphviz）；Intel Mac 改用官方 jar＋免安裝版 Java（env/java）
#   4. 把 ~/NewebDoc/env/bin 加到 PATH（寫入 ~/.zshrc），最後執行環境檢查
set -euo pipefail

RAW="${SSK_RAW:-https://raw.githubusercontent.com/lingogo2025/NewebDoc/main/spec-studio}"
ROOT="${SSK_ROOT:-$HOME/NewebDoc}"
KIT="$ROOT/spec-studio"
ENVD="$ROOT/env"
PY_TAG="20261110"
PY_VER="3.12.16"
PUML_VER="1.2026.10"
ARCH="$(uname -m)"

say()  { printf '\n== %s\n' "$1"; }
ok()   { printf 'OK  ｜%s\n' "$1"; }
warn() { printf '提醒｜%s\n' "$1"; }
fail() { printf '錯誤｜%s\n' "$1" >&2; exit 1; }
py_ok() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; }

mkdir -p "$ENVD/bin"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

say "1/4 Python"
PY=""
if [ -x "$ENVD/python/bin/python3" ] && py_ok "$ENVD/python/bin/python3"; then
  PY="$ENVD/python/bin/python3"
elif command -v python3 >/dev/null 2>&1 && [ "$(command -v python3)" != "/usr/bin/python3" ] && py_ok python3; then
  PY="$(command -v python3)"
elif xcode-select -p >/dev/null 2>&1 && py_ok /usr/bin/python3; then
  # 沒裝 Xcode 命令列工具時 /usr/bin/python3 會跳出安裝視窗，所以先確認 xcode-select
  PY="/usr/bin/python3"
fi
if [ -z "$PY" ]; then
  case "$ARCH" in
    arm64)  TRIPLE="aarch64-apple-darwin" ;;
    x86_64) TRIPLE="x86_64-apple-darwin" ;;
    *) fail "不支援的處理器 $ARCH" ;;
  esac
  echo "下載免安裝版 Python $PY_VER …"
  curl -fL --progress-bar -o "$TMP/python.tar.gz" \
    "https://github.com/astral-sh/python-build-standalone/releases/download/$PY_TAG/cpython-$PY_VER+$PY_TAG-$TRIPLE-install_only.tar.gz"
  rm -rf "$ENVD/python"
  tar -xzf "$TMP/python.tar.gz" -C "$ENVD"
  PY="$ENVD/python/bin/python3"
  py_ok "$PY" || fail "Python 解壓後無法執行：$PY"
  ln -sf "$PY" "$ENVD/bin/python3"
fi
ok "Python：$("$PY" --version 2>&1)（$PY）"

say "2/4 工具組"
curl -fsSL -o "$TMP/update_kit.py" "$RAW/tools/update_kit.py"
SSK_RAW="$RAW" "$PY" "$TMP/update_kit.py" --dest "$KIT"
[ -f "$KIT/tools/doctor.py" ] || fail "工具組下載不完整：找不到 $KIT/tools/doctor.py"
ok "工具組：$KIT（$(cat "$KIT/VERSION")）"

say "3/4 PlantUML"
puml_ok() { "$1" -version 2>/dev/null | grep -q "PlantUML version"; }
if [ -x "$ENVD/bin/plantuml" ] && puml_ok "$ENVD/bin/plantuml"; then
  ok "PlantUML：已安裝（$ENVD/bin/plantuml）"
elif command -v plantuml >/dev/null 2>&1 && puml_ok plantuml; then
  ok "PlantUML：沿用 $(command -v plantuml)"
elif [ "$ARCH" = "arm64" ] && [ -z "${SSK_FORCE_JAVA:-}" ]; then
  echo "下載 PlantUML $PUML_VER（官方免安裝版，約 55MB）…"
  curl -fL --progress-bar -o "$TMP/plantuml.zip" \
    "https://github.com/plantuml/plantuml/releases/download/v$PUML_VER/native-plantuml-macos-arm64-$PUML_VER.zip"
  rm -rf "$ENVD/plantuml"
  mkdir -p "$ENVD/plantuml"
  unzip -q -o "$TMP/plantuml.zip" -d "$ENVD/plantuml"
  chmod +x "$ENVD/plantuml/plantuml"
  ln -sf "$ENVD/plantuml/plantuml" "$ENVD/bin/plantuml"
  puml_ok "$ENVD/bin/plantuml" || fail "PlantUML 無法執行：$ENVD/bin/plantuml"
  ok "PlantUML：$PUML_VER（$ENVD/bin/plantuml）"
else
  # Intel Mac：官方 jar ＋ 免安裝版 Java（Eclipse Temurin JRE），不需要 Graphviz
  JAVA="$ENVD/java/Contents/Home/bin/java"
  if [ ! -x "$JAVA" ]; then
    case "$ARCH" in arm64) JARCH="aarch64" ;; *) JARCH="x64" ;; esac
    echo "下載免安裝版 Java（約 45MB）…"
    curl -fL --progress-bar -o "$TMP/java.tar.gz" \
      "https://api.adoptium.net/v3/binary/latest/21/ga/mac/$JARCH/jre/hotspot/normal/eclipse"
    mkdir -p "$TMP/java"
    tar -xzf "$TMP/java.tar.gz" -C "$TMP/java"
    rm -rf "$ENVD/java"
    mv "$(find "$TMP/java" -mindepth 1 -maxdepth 1 -type d | head -1)" "$ENVD/java"
  fi
  [ -x "$JAVA" ] || fail "Java 解壓後找不到 $JAVA"
  mkdir -p "$ENVD/plantuml"
  echo "下載 PlantUML $PUML_VER（jar，約 28MB）…"
  curl -fL --progress-bar -o "$ENVD/plantuml/plantuml.jar" \
    "https://github.com/plantuml/plantuml/releases/download/v$PUML_VER/plantuml-$PUML_VER.jar"
  rm -f "$ENVD/bin/plantuml"
  printf '#!/bin/sh\nD="$(cd "$(dirname "$0")/.." && pwd)"\nexec "$D/java/Contents/Home/bin/java" -jar "$D/plantuml/plantuml.jar" "$@"\n' > "$ENVD/bin/plantuml"
  chmod +x "$ENVD/bin/plantuml"
  puml_ok "$ENVD/bin/plantuml" || fail "PlantUML 無法執行：$ENVD/bin/plantuml"
  ok "PlantUML：$PUML_VER（jar ＋ 免安裝版 Java）"
fi

say "4/4 設定 PATH"
LINE="export PATH=\"$ENVD/bin:\$PATH\"  # screen-spec-kit"
for RC in "$HOME/.zshrc" "$HOME/.bash_profile"; do
  if [ "$RC" = "$HOME/.bash_profile" ] && [ ! -f "$RC" ]; then
    continue
  fi
  if ! grep -qF "# screen-spec-kit" "$RC" 2>/dev/null; then
    printf '\n%s\n' "$LINE" >> "$RC"
    ok "已寫入 $RC"
  else
    ok "$RC 已設定"
  fi
done
export PATH="$ENVD/bin:$PATH"

say "環境檢查"
set +e
"$PY" "$KIT/tools/doctor.py"
CODE=$?
set -e
echo
if [ "$CODE" -eq 0 ]; then
  echo "完成！下一步：重新開啟 AI 工具（Claude Code 或 Codex），在一個空資料夾貼上入門頁第 3 步的提示詞。"
else
  echo "環境還沒就緒，請把上面的訊息貼給維護者或 AI 協助。"
fi
