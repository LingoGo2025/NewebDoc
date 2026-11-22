#!/usr/bin/env python3
"""點選式問卷：把 AI 要問的問題做成一個網頁，用瀏覽器打開讓使用者點選，填完按「複製答案」貼回給 AI。

用法：
  python3 scripts/ask.py <問題.json>                 # 產生問卷網頁並用瀏覽器打開
  python3 scripts/ask.py <問題.json> --out <檔案.html>  # 指定輸出位置
  python3 scripts/ask.py <問題.json> --no-open       # 只產生，不打開
  python3 scripts/ask.py --example                   # 印出問題 JSON 範例
  python3 scripts/ask.py --start "<目前資料夾>"        # 內建問卷「建立專案」：名稱、主題、位置、模式（不用寫 JSON）
  python3 scripts/ask.py --example auto              # 印出全自動 10 題的骨架（AI 依主題改寫選項後再執行）

建立專案前（還沒有專案資料夾）也能用：直接執行工具組裡的 engine/scripts/ask.py。本工具不讀專案設定。
預設輸出到目前資料夾的 .ssk-ask/（AI 工具的沙盒一定允許寫入；建立專案時 init_project.py 會忽略並清掉它）；
寫不進去時依序改試家目錄的 NewebDoc/ask/、系統暫存資料夾。檔名一律英文。

問題 JSON：
  title, intro                  問卷標題與說明
  questions: [                  每題：
    {"id": "name", "type": "text" | "textarea" | "single" | "multi",
     "label": "題目", "help": "補充說明（選填）", "placeholder": "（text／textarea）", "required": true,
     "options": [{"label": "選項", "desc": "說明", "recommended": true, "reason": "AI 建議的理由"}],   # single／multi
     "other": true}             # single／multi：加「其他（自行填寫）」
  ]
AI 建議的選項會預先選好並標「AI 建議」；頁面有「全部照建議」按鈕。使用者按「完成並複製答案」後，
答案以文字格式複製到剪貼簿，貼回 AI 工具即可。打不開瀏覽器時，請使用者自行雙擊產生的檔案。
"""
from __future__ import annotations

import datetime
import html
import json
import re
import sys
import webbrowser
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

EXAMPLE = {
    "title": "建立專案",
    "intro": "請點選或填寫下面的問題，完成後按「完成並複製答案」，再貼回 AI 工具。",
    "questions": [
        {"id": "name", "type": "text", "label": "專案名稱", "placeholder": "例如：停車場月租與臨停繳費平台", "required": True},
        {"id": "topic", "type": "textarea", "label": "主題", "help": "用幾句話描述這個系統給誰用、做什麼。",
         "placeholder": "例如：車主可以線上查空位、臨停繳費、申請月租；場站人員在後台管理…", "required": True},
        {"id": "location", "type": "single", "label": "專案位置", "options": [
            {"label": "放在目前資料夾", "desc": "C:\\新專案", "recommended": True, "reason": "目前資料夾是空的"},
            {"label": "在目前資料夾裡新建子資料夾"}], "other": True},
        {"id": "mode", "type": "single", "label": "建立模式", "required": True, "options": [
            {"label": "全自動", "desc": "AI 一次問最多 10 題，之後直接產出 12 個階段的第一版，再一起審閱",
             "recommended": True, "reason": "案子初期最快看到整體"},
            {"label": "階段式", "desc": "12 個階段一題一題問，每一步確認後才寫入"}]},
    ],
}

AUTO_SKELETON = {
    "title": "全自動起稿：確認方向",
    "intro": "AI 依你的主題預先選好建議（標「AI 建議」），可以直接按「全部照 AI 建議」再按完成；要改的再點選或填寫。",
    "questions": [
        {"id": "users", "type": "single", "label": "主要使用者或客戶", "options": [
            {"label": "〈依主題填寫，例如：一般民眾〉", "recommended": True, "reason": "〈一句理由〉"}, {"label": "〈另一種〉"}], "other": True},
        {"id": "regions", "type": "multi", "label": "需要的區域", "options": [
            {"label": "前台", "recommended": True}, {"label": "會員中心", "recommended": True}, {"label": "後台", "recommended": True},
            {"label": "對外 API", "desc": "提供 API 給其他系統呼叫"}]},
        {"id": "features", "type": "multi", "label": "第一版的核心功能", "help": "AI 依主題列出建議，取消勾選不要的，或在「其他」補充。",
         "options": [{"label": "〈功能一〉", "recommended": True}, {"label": "〈功能二〉", "recommended": True}], "other": True},
        {"id": "scale", "type": "single", "label": "規模", "required": True, "options": [
            {"label": "標準（約 30 頁）", "recommended": True, "reason": "第一版夠完整、審閱負擔適中"},
            {"label": "精簡（約 15 頁）"}, {"label": "完整（約 50 頁）"}]},
        {"id": "admin_roles", "type": "single", "label": "後台角色分工", "options": [
            {"label": "〈依主題，例如：總管理者、營運人員、客服〉", "recommended": True}, {"label": "只有一種管理者"}], "other": True},
        {"id": "externals", "type": "multi", "label": "已知要串接的外部系統", "options": [
            {"label": "〈依主題，例如：金流〉", "recommended": True}, {"label": "簡訊／Email"}], "other": True},
        {"id": "api", "type": "single", "label": "是否提供對外 API", "options": [
            {"label": "〈提供或先不提供，依主題建議〉", "recommended": True, "reason": "〈一句理由〉"}, {"label": "〈另一個選項〉"}]},
        {"id": "brand", "type": "single", "label": "品牌主色", "options": [
            {"label": "先沿用預設", "recommended": True}], "other": True},
        {"id": "legacy", "type": "single", "label": "有沒有要移轉的舊系統", "options": [
            {"label": "先標待確認", "recommended": True, "reason": "移轉範圍需要實際資料才能判斷"}, {"label": "沒有"}], "other": True},
        {"id": "rules", "type": "textarea", "label": "特殊業務規則或畫面禁用的用語（選填）",
         "placeholder": "沒有就留空；費率、金額、法規等細節會先標待確認"},
    ],
}


def start_questions(folder: str) -> dict:
    """內建問卷「建立專案」：名稱、主題、位置、模式。目前資料夾是空的就建議直接放這裡。"""
    path = Path(folder).expanduser()
    empty = not path.exists() or not any(p for p in path.iterdir() if not p.name.startswith("."))
    return {
        "title": "建立專案",
        "intro": "請填寫專案名稱與主題，點選位置與模式，完成後按「完成並複製答案」，再貼回 AI 工具。",
        "questions": [
            {"id": "name", "type": "text", "label": "專案名稱", "required": True, "placeholder": "例如：停車場月租與臨停繳費平台"},
            {"id": "topic", "type": "textarea", "label": "主題", "required": True,
             "help": "用幾句話描述這個系統給誰用、做什麼；越具體，第一版越準。",
             "placeholder": "例如：車主可以線上查空位、臨停繳費、申請月租；場站人員在後台管理車位、費率與異常…"},
            {"id": "location", "type": "single", "label": "專案位置", "required": True, "options": [
                {"label": "放在目前資料夾", "desc": str(path), "recommended": empty,
                 "reason": "目前資料夾是空的" if empty else ""},
                {"label": "在目前資料夾裡新建一個以專案名稱命名的子資料夾", "recommended": not empty,
                 "reason": "" if empty else "目前資料夾不是空的"}], "other": True},
            {"id": "mode", "type": "single", "label": "建立模式", "required": True, "options": [
                {"label": "全自動", "recommended": True, "reason": "案子初期最快看到整體",
                 "desc": "AI 再問你最多 10 題（同樣用問卷），之後直接產出網站地圖、每頁示意圖、流程、架構圖等 12 個階段的第一版（每頁列出待確認事項），推測內容標「AI 起稿」，之後再一起審閱"},
                {"label": "階段式", "desc": "12 個階段一題一題問，每一步確認後才寫入，適合需求已經很清楚的情況"}]},
        ],
    }


PAGE = r"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__｜問卷</title>
<style>
:root{--bg:#f5f6f2;--surface:#fffefa;--ink:#203f3c;--text:#3e5751;--muted:#6e827a;--line:#dce7df;--accent:#087e78;--accent-ink:#fff;
  --accent-soft:#e6f2eb;--rec:#b4690e;--rec-soft:#fff3e2;--err:#b3261e;--shadow:0 3px 14px rgba(30,69,61,.07)}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#121a19;--surface:#1a2523;--ink:#e3eeea;--text:#c3d3ce;--muted:#8fa49d;
  --line:#2c3b38;--accent:#4cc2b8;--accent-ink:#0d1f1d;--accent-soft:#1d3532;--rec:#f0b35a;--rec-soft:#2e2516;--err:#ff8a80;--shadow:none}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.7 "PingFang TC","Noto Sans TC","Microsoft JhengHei",system-ui,sans-serif}
.wrap{width:min(860px,100%);margin:0 auto;padding:36px 20px 120px}
h1{font-size:28px;color:var(--ink);margin:0 0 6px}
.intro{margin:0 0 18px;color:var(--text)}
.bar{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 20px}
button{font:inherit;cursor:pointer}
.ghost{background:none;border:2px solid var(--accent);color:var(--accent);border-radius:10px;padding:6px 14px;font-weight:700}
.q{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:0 0 16px;box-shadow:var(--shadow)}
.q.missing{border-color:var(--err)}
.q h2{font-size:18px;color:var(--ink);margin:0 0 4px;display:flex;gap:10px;align-items:baseline}
.q h2 .n{color:var(--accent)}
.q h2 .req{font-size:12px;color:var(--err)}
.help{margin:0 0 10px;color:var(--muted);font-size:14px}
.opt{display:grid;grid-template-columns:22px minmax(0,1fr);gap:10px;align-items:start;border:1px solid var(--line);border-radius:10px;
  padding:10px 12px;margin:8px 0;cursor:pointer}
.opt:hover{border-color:var(--accent)}
.opt input{margin:4px 0 0;width:18px;height:18px;accent-color:var(--accent)}
.opt.on{border-color:var(--accent);background:var(--accent-soft)}
.opt b{color:var(--ink)}
.opt .desc{display:block;font-size:14px;color:var(--text)}
.badge{display:inline-block;font-size:12px;font-weight:700;color:var(--rec);background:var(--rec-soft);border-radius:99px;padding:0 8px;margin-left:6px}
.reason{display:block;font-size:13px;color:var(--rec)}
input[type=text],textarea{width:100%;font:inherit;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
textarea{min-height:96px;resize:vertical}
input[type=text]:focus,textarea:focus{outline:2px solid var(--accent);border-color:var(--accent)}
.other{margin-top:6px}
.done{position:fixed;left:0;right:0;bottom:0;background:var(--surface);border-top:1px solid var(--line);padding:12px 20px;display:flex;
  justify-content:center;gap:12px;align-items:center;flex-wrap:wrap}
.primary{background:var(--accent);color:var(--accent-ink);border:0;border-radius:10px;padding:10px 22px;font-weight:700;font-size:16px}
.msg{font-size:14px;color:var(--muted)}
.msg.err{color:var(--err)}
#result{display:none;margin:20px 0 0}
#result textarea{min-height:200px;font:14px/1.6 "SF Mono",Menlo,Consolas,monospace}
#result p{margin:0 0 8px;color:var(--ink);font-weight:700}
</style>
</head>
<body>
<div class="wrap">
<h1>__TITLE__</h1>
<p class="intro">__INTRO__</p>
<div class="bar"><button type="button" class="ghost" id="all-rec">全部照 AI 建議</button></div>
<form id="form" novalidate></form>
<div id="result"><p>已複製答案，請回到 AI 工具貼上。如果沒有複製成功，請全選下面的文字自行複製：</p><textarea id="answer" readonly></textarea></div>
</div>
<div class="done"><button type="button" class="primary" id="finish">完成並複製答案</button><span class="msg" id="msg"></span></div>
<script>
(function () {
  var DATA = __DATA__;
  var form = document.getElementById("form");
  var LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (text != null) e.textContent = text;
    return e;
  }
  DATA.questions.forEach(function (q, i) {
    var box = el("section", { "class": "q", id: "q-" + q.id });
    var h = el("h2"); h.appendChild(el("span", { "class": "n" }, (i + 1) + ".")); h.appendChild(document.createTextNode(q.label));
    if (q.required) h.appendChild(el("span", { "class": "req" }, "必填"));
    box.appendChild(h);
    if (q.help) box.appendChild(el("p", { "class": "help" }, q.help));
    if (q.type === "text" || q.type === "textarea") {
      var input = el(q.type === "text" ? "input" : "textarea", { name: q.id, placeholder: q.placeholder || "" });
      if (q.type === "text") input.type = "text";
      box.appendChild(input);
    } else {
      var type = q.type === "multi" ? "checkbox" : "radio";
      (q.options || []).forEach(function (o, j) {
        var lab = el("label", { "class": "opt" });
        var inp = el("input", { type: type, name: q.id, value: j });
        if (o.recommended) { inp.checked = true; inp.dataset.rec = "1"; }
        lab.appendChild(inp);
        var span = el("span");
        var b = el("b", null, LETTERS[j] + ". " + o.label); span.appendChild(b);
        if (o.recommended) span.appendChild(el("span", { "class": "badge" }, "AI 建議"));
        if (o.desc) span.appendChild(el("span", { "class": "desc" }, o.desc));
        if (o.recommended && o.reason) span.appendChild(el("span", { "class": "reason" }, "理由：" + o.reason));
        lab.appendChild(span);
        box.appendChild(lab);
      });
      if (q.other) {
        var lab2 = el("label", { "class": "opt" });
        var inp2 = el("input", { type: type, name: q.id, value: "other" });
        lab2.appendChild(inp2);
        var span2 = el("span"); span2.appendChild(el("b", null, "其他（自行填寫）"));
        var txt = el("input", { type: "text", "class": "other", "data-other": q.id, placeholder: "請填寫" });
        txt.addEventListener("input", function () { if (txt.value) { inp2.checked = true; mark(); } });
        span2.appendChild(txt); lab2.appendChild(span2); box.appendChild(lab2);
      }
    }
    form.appendChild(box);
  });
  function mark() {
    form.querySelectorAll(".opt").forEach(function (o) { o.classList.toggle("on", o.querySelector("input").checked); });
  }
  form.addEventListener("change", mark); mark();
  document.getElementById("all-rec").addEventListener("click", function () {
    form.querySelectorAll('input[type=radio],input[type=checkbox]').forEach(function (i) { i.checked = i.dataset.rec === "1"; });
    mark();
  });
  document.getElementById("finish").addEventListener("click", function () {
    var lines = ["【問卷答案】" + DATA.title], missing = [];
    DATA.questions.forEach(function (q, i) {
      var box = document.getElementById("q-" + q.id), val = "";
      if (q.type === "text" || q.type === "textarea") {
        val = form.querySelector('[name="' + q.id + '"]').value.trim();
      } else {
        var picked = [].slice.call(form.querySelectorAll('input[name="' + q.id + '"]:checked'));
        val = picked.map(function (p) {
          if (p.value === "other") {
            var t = form.querySelector('[data-other="' + q.id + '"]').value.trim();
            return "其他：" + (t || "（未填寫）");
          }
          var o = q.options[+p.value];
          return LETTERS[+p.value] + ". " + o.label + (o.recommended ? "（AI 建議）" : "");
        }).join("、");
      }
      box.classList.toggle("missing", !!(q.required && !val));
      if (q.required && !val) missing.push(i + 1);
      lines.push((i + 1) + ". " + q.label + "：" + (val || "（未回答）"));
    });
    var msg = document.getElementById("msg");
    if (missing.length) {
      msg.textContent = "第 " + missing.join("、") + " 題是必填"; msg.className = "msg err";
      document.getElementById("q-" + DATA.questions[missing[0] - 1].id).scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    var text = lines.join("\n");
    var area = document.getElementById("answer");
    area.value = text;
    document.getElementById("result").style.display = "block";
    var ok = function () { msg.textContent = "已複製，請貼回 AI 工具"; msg.className = "msg"; };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(ok, function () { area.select(); try { document.execCommand("copy"); ok(); } catch (e) {} });
    } else { area.select(); try { document.execCommand("copy"); ok(); } catch (e) {} }
    area.scrollIntoView({ behavior: "smooth", block: "center" });
  });
})();
</script>
</body>
</html>
"""


def validate(d: dict) -> list[str]:
    errs = []
    if not d.get("title"):
        errs.append("缺少 title")
    qs = d.get("questions") or []
    if not qs:
        errs.append("缺少 questions")
    ids = set()
    for i, q in enumerate(qs, 1):
        if q.get("type") not in ("text", "textarea", "single", "multi"):
            errs.append(f"第 {i} 題 type 須為 text、textarea、single、multi")
        if not q.get("label"):
            errs.append(f"第 {i} 題缺少 label")
        qid = q.get("id") or f"q{i}"
        q["id"] = re.sub(r"[^\w-]", "_", qid)
        if q["id"] in ids:
            errs.append(f"第 {i} 題 id 重複：{qid}")
        ids.add(q["id"])
        if q.get("type") in ("single", "multi") and not q.get("options"):
            errs.append(f"第 {i} 題缺少 options")
        if q.get("type") == "single" and sum(1 for o in q.get("options", []) if o.get("recommended")) > 1:
            errs.append(f"第 {i} 題是單選，只能有一個 AI 建議選項")
    return errs


def build(d: dict) -> str:
    data = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    return (PAGE.replace("__TITLE__", html.escape(d["title"])).replace("__INTRO__", html.escape(d.get("intro", "")))
            .replace("__DATA__", data))


def open_in_browser(path: Path) -> bool:
    """用預設瀏覽器打開；webbrowser 不行時改用系統指令（Windows start、macOS open、Linux xdg-open）。"""
    import os
    import subprocess
    try:
        if webbrowser.open(path.resolve().as_uri()):
            return True
    except Exception:  # noqa: BLE001
        pass
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
            return True
        cmd = ["open", str(path)] if sys.platform == "darwin" else ["xdg-open", str(path)]
        return subprocess.run(cmd, capture_output=True, timeout=15).returncode == 0
    except Exception:  # noqa: BLE001
        return False


def main() -> int:
    args = sys.argv[1:]
    if "--example" in args:
        print(json.dumps(AUTO_SKELETON if "auto" in args else EXAMPLE, ensure_ascii=False, indent=2))
        return 0
    if "--start" in args:
        folder = args[args.index("--start") + 1] if len(args) > args.index("--start") + 1 else "."
        d = start_questions(folder)
        args = [a for a in args if a not in ("--start", folder)]
    else:
        d = None
    files = [a for a in args if not a.startswith("--")]
    if "--out" in args:
        out = Path(args[args.index("--out") + 1]).expanduser()
        files = [f for f in files if f != args[args.index("--out") + 1]]
    else:
        out = None
    if d is None:
        if len(files) != 1:
            print(__doc__)
            return 2
        d = json.loads(Path(files[0]).read_text(encoding="utf-8"))
    errs = validate(d)
    if errs:
        print("問題 JSON 有誤：\n" + "\n".join(f"  - {e}" for e in errs))
        return 1
    page = build(d)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    import tempfile
    candidates = [out] if out is not None else [
        Path.cwd() / ".ssk-ask" / f"{stamp}.html",              # 目前資料夾：沙盒一定可寫
        Path.home() / "NewebDoc" / "ask" / f"{stamp}.html",
        Path(tempfile.gettempdir()) / "ssk-ask" / f"{stamp}.html",
    ]
    out, last_err = None, None
    for cand in candidates:
        try:
            cand.parent.mkdir(parents=True, exist_ok=True)
            cand.write_text(page, encoding="utf-8")
            out = cand
            break
        except OSError as e:
            last_err = e
    if out is None:
        print(f"錯誤｜問卷網頁寫不進任何位置（{last_err}）；請改用文字一次問完這些問題")
        return 1
    print(f"已產生問卷｜{out}")
    print(f"網址｜{out.resolve().as_uri()}")
    opened = False
    if "--no-open" not in args:
        opened = open_in_browser(out)
    print("已用瀏覽器打開。" if opened else "沒能自動打開瀏覽器：請使用者在檔案總管／Finder 雙擊上面這個檔案。")
    print("下一步｜把下面這段話原封不動告訴使用者，然後結束這一輪、等使用者貼回答案，不要繼續：")
    print(f"  已幫你打開問卷「{d['title']}」（如果瀏覽器沒有自動打開，請到檔案總管／Finder 雙擊：{out}）。"
          "請點選、填完後按頁面下方的「完成並複製答案」，再把答案貼回這裡。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
