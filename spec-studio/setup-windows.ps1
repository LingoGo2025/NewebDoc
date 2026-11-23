# screen-spec-kit 安裝腳本（Windows）
#
# 在 PowerShell 執行（開始選單搜尋「PowerShell」，不需要系統管理員）：
#   [Net.ServicePointManager]::SecurityProtocol=3072; $w=New-Object Net.WebClient; $w.Encoding=[Text.Encoding]::UTF8; iex $w.DownloadString('https://lingogo2025.github.io/NewebDoc/spec-studio/setup-windows.ps1')
#
# 會做的事（全部放在 %USERPROFILE%\NewebDoc，不需要 winget、安裝程式或系統管理員權限；可重複執行，已裝好的會略過）：
#   1. Python：電腦已有 3.9 以上就沿用；沒有就下載免安裝版（python-build-standalone）到 NewebDoc\env\python
#   2. 工具組：下載或更新到 NewebDoc\spec-studio（不需要 Git）
#   3. PlantUML：x64 下載官方免安裝版（不需要 Java、Graphviz）；ARM64 等改用官方 jar＋免安裝版 Java（env\java）
#   4. 把 NewebDoc\env\bin 與 Python 加到使用者 PATH、設定 PYTHONUTF8=1，最後執行環境檢查

& {
  # 不用 Stop：Windows PowerShell 5.1 會把外部程式寫到 stderr 的訊息當成錯誤中斷；重要步驟各自檢查
  $ErrorActionPreference = 'Continue'
  $ProgressPreference = 'SilentlyContinue'   # Windows PowerShell 5.1 顯示進度條會讓下載變很慢
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

  $Raw = if ($env:SSK_RAW) { $env:SSK_RAW } else { 'https://raw.githubusercontent.com/lingogo2025/NewebDoc/main/spec-studio' }
  $Root = if ($env:SSK_ROOT) { $env:SSK_ROOT } else { Join-Path $env:USERPROFILE 'NewebDoc' }
  $Kit = Join-Path $Root 'spec-studio'
  $EnvDir = Join-Path $Root 'env'
  $Bin = Join-Path $EnvDir 'bin'
  $PyTag = '20261110'
  $PyVer = '3.12.16'
  $PumlVer = '1.2026.10'

  function Say($m) { Write-Host ''; Write-Host "== $m" -ForegroundColor Cyan }
  function Ok($m) { Write-Host "OK  | $m" -ForegroundColor Green }
  function Warn($m) { Write-Host "提醒| $m" -ForegroundColor Yellow }
  function Get-File($url, $out) {
    Write-Host "下載 $url"
    (New-Object Net.WebClient).DownloadFile($url, $out)
  }
  function Test-Python($exe) {
    if (-not $exe) { return $false }
    try {
      & $exe -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>$null | Out-Null
      return ($LASTEXITCODE -eq 0)
    } catch { return $false }
  }

  try {
    New-Item -ItemType Directory -Force -Path $Bin -ErrorAction Stop | Out-Null
    $Tmp = Join-Path ([IO.Path]::GetTempPath()) ("ssk-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $Tmp -ErrorAction Stop | Out-Null

    Say '1/4 Python'
    $Py = $null
    $Mine = Join-Path $EnvDir 'python\python.exe'
    if (Test-Python $Mine) {
      $Py = $Mine
    } else {
      $cmd = Get-Command python -ErrorAction SilentlyContinue
      # WindowsApps 裡的 python.exe 是「到 Microsoft Store 安裝」的捷徑，不是真的 Python
      if ($cmd -and ($cmd.Source -notlike '*WindowsApps*') -and (Test-Python $cmd.Source)) { $Py = $cmd.Source }
    }
    if (-not $Py) {
      $arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'aarch64' } else { 'x86_64' }
      $zip = Join-Path $Tmp 'python.tar.gz'
      Get-File "https://github.com/astral-sh/python-build-standalone/releases/download/$PyTag/cpython-$PyVer+$PyTag-$arch-pc-windows-msvc-install_only.tar.gz" $zip
      $old = Join-Path $EnvDir 'python'
      if (Test-Path $old) { Remove-Item -Recurse -Force $old -ErrorAction Stop }
      & tar.exe -xzf $zip -C $EnvDir
      if ($LASTEXITCODE -ne 0) { throw "Python 解壓失敗（需要 Windows 10 1803 以上內建的 tar）" }
      $Py = $Mine
      if (-not (Test-Python $Py)) { throw "Python 解壓後無法執行：$Py" }
    }
    Ok ("Python：" + (& $Py --version 2>&1) + "（$Py）")

    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'

    Say '2/4 工具組'
    $upd = Join-Path $Tmp 'update_kit.py'
    Get-File "$Raw/tools/update_kit.py" $upd
    $env:SSK_RAW = $Raw
    & $Py $upd --dest $Kit
    if ($LASTEXITCODE -ne 0) { throw "工具組下載失敗" }
    if (-not (Test-Path (Join-Path $Kit 'tools\doctor.py'))) { throw "工具組下載不完整：找不到 $Kit\tools\doctor.py" }
    Ok ("工具組：$Kit（" + (Get-Content (Join-Path $Kit 'VERSION')) + "）")

    Say '3/4 PlantUML'
    # x64：官方 native 版（單一 exe，不需要 Java、Graphviz）
    # 其他（ARM64 等）：官方 jar ＋ 免安裝版 Java（Eclipse Temurin JRE），一樣不需要 Graphviz
    $PumlCmd = Join-Path $Bin 'plantuml.cmd'
    $PumlDir = Join-Path $EnvDir 'plantuml'
    $JavaDir = Join-Path $EnvDir 'java'
    function Test-Puml($cmd) {
      if (-not (Test-Path $cmd)) { return $false }
      $v = & $cmd -version 2>&1 | Out-String
      return ($v -match 'PlantUML version')
    }
    $useNative = ($env:PROCESSOR_ARCHITECTURE -eq 'AMD64') -and (-not $env:SSK_FORCE_JAVA)
    if (Test-Puml $PumlCmd) {
      Ok "PlantUML：已安裝（$PumlCmd）"
    } elseif ($useNative) {
      $zip = Join-Path $Tmp 'plantuml.zip'
      Write-Host "PlantUML 免安裝版約 50MB，請稍候…"
      Get-File "https://github.com/plantuml/plantuml/releases/download/v$PumlVer/native-plantuml-windows-amd64-$PumlVer.zip" $zip
      if (Test-Path $PumlDir) { Remove-Item -Recurse -Force $PumlDir -ErrorAction Stop }
      Expand-Archive -Path $zip -DestinationPath $PumlDir -Force -ErrorAction Stop
      Set-Content -Path $PumlCmd -Value "@`"%~dp0..\plantuml\plantuml.exe`" %*" -Encoding ASCII -ErrorAction Stop
      if (-not (Test-Puml $PumlCmd)) { throw "PlantUML 無法執行：$PumlDir\plantuml.exe（可能被公司防毒或應用程式控制擋下）" }
      Ok "PlantUML：$PumlVer（native 版）"
    } else {
      $java = Join-Path $JavaDir 'bin\java.exe'
      if (-not (Test-Path $java)) {
        $jarch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'aarch64' } else { 'x64' }
        $zip = Join-Path $Tmp 'java.zip'
        Write-Host "下載免安裝版 Java（約 45MB）…"
        Get-File "https://api.adoptium.net/v3/binary/latest/21/ga/windows/$jarch/jre/hotspot/normal/eclipse" $zip
        $x = Join-Path $Tmp 'java'
        Expand-Archive -Path $zip -DestinationPath $x -Force -ErrorAction Stop
        $inner = Get-ChildItem -Path $x -Directory | Select-Object -First 1
        if (-not $inner) { throw "Java 壓縮檔內容不如預期" }
        if (Test-Path $JavaDir) { Remove-Item -Recurse -Force $JavaDir -ErrorAction Stop }
        Move-Item -Path $inner.FullName -Destination $JavaDir -ErrorAction Stop
      }
      if (-not (Test-Path $java)) { throw "Java 解壓後找不到 $java" }
      New-Item -ItemType Directory -Force -Path $PumlDir -ErrorAction Stop | Out-Null
      Write-Host "下載 PlantUML $PumlVer（jar，約 28MB）…"
      Get-File "https://github.com/plantuml/plantuml/releases/download/v$PumlVer/plantuml-$PumlVer.jar" (Join-Path $PumlDir 'plantuml.jar')
      Set-Content -Path $PumlCmd -Value "@`"%~dp0..\java\bin\java.exe`" -jar `"%~dp0..\plantuml\plantuml.jar`" %*" -Encoding ASCII -ErrorAction Stop
      if (-not (Test-Puml $PumlCmd)) { throw "PlantUML 無法執行：$PumlCmd（可能被公司防毒或應用程式控制擋下）" }
      Ok "PlantUML：$PumlVer（jar ＋ 免安裝版 Java）"
    }

    Say '4/4 設定 PATH 與編碼'
    $add = @($Bin)
    if ($Py -eq $Mine) { $add += (Join-Path $EnvDir 'python'); $add += (Join-Path $EnvDir 'python\Scripts') }
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $parts = @()
    if ($userPath) { $parts = $userPath -split ';' | Where-Object { $_ } }
    $new = @($add | Where-Object { $parts -notcontains $_ }) + $parts
    if ($new.Count -ne $parts.Count) {
      [Environment]::SetEnvironmentVariable('Path', ($new -join ';'), 'User')
      Ok ("已加入使用者 PATH：" + (($add | Where-Object { $parts -notcontains $_ }) -join '; '))
    } else {
      Ok '使用者 PATH 已設定'
    }
    [Environment]::SetEnvironmentVariable('PYTHONUTF8', '1', 'User')
    Ok 'PYTHONUTF8=1'
    $env:Path = (($add + ($env:Path -split ';')) | Select-Object -Unique) -join ';'

    Say '環境檢查'
    & $Py (Join-Path $Kit 'tools\doctor.py')
    Write-Host ''
    if ($LASTEXITCODE -eq 0) {
      Write-Host '完成！下一步：重新開啟 AI 工具（Claude Code 或 Codex），在一個空資料夾貼上入門頁第 3 步的提示詞。' -ForegroundColor Green
    } else {
      Write-Host '環境還沒就緒，請把上面的訊息貼給維護者或 AI 協助。' -ForegroundColor Yellow
    }
  } catch {
    Write-Host ''
    Write-Host ("錯誤| " + $_.Exception.Message) -ForegroundColor Red
    Write-Host '請把上面的訊息貼給維護者或 AI 協助；修正後可以重新執行同一行指令。' -ForegroundColor Yellow
  } finally {
    if ($Tmp -and (Test-Path $Tmp)) { Remove-Item -Recurse -Force $Tmp -ErrorAction SilentlyContinue }
  }
}
