#!/usr/bin/env python3
"""全自動起稿：依一份起稿描述（JSON）一次產生整個新專案的初稿。

用法：
  python3 scripts/draft_apply.py --example           # 印出描述範例（給 AI 參考格式）
  python3 scripts/draft_apply.py <描述.json> --check  # 只檢查描述與品質提醒，不寫檔
  python3 scripts/draft_apply.py <描述.json> --accept-warnings  # 有品質提醒仍寫入（須向使用者說明原因）
  python3 scripts/draft_apply.py <描述.json>          # 寫入（只用於剛建立、尚無頁面的專案）
  python3 scripts/draft_apply.py <描述.json> --screens A03,B05   # 視覺自檢後重畫指定頁面（或 all；只用於未手動調整的初稿）

會做的事：
  1. 改寫 project.json（區域、ID、配色、各區版型）、網站地圖.md（區域、節點、按鈕、共用選單）、
     專案規則.md、規格（使用者、外部系統、業務模組、共用服務、流程參與者、全站共用規則預設值、
     API、各頁段落（SA 規格只列本頁待確認）、跨頁流程、尚待確認、舊系統移轉與相關法規）、architecture/ 兩張架構圖、
     flows/ 流程原稿、index.html 首頁副標與選填兩區
  2. 每頁以 mockup.py 產生 SVG 初稿（依頁面 kind 組合元件，或用描述裡的 blocks）
  3. 依序執行 sync_screen_text、index_build、flow_sync、本機 plantuml、dev_notes、svg_bundle、inventory、check

AI 推測的內容一律標「〔AI 起稿・第 n 階段：待審閱〕」，審閱確認後由 AI 刪除標記；interview_status.py
把這些階段列為「待審閱」。API 欄位、金流、法規、商業政策只列「待確認」，不寫具體內容。
"""
from __future__ import annotations

import colorsys
import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SPEC_NAME = "畫面與流程文字規格.md"
MARK = "〔AI 起稿・第 {} 階段：待審閱〕"
TODAY = datetime.date.today().isoformat()

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

EXAMPLE = {
    "_說明": "格式範例（頁數很少，只示範欄位寫法）；實際頁數依 scale，並照 規範/新專案.md「完整度清單」補齊。"
             "region 可加 device: mobile（手機版示意圖）；頁面可加 stepper/step、price、choices、media、map、tiles、"
             "hero_art/preview、result 與 blocks（元件見 規範/mockup.md）。",
    "summary": "提供營業人開立、作廢、折讓與查詢電子發票的加值服務平台，並以 API 讓營業人系統串接。",
    "short_name": "電子發票平台",
    "scale": "精簡",
    "tagline": "營業人電子發票開立與串接服務",
    "language": "一律使用繁體中文（台灣用語）",
    "brand": {"primary": "#1F6FB2"},
    "answers": [["主要客戶", "營業人（企業）"], ["對外 API", "需要"]],
    "roles": [
        {"name": "訪客", "regions": ["前台"], "desc": "瀏覽方案與申辦"},
        {"name": "營業人管理者", "regions": ["會員中心"], "desc": "開立與管理發票、設定串接"},
        {"name": "平台管理者", "regions": ["後台"], "desc": "審核申辦、管理營業人與系統設定"},
    ],
    "rules": ["一張發票開立後只能作廢或折讓，不可直接修改"],
    "regions": [
        {"name": "前台", "column": "public", "prefix": "A", "desc": "官網、方案介紹與申辦",
         "nodes": [{"title": "方案與申辦", "desc": "介紹服務方案並受理申辦。", "pages": [
             {"id": "A01", "name": "首頁", "desc": "服務特色與方案入口。", "kind": "landing", "module": "申辦與方案",
              "headline": "電子發票，開立、上傳一次完成", "buttons": ["立即申辦", "查看方案"],
              "cards": [{"title": "線上開立與作廢", "meta": "網頁或 API 開立，自動上傳整合服務平台", "button": "了解更多"},
                        {"title": "ERP／POS 串接", "meta": "提供開立、作廢、查詢 API", "button": "了解更多"},
                        {"title": "報表與對帳", "meta": "依期別彙總銷項，一鍵匯出", "button": "了解更多"}]},
             {"id": "A02", "name": "線上申辦", "desc": "填寫營業人資料申請開通。", "kind": "form", "module": "申辦與方案",
              "fields": ["公司名稱*", "統一編號*", "聯絡人*", "Email*", ["營業登記文件", "拖曳 PDF 或圖片到這裡", "upload"], "備註"],
              "stepper": ["填寫資料", "確認送出", "申辦完成"], "step": 1,
              "steps": [["填寫營業人資料", "約 3 分鐘"], ["平台審核", "1–3 個工作天"], ["開通後設定字軌", "收到通知信後登入"]],
              "rules": ["同一統一編號只能有一筆審核中的申辦", "送出後寄送申辦編號到聯絡 Email"],
              "buttons": [["取消", "回首頁 A01"], ["送出申辦", "申辦完成提示，顯示申辦編號"]],
              "pending": ["需要上傳哪些證明文件"],
              "writes": ["新增申辦資料（狀態：審核中）"],
              "acceptance": ["統一編號格式錯誤時不送出", "送出成功後顯示申辦編號並寄出通知信"], "manage": ["C01"]},
             {"id": "A03", "name": "申辦完成", "desc": "顯示申辦編號與後續審核方式。", "kind": "result", "module": "申辦與方案",
              "stepper": ["填寫資料", "確認送出", "申辦完成"], "step": 3,
              "result": {"tone": "ok", "title": "申辦已送出", "text": "審核結果會寄到 service@daxin.com.tw，通常 1–3 個工作天。"},
              "fields": [["申辦編號", "AP-20261123-0042"], ["公司名稱", "大新商行有限公司"], ["送出時間", "2026-11-23 10:42"]],
              "buttons": ["回首頁", "查看申辦進度"], "manage": ["C01"]}]}]},
        {"name": "會員中心", "column": "org", "prefix": "B", "backend": True, "desc": "營業人的發票作業後台",
         "nodes": [{"title": "發票作業", "desc": "開立、查詢與作廢發票。", "pages": [
             {"id": "B01", "name": "發票列表", "desc": "查詢已開立的發票。", "kind": "list", "module": "發票開立與管理",
              "columns": ["發票號碼", "開立日期", "買受人", "金額", "狀態"],
              "sample": [["AB-12345678", "2026-11-20", "大同商行", "12,600", "已上傳"],
                         ["AB-12345677", "2026-11-19", "晨光咖啡", "3,480", "待上傳"],
                         ["AB-12345676", "2026-11-18", "宏達工程", "58,000", "作廢"]],
              "tabs": [["全部", 128], ["待上傳", 6], ["作廢", 3]], "pending": ["上傳失敗時的重送方式"]},
             {"id": "B02", "name": "開立發票", "desc": "輸入買受人與品項開立發票。", "kind": "form", "module": "發票開立與管理",
              "fields": ["買受人統編", "品項", "數量", "單價"], "similar": ["B01"]}]}]},
        {"name": "後台", "column": "admin", "prefix": "C", "backend": True, "desc": "平台管理者後台",
         "nodes": [{"title": "營業人管理", "desc": "審核申辦與管理營業人。", "pages": [
             {"id": "C01", "name": "申辦審核", "desc": "審核營業人申辦資料。", "kind": "list", "module": "申辦與方案",
              "columns": ["申請日", "公司名稱", "統一編號", "狀態"]}]}]},
        {"name": "API", "column": "api", "prefix": "API", "backend": True, "desc": "營業人系統串接",
         "apis": [{"id": "API01", "name": "開立發票 API", "caller": "營業人系統", "desc": "營業人系統呼叫以開立發票。",
                   "module": "發票開立與管理"}]},
    ],
    "modules": [{"name": "申辦與方案"}, {"name": "發票開立與管理"}],
    "services": [{"name": "通知服務", "use": "Email 通知", "external": "Email 服務"}],
    "externals": [
        {"name": "財政部電子發票整合服務平台", "category": "系統需求", "data": "發票上傳、作廢、折讓", "basis": "B02",
         "status": "介接方式與規範待確認"},
        {"name": "Email 服務", "category": "系統需求", "data": "通知信", "basis": "通知服務", "status": "供應商待確認"}],
    "flows": [{"key": "invoice_issue", "title": "開立發票", "order": "B01,B02",
               "summary": "營業人從發票列表進入開立，送出後由平台上傳整合服務平台。",
               "steps": ["營業人管理者 -> 發票列表 B01 : 點「開立發票」",
                         "發票列表 B01 -> 開立發票 B02 : 開啟表單",
                         "營業人管理者 -> 開立發票 B02 : 填寫買受人與品項後送出",
                         "開立發票 B02 -> 發票服務 : 建立發票",
                         "發票服務 -> 財政部電子發票整合服務平台 : 上傳（方式待確認）",
                         "alt 上傳成功",
                         "財政部電子發票整合服務平台 --> 發票服務 : 上傳成功",
                         "發票服務 --> 開立發票 B02 : 顯示開立完成",
                         "else 上傳失敗",
                         "財政部電子發票整合服務平台 --> 發票服務 : 錯誤代碼",
                         "發票服務 --> 開立發票 B02 : 顯示失敗原因並可重送",
                         "end",
                         "note right of 發票服務 : 上傳時限與重送規則待確認"]}],
    "journeys": [
        {"role": "訪客", "task": "申辦電子發票服務",
         "steps": ["A01 首頁點「立即申辦」", "A02 填寫公司資料並上傳營業登記文件", "A03 看到申辦編號與審核時間"],
         "exceptions": ["統一編號已有審核中的申辦 → A02 顯示提示與查詢進度連結", "文件格式不符 → A02 上傳欄位顯示錯誤"]},
        {"role": "營業人管理者", "task": "開立一張發票",
         "steps": ["B01 發票列表點「開立發票」", "B02 輸入買受人與品項後送出", "B01 列表出現新發票，狀態待上傳"],
         "exceptions": ["上傳整合服務平台失敗 → B01 狀態顯示上傳失敗並可重送"]},
        {"role": "平台管理者", "task": "審核申辦",
         "steps": ["C01 申辦審核列表篩選「待審核」", "C01 檢視申辦資料並核准或退回"], "exceptions": ["資料不全 → 退回並填寫原因"]}],
    "benchmark": [
        {"feature": "線上申辦與審核", "scope": "第一版", "pages": ["A02", "A03", "C01"]},
        {"feature": "網頁開立發票", "scope": "第一版", "pages": ["B02"]},
        {"feature": "API 開立", "scope": "第一版", "pages": ["API01"]},
        {"feature": "折讓單", "scope": "之後", "note": "第一版先作廢重開"}],
    "pending": ["加值服務中心的申請資格與營運規範", "與財政部電子發票整合服務平台的介接方式與上傳期限"],
    "migration": {"system": "", "scope": ""},
    "regulations": ["電子發票相關規定", "個人資料保護"],
}

# 區域欄位 → 架構圖與流程類別配色（與範本一致）
REGION_COLORS = {"public": ("#C8EEDF", "#0B8A6B"), "org": ("#D6E0FF", "#3D5BD9"), "admin": ("#FFD9B8", "#D9701E"),
                 "api": ("#E8D5FA", "#8B3FD1")}
EXTRA_COLORS = [("#CFF0F5", "#0F8FA3"), ("#FDE2EC", "#C2416B"), ("#E5F0D0", "#5E8A1E")]
FLOW_CATS = [("front", "#E3F2EE", "#087E78"), ("member", "#E7EBFA", "#5468C4"), ("mgr", "#FCEBDD", "#B87542"),
             ("cross", "#F4F0EA", "#8C7B6B"), ("api", "#F1E8F7", "#8A5BB0"), ("service", "#EAF3F6", "#4F7A86"),
             ("external", "#FFF4D6", "#B8901A"), ("data", "#F1F4F3", "#6E827A")]
COLUMN_CAT = {"public": "front", "org": "member", "admin": "mgr", "api": "api"}
PLATFORM = ("#F2FBF7", "#087E78")
EXTERNAL = ("#FFF4D6", "#B8901A")
ENTRY_FRAME = ("#F0FAF6", "#0B8A6B")
MODULE_FRAME, MODULE_BOX = ("#FFF9F2", "#E0663A"), ("#D9E8FF", "#2F6FD6")
SERVICE_FRAME, SERVICE_BOX = ("#F3F5F7", "#5F7380"), ("#E6EBEE", "#5F7380")
STEP_RE = re.compile(r"^(.+?)\s*(-->|->)\s*(.+?)\s*:\s*(.*)$")
PASS_RE = re.compile(r"^(alt|else|end|opt|loop|group|note|== )")


# ---------- 描述檢查 ----------

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(d: dict) -> list[str]:
    errs: list[str] = []
    regions = d.get("regions") or []
    if not d.get("summary"):
        errs.append("缺少 summary（一段專案說明）")
    if not regions:
        errs.append("缺少 regions")
    prefixes, ids, names = set(), [], set()
    for r in regions:
        for k in ("name", "prefix"):
            if not r.get(k):
                errs.append(f"區域缺少 {k}：{r}")
        if r.get("prefix") in prefixes:
            errs.append(f"區域字首重複：{r.get('prefix')}")
        prefixes.add(r.get("prefix"))
        names.add(r.get("name"))
        is_api = r.get("prefix") == "API"
        for node in r.get("nodes", []):
            if not node.get("title"):
                errs.append(f"{r.get('name')} 有節點缺少 title")
            for p in node.get("pages", []):
                pid = p.get("id", "")
                if is_api:
                    ok = re.fullmatch(r"[A-Z]\d{2}", pid) is not None   # API 區可放其他區字首的頁面（API 開啟的頁面）
                else:
                    ok = re.fullmatch(rf"{re.escape(r.get('prefix', ''))}\d{{2}}", pid) is not None
                if not ok:
                    errs.append(f"頁面 ID「{pid}」不符合 {r.get('name')} 的字首 {r.get('prefix')}＋兩位數字")
                if not p.get("name") or not p.get("desc"):
                    errs.append(f"頁面 {pid} 缺少 name 或 desc")
                if re.search(r'[\\/:*?"<>|]', p.get("name", "")):
                    errs.append(f"頁面 {pid} 名稱含有不能當檔名的字元")
                ids.append(pid)
        for a in r.get("apis", []):
            if not re.fullmatch(r"API\d{2}", a.get("id", "")):
                errs.append(f"API ID「{a.get('id')}」須為 API＋兩位數字")
            if not a.get("name"):
                errs.append(f"{a.get('id')} 缺少 name")
            ids.append(a.get("id", ""))
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        errs.append("ID 重複：" + "、".join(dup))
    for role in d.get("roles", []):
        for rn in role.get("regions", []):
            if rn not in names:
                errs.append(f"角色「{role.get('name')}」的區域「{rn}」不在 regions")
    known = set(ids)
    for j in d.get("journeys", []):
        for pid in re.findall(r"\b[A-Z]+\d{2}\b", " ".join(map(str, j.get("steps", []) + j.get("exceptions", [])))):
            if pid not in known:
                errs.append(f"情境走查「{j.get('task')}」提到不存在的頁面 {pid}")
    for b in d.get("benchmark", []):
        for pid in b.get("pages", []):
            if pid not in known:
                errs.append(f"功能範圍比對「{b.get('feature')}」的 pages 有不存在的頁面 {pid}")
        if b.get("scope") not in ("第一版", "之後", "不做"):
            errs.append(f"功能範圍比對「{b.get('feature')}」的 scope 須為 第一版／之後／不做")
    for f in d.get("flows", []):
        if not re.fullmatch(r"[a-z0-9_]+", f.get("key", "")):
            errs.append(f"流程 key「{f.get('key')}」只能用小寫英文、數字與底線")
        for pid in re.findall(r"[A-Z]+\d+", f.get("order", "")):
            if pid not in known:
                errs.append(f"流程 {f.get('key')} 的 order 有不存在的頁面 {pid}")
        for s in f.get("steps", []):
            if not (STEP_RE.match(s) or PASS_RE.match(s)):
                errs.append(f"流程 {f.get('key')} 的步驟格式不對（應為「甲 -> 乙 : 說明」）：{s}")
    return errs


# ---------- 共用 ----------

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def replace_section(text: str, heading: str, body: str) -> str:
    """把 heading 那一行之後、到下一個同層或更高層標題之前的內容換成 body。"""
    lines = text.split("\n")
    level = len(heading) - len(heading.lstrip("#"))
    try:
        i = lines.index(heading)
    except ValueError:
        raise SystemExit(f"錯誤｜找不到標題「{heading}」；這個專案可能不是用範本建立的")
    j = i + 1
    while j < len(lines):
        m = re.match(r"^(#+) ", lines[j])
        if m and len(m.group(1)) <= level:
            break
        j += 1
    return "\n".join(lines[:i + 1] + [""] + body.strip("\n").split("\n") + [""] + lines[j:])


def ids_text(ids: list[str], per_line: int = 5) -> str:
    rows = [" ".join(ids[i:i + per_line]) for i in range(0, len(ids), per_line)]
    return "\\n".join(rows)


def shade(hex_color: str, light: float | None = None, sat: float | None = None) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = light if light is not None else l
    s = sat if sat is not None else s
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


class Draft:
    def __init__(self, d: dict):
        self.d = d
        self.regions = d["regions"]
        for i, r in enumerate(self.regions):
            if r["prefix"] == "API":
                r.setdefault("column", "api")
                r["backend"] = True
            r.setdefault("column", ["public", "org", "admin"][i] if i < 3 else f"r{i + 1}")
            r.setdefault("backend", r["column"] != "public")
        self.pages: list[dict] = []
        self.apis: list[dict] = []
        for r in self.regions:
            for node in r.get("nodes", []):
                for p in node.get("pages", []):
                    p["_region"], p["_node"] = r, node
                    self.pages.append(p)
            for a in r.get("apis", []):
                a["_region"] = r
                self.apis.append(a)
        self.page_by_id = {p["id"]: p for p in self.pages}
        self.region_of_prefix = {r["prefix"]: r for r in self.regions}
        self.flows = list(d.get("flows", []))
        flowed_apis = {a for f in self.flows for a in f.get("apis", [])}
        for a in self.apis:   # 每支 API 都要有流程圖（網站地圖 API 按鈕開啟）
            if a["id"] in flowed_apis or a.get("flow"):
                a.setdefault("flow", next((f["key"] for f in self.flows if a["id"] in f.get("apis", [])), a.get("flow")))
                continue
            key = f"api_{a['id'].lower()}"
            a["flow"] = key
            caller = a.get("caller") or "呼叫端系統"
            opened = a.get("pages", [])
            steps = [f"{caller} -> {a['name']} : 呼叫（網址、欄位與驗證方式待確認）",
                     f"{a['name']} -> {a.get('service', '平台服務')} : 檢核與處理"]
            for pid in opened:
                pname = self.page_by_id.get(pid, {}).get("name", pid)
                steps.append(f"{a['name']} -> {pname} {pid} : 開啟頁面")
            steps += [f"{a.get('service', '平台服務')} --> {a['name']} : 處理結果",
                      f"{a['name']} --> {caller} : 回傳結果（格式待確認）"]
            self.flows.append({"key": key, "title": f"{a['name']}流程", "summary": a.get("desc", f"{caller}呼叫 {a['name']}。"),
                               "order": ",".join(opened), "steps": steps, "apis": [a["id"]], "_auto": True})
        self.region_ext = {e["name"] for e in d.get("externals", [])}
        self.services = d.get("services", [])

    # ----- 區域與配色 -----
    def region_color(self, r: dict) -> tuple[str, str]:
        if r["column"] in REGION_COLORS:
            return REGION_COLORS[r["column"]]
        extras = [x for x in self.regions if x["column"] not in REGION_COLORS]
        return EXTRA_COLORS[extras.index(r) % len(EXTRA_COLORS)]

    def region_pages(self, r: dict) -> list[str]:
        out = [p["id"] for node in r.get("nodes", []) for p in node.get("pages", [])]
        return [a["id"] for a in r.get("apis", [])] + out

    def page_region(self, pid: str) -> dict | None:
        p = self.page_by_id.get(pid)
        if p:
            return self.region_of_prefix.get(re.match(r"[A-Z]+", pid).group(0), p["_region"])
        if pid.startswith("API"):
            return self.region_of_prefix.get("API")
        return None


# ---------- project.json ----------

def apply_project(dr: Draft) -> None:
    path = ROOT / "project.json"
    cfg = json.loads(read(path))
    old_mockup = cfg.get("mockup", {})
    cfg["regions"] = []
    for r in dr.regions:
        item = {"name": r["name"], "column": r["column"], "prefix": r["prefix"]}
        if r.get("backend"):
            item["backend"] = True
        cfg["regions"].append(item)
    cfg["ids"]["page_prefixes"] = [r["prefix"] for r in dr.regions if r["prefix"] != "API"]
    cols = [r["column"] for r in dr.regions]
    layout = [[c] for c in cols if c != "api"]
    if "api" in cols:
        if layout:
            layout[-1].append("api")
        else:
            layout.append(["api"])
    cfg["index"]["layout"] = layout
    theme = cfg.setdefault("theme", {})
    primary = (dr.d.get("brand") or {}).get("primary")
    if primary and re.fullmatch(r"#[0-9a-fA-F]{6}", primary):
        theme.update({"primary": primary.lower(), "primary_dark": shade(primary, light=0.28),
                      "primary_soft": shade(primary, light=0.93), "sidebar": shade(primary, light=0.16, sat=0.45)})
    theme["_說明"] = re.sub(r"〔待訪談第 1 階段[^〕]*〕", MARK.format(1), theme.get("_說明", ""))
    if MARK.format(1) not in theme["_說明"]:
        theme["_說明"] = MARK.format(1) + theme["_說明"]
    mockup = {k: v for k, v in old_mockup.items() if k.startswith("_")}
    name = cfg.get("name", "")
    for r in dr.regions:
        base = dict(old_mockup.get(r["column"], {}))
        mobile = r.get("device") == "mobile"
        if r["column"] == "api" or not r.get("backend"):
            base["layout"] = "mobile" if mobile else base.get("layout", "public")
            base.setdefault("brand", "logo")
            base.setdefault("footer", [f"© {name}", "隱私權政策　聯絡方式"])
            if r["column"] != "api":
                base["nav_items"] = [n["title"] for n in r.get("nodes", [])][:5]
                base.setdefault("buttons", ["登入"])
        else:
            base["layout"] = "mobile" if mobile else base.get("layout", "backend")
            base["nav"] = r.get("nav") or {"org": "member", "admin": "admin"}.get(r["column"], r["column"])
            base["label"] = base.get("label") or r["name"]
            base["badge"] = r["name"]
            base.setdefault("sublabel", "")
            base.setdefault("account", "")
            role_names = [ro["name"] for ro in dr.d.get("roles", []) if r["name"] in ro.get("regions", [])]
            if not any(base.get("identity", ["", "", ""])[1:]):
                base["identity"] = ["目前身分", role_names[0] if role_names else r["name"], r.get("desc", "")[:16]]
            if not base.get("account"):
                base["account"] = (role_names[0] + "　您好") if role_names else ""
            base.setdefault("footer", [f"© {name}", "支援中心"])
        mockup[r["column"]] = base
    cfg["mockup"] = mockup
    if dr.d.get("short_name"):   # 示意圖頁首與側欄用的短品牌名（專案名稱太長會被截斷）
        cfg.setdefault("brand", {})["name"] = dr.d["short_name"]
    write(path, json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")


# ---------- 網站地圖.md ----------

def apply_sitemap(dr: Draft) -> None:
    path = ROOT / "網站地圖.md"
    text = read(path)
    rows = ["| 區域 | 對象／用途 | 示意圖數 |", "|---|---|---:|"]
    for r in dr.regions:
        n_pages = sum(len(node.get("pages", [])) for node in r.get("nodes", []))
        count = (f"{len(r.get('apis', []))} API＋{n_pages} 頁" if r.get("apis") else str(n_pages))
        rows.append(f"| {r['name']} | {r.get('desc', '')} | {count} |")
    text = replace_section(text, "## 全站區域", MARK.format(4) + "\n\n" + "\n".join(rows))
    out = ["節點與按鈕寫法見 `規範/workflow.md`「網站地圖寫法」。", "", MARK.format(5), ""]
    for r in dr.regions:
        out += [f"### {r['name']}", "", f"_{r.get('desc', '')}_", ""]
        for a in r.get("apis", []):
            out += [f"#### {a['name']}", "", a.get("desc", ""), "",
                    f"- 按鈕（{a['id']}）：`{a['name']}`（點擊後以燈箱顯示流程圖、傳送欄位、回傳欄位與加解密方式）",
                    f"  - 說明：{a.get('desc', '')} 欄位與介接方式待確認。",
                    f"- 流程圖：`flows/{a['flow']}.svg`",
                    f"- 細節：[畫面與流程文字規格]({SPEC_NAME}#api-{a['id'].lower()})", ""]
        for node in r.get("nodes", []):
            out += [f"#### {node['title']}", "", node.get("desc") or node["title"], "", "頁面／按鈕："]
            for p in node.get("pages", []):
                out.append(f"- [{p['id']}]({SPEC_NAME}#{p['id'].lower()}) {p['name']}")
                out.append(f"  - 說明：{p['desc']}")
                if p.get("similar"):
                    out.append("  - 類似：" + "、".join(p["similar"]))
                if p.get("manage"):
                    out.append("  - 管理：" + "、".join(p["manage"]))
            out.append("")
    text = replace_section(text, "## 網站地圖節點", "\n".join(out))
    menus = ["側欄與頂部導覽的基準；表格標題寫 `（nav: key）`，改完執行 `python3 scripts/nav.py`。", "", MARK.format(5), ""]
    has_menu = False
    for r in dr.regions:
        if not r.get("backend") or r["column"] == "api":
            continue
        standalone = {p["id"] for n in r.get("nodes", []) for p in n.get("pages", []) if p.get("kind") == "login" or p.get("bare")}
        pages = [x for x in dr.region_pages(r) if x not in standalone]   # 登入等獨立頁不畫選單
        if not pages:
            continue
        has_menu = True
        key = r.get("nav") or {"org": "member", "admin": "admin"}.get(r["column"], r["column"])
        style, kind = ("tabbar", "頁籤列") if r.get("device") == "mobile" else ("sidebar", "側欄")
        menus += [f"### {r['name']}{kind}（nav: {key}）", "", f"- 樣式：{style}", f"- 套用頁面：{' '.join(pages)}", "",
                  "| 順序 | 選單項目 | 反白頁面 |", "|---:|---|---|"]
        for i, node in enumerate(r.get("nodes", []), 1):
            menus.append(f"| {i} | {node.get('menu') or node['title']} | {' '.join(p['id'] for p in node.get('pages', []) if p['id'] not in standalone)} |")
        menus.append("")
    if not has_menu:
        menus.append("無（沒有後台區域）。")
    text = replace_section(text, "## 共用選單", "\n".join(menus))
    text = text.rstrip("\n") + f"\n- {TODAY}：AI 依起稿描述產生區域、節點、頁面按鈕與共用選單初稿（待審閱）。\n"
    write(path, text)


# ---------- 專案規則.md ----------

def apply_rules(dr: Draft) -> None:
    path = ROOT / "專案規則.md"
    text = read(path)
    d = dr.d
    text = replace_section(text, "## 回答語言", MARK.format(1) + "\n\n" + (d.get("language") or "一律使用繁體中文（台灣用語）。"))
    area = [MARK.format(4), ""]
    for r in dr.regions:
        ids = dr.region_pages(r)
        span = f"{ids[0]}–{ids[-1]}" if len(ids) > 1 else (ids[0] if ids else "尚無頁面")
        area.append(f"- {r['name']}（字首 {r['prefix']}，{span}）：{r.get('desc', '')}")
    text = replace_section(text, "## 區域歸屬", "\n".join(area))
    biz = [MARK.format(3), ""]
    for q, a in d.get("answers", []):
        biz.append(f"- 起稿問答｜{q}：{a}")
    for rule in d.get("rules", []):
        biz.append(f"- {rule}")
    if not d.get("rules"):
        biz.append("- 業務規則：起稿時未提供，審閱時補上。")
    biz.append("- 用語限制：起稿時未設定（`project.json › term_rules` 為空）。")
    text = replace_section(text, "## 業務規則與用語限制", "\n".join(biz))
    primary = (d.get("brand") or {}).get("primary")
    brand = [MARK.format(1), "",
             f"- 品牌名稱：沿用專案名稱；正式標誌待提供（放 `assets/`，寫進 `project.json › brand`）。",
             f"- 主色：{primary}（起稿推測，已寫入 `project.json › theme`）。" if primary else "- 主色：沿用範本預設，待提供。",
             "- 新頁面 SVG 以 `scripts/mockup.py` 產生，配色自動套用。"]
    text = replace_section(text, "## 品牌與素材", "\n".join(brand))
    text = replace_section(text, "## 配色對照", MARK.format(8) + "\n\n架構圖入口區域、使用者與外部系統的顏色見規格「系統架構 › 圖例」；"
                           "流程圖參與者顏色見規格「流程圖參與者類別」表。")
    write(path, text)


def apply_hero(dr: Draft) -> None:
    """index.html 首頁副標（內容區 hero）：把範本的「一句話說明」標記換成起稿描述的 tagline 或說明第一句。"""
    path = ROOT / "index.html"
    tagline = dr.d.get("tagline") or re.split(r"[，。,；]", dr.d["summary"])[0]
    write(path, read(path).replace("〔待訪談第 1 階段：一句話說明〕", tagline[:40]))


def apply_summary_card(dr: Draft) -> None:
    """index.html 內容區 cards：放一張「專案摘要」折疊卡（主題、起稿問答、規模與數量、待確認數）。"""
    import html as _h
    d = dr.d
    path = ROOT / "index.html"
    text = read(path)
    answers = "".join(f"<li><b>{_h.escape(q)}</b>：{_h.escape(a)}</li>" for q, a in d.get("answers", []))
    counts = (f"{len(dr.regions)} 個區域、{len(dr.pages)} 頁、{len(dr.apis)} 支 API、"
              f"{len([f for f in dr.flows if not f.get('_auto')])} 條流程、{len(module_list(dr))} 個業務模組；"
              f"尚待確認 {len(d.get('pending', []))} 項")
    card = (f'\n<details class="mapfold extfold" id="project-summary"><summary><span class="fold-num" aria-hidden="true">0</span>'
            f'專案摘要｜AI 起稿・待審閱</summary><div class="ext-body">'
            f'<p class="arch-intro"><span class="ext-badge">AI 起稿・待審閱</span> {_h.escape(d["summary"])}</p>'
            f'<p class="arch-intro">規模：{_h.escape(str(d.get("scale", "未指定")))}；{counts}。</p>'
            + (f'<ul class="arch-intro">{answers}</ul>' if answers else "")
            + '</div></details>\n')
    new = re.sub(r"(<!-- \[slot:cards\] -->)(.*?)(<!-- \[/slot:cards\] -->)",
                 lambda m: m.group(1) + card + m.group(3), text, count=1, flags=re.S)
    write(path, new)


# ---------- 架構圖 ----------

PUML_HEAD = """skinparam defaultFontName "PingFang TC"
skinparam defaultFontColor #203F3C
skinparam backgroundColor #FFFFFF
skinparam shadowing false
skinparam TitleFontSize 20
skinparam TitleFontColor #087E78
skinparam rectangle {
  RoundCorner 12
  BorderThickness 2
  FontSize 13
}
skinparam packageStyle rectangle
"""


def apply_architecture(dr: Draft, name: str) -> list[list[str]]:
    """寫 architecture/ 兩張圖，回傳規格圖例列。"""
    legend: list[list[str]] = []
    roles = dr.d.get("roles", [])
    ext = dr.d.get("externals", [])
    # 系統情境圖
    lines = ["' @title 系統情境圖", f"' @summary {name}與使用者、外部系統的邊界與交換資料（AI 起稿）。", "@startuml",
             f"title 系統情境圖｜{name}", "left to right direction", PUML_HEAD]
    for i, role in enumerate(roles, 1):
        lines.append(f'actor "{role["name"]}" as U{i}')
    lines.append(f'package "{name}（平台邊界）" as P {PLATFORM[0]};line:{PLATFORM[1][1:]} {{')
    for i, r in enumerate(dr.regions, 1):
        fill, line = dr.region_color(r)
        lines.append(f'  rectangle "{r["name"]}" as E{i} {fill};line:{line[1:]}')
        legend.append(["系統情境圖", fill, line, r["name"]])
    lines.append("}")
    legend.append(["系統情境圖", PLATFORM[0], PLATFORM[1], "平台邊界"])
    for i, e in enumerate(ext, 1):
        lines.append(f'rectangle "{e["name"]}" as X{i} {EXTERNAL[0]};line:{EXTERNAL[1][1:]}')
    if ext:
        legend.append(["系統情境圖", EXTERNAL[0], EXTERNAL[1], "外部系統"])
    for i, role in enumerate(roles, 1):
        for rn in role.get("regions", []):
            idx = next(k for k, r in enumerate(dr.regions, 1) if r["name"] == rn)
            lines.append(f"U{i} --> E{idx}")
    for i, e in enumerate(ext, 1):
        label = e.get("data", "")
        lines.append(f'P --> X{i}' + (f' : {label}' if label else ""))
    lines.append("@enduml")
    write(ROOT / "architecture" / "system_context.puml", "\n".join(lines) + "\n")
    # 功能架構圖
    lines = ["' @title 功能架構圖", "' @summary 入口層（網站地圖各區）→ 業務模組（標示涵蓋頁面）→ 共用服務（AI 起稿）。", "@startuml",
             f"title 功能架構圖｜{name}", PUML_HEAD,
             f'package "入口層（網站地圖各區）" as L1 {ENTRY_FRAME[0]};line:{ENTRY_FRAME[1][1:]} {{']
    legend.append(["功能架構圖", ENTRY_FRAME[0], ENTRY_FRAME[1], "入口層外框"])
    for i, r in enumerate(dr.regions, 1):
        fill, line = dr.region_color(r)
        ids = dr.region_pages(r)
        lines.append(f'  rectangle "{r["name"]}\\n{ids_text(ids) or "（尚無頁面）"}" as E{i} {fill};line:{line[1:]}')
        legend.append(["功能架構圖", fill, line, f"入口層：{r['name']}"])
    lines += [f"  E{i} -[hidden]right- E{i + 1}" for i in range(1, len(dr.regions))] + ["}"]
    modules = module_list(dr)
    if modules:
        lines.append(f'package "業務模組" as L2 {MODULE_FRAME[0]};line:{MODULE_FRAME[1][1:]} {{')
        for i, (mname, ids) in enumerate(modules, 1):
            lines.append(f'  rectangle "{mname}\\n{ids_text(ids)}" as M{i} {MODULE_BOX[0]};line:{MODULE_BOX[1][1:]}')
        lines += [f"  M{i} -[hidden]right- M{i + 1}" for i in range(1, len(modules)) if i % 5]   # 每排 5 個
        lines += [f"  M{i - 5} -[hidden]down- M{i}" for i in range(6, len(modules) + 1, 5)] + ["}"]
        legend += [["功能架構圖", MODULE_FRAME[0], MODULE_FRAME[1], "業務模組外框"],
                   ["功能架構圖", MODULE_BOX[0], MODULE_BOX[1], "業務模組"]]
    if dr.services:
        lines.append(f'package "共用服務" as L3 {SERVICE_FRAME[0]};line:{SERVICE_FRAME[1][1:]} {{')
        for i, s in enumerate(dr.services, 1):
            lines.append(f'  rectangle "{s["name"]}" as S{i} {SERVICE_BOX[0]};line:{SERVICE_BOX[1][1:]}')
        lines += [f"  S{i} -[hidden]right- S{i + 1}" for i in range(1, len(dr.services))] + ["}"]
        legend += [["功能架構圖", SERVICE_FRAME[0], SERVICE_FRAME[1], "共用服務外框"],
                   ["功能架構圖", SERVICE_BOX[0], SERVICE_BOX[1], "共用服務"]]
    lines += ["L1 -[hidden]down- L2" if modules else "", "L2 -[hidden]down- L3" if modules and dr.services else "", "@enduml"]
    write(ROOT / "architecture" / "functional_architecture.puml", "\n".join(x for x in lines if x is not None) + "\n")
    return legend


def module_list(dr: Draft) -> list[tuple[str, list[str]]]:
    order = [m["name"] for m in dr.d.get("modules", [])]
    found: dict[str, list[str]] = {}
    for item in [*dr.apis, *dr.pages]:
        m = item.get("module")
        if m:
            found.setdefault(m, []).append(item["id"])
    names = [n for n in order if n in found] + [n for n in found if n not in order]
    return [(n, sorted(found[n], key=id_key)) for n in names]


def id_key(pid: str) -> tuple:
    m = re.match(r"([A-Z]+)(\d+)", pid)
    return (m.group(1), int(m.group(2))) if m else (pid, 0)


# ---------- 流程 ----------

def flow_participants(dr: Draft, f: dict) -> list[tuple[str, str]]:
    names: list[str] = []
    for s in f.get("steps", []):
        m = STEP_RE.match(s)
        if m:
            for n in (m.group(1).strip(), m.group(3).strip()):
                if n not in names:
                    names.append(n)
    roles = {r["name"] for r in dr.d.get("roles", [])}
    out = []
    for n in names:
        kind = "actor" if n in roles else ("database" if ("資料庫" in n or n.endswith("DB")) else "participant")
        out.append((kind, n))
    return out


def participant_cat(dr: Draft, kind: str, name: str) -> str:
    if kind == "database":
        return "data"
    roles = {r["name"]: r for r in dr.d.get("roles", [])}
    if name in roles:
        regs = [r for r in dr.regions if r["name"] in roles[name].get("regions", [])]
        cats = {COLUMN_CAT.get(r["column"], "cross") for r in regs}
        return cats.pop() if len(cats) == 1 else "cross"
    m = re.search(r"\b(API\d{2}|[A-Z]\d{2})\b", name)
    if m:
        r = dr.page_region(m.group(1))
        if r:
            return COLUMN_CAT.get(r["column"], "cross")
    if name in {a["name"] for a in dr.apis}:
        return "api"
    if name in dr.region_ext:
        return "external"
    return "service"


def apply_flows(dr: Draft) -> dict[str, list[str]]:
    """寫 flows/*.puml，回傳 {類別: [參與者]}。"""
    cats: dict[str, list[str]] = {}
    for f in dr.flows:
        parts = flow_participants(dr, f)
        alias = {}
        decl = []
        for i, (kind, n) in enumerate(parts, 1):
            alias[n] = f"P{i}"
            decl.append(f'{kind} "{n}" as P{i}')
            cat = participant_cat(dr, kind, n)
            if cat != "data" and n not in cats.setdefault(cat, []):
                cats[cat].append(n)
        order = f.get("order", "")
        pages = re.findall(r"[A-Z]+\d+", order)
        head = [f"' @title {f['title']}", f"' @pages {','.join(pages)}"]
        if len(pages) > 1:
            head.append(f"' @order {order}")
        head.append(f"' @summary {f.get('summary', '')}")
        body = []
        for s in f.get("steps", []):
            m = STEP_RE.match(s)
            if m:
                body.append(f"{alias[m.group(1).strip()]} {m.group(2)} {alias[m.group(3).strip()]} : {m.group(4)}")
            else:
                line = s
                if re.match(r"^\s*note\b", s):   # note right of 參與者 : … ／ note over 甲, 乙 : …
                    head_part, sep, tail = s.partition(":")
                    for n in sorted(alias, key=len, reverse=True):
                        head_part = head_part.replace(n, alias[n])
                    line = head_part + sep + tail
                body.append(line)
        write(ROOT / "flows" / f"{f['key']}.puml", "\n".join(head + ["@startuml", *decl, "", *body, "@enduml"]) + "\n")
    return cats


# ---------- 規格 ----------

COMMON_RULES = """{mark}

#### 共用欄位規則

| 編號 | 欄位 | 規則 | 錯誤 |
|---|---|---|---|
| CF-01 | 姓名 | 去除前後空白後 1–50 字（預設規則） | CE-01 |
| CF-02 | 電子信箱 | Email 格式；上限 254 字（預設規則） | CE-01、CE-02 |
| CF-03 | 手機號碼 | 09 開頭 10 碼；可輸入「-」與空格，存檔時去除（預設規則） | CE-01、CE-03 |
| CF-04 | 日期 | YYYY-MM-DD；區間查詢的起日不得晚於迄日（預設規則） | CE-04 |

#### 共用表單行為

| 編號 | 行為 | 規則 |
|---|---|---|
| CB-01 | 防止重複送出 | 送出後按鈕鎖定並顯示處理中，完成或失敗後恢復（預設規則） |
| CB-02 | 離開未儲存 | 有未儲存的修改時，離開頁面前提醒（預設規則） |
| CB-03 | 列表 | 預設每頁 20 筆，依更新時間新到舊排列（預設規則） |

#### 共用錯誤文案

| 編號 | 情境 | 文案 |
|---|---|---|
| CE-01 | 必填未填 | 此欄位為必填（預設規則） |
| CE-02 | Email 格式錯誤 | 請輸入正確的電子信箱（預設規則） |
| CE-03 | 手機格式錯誤 | 請輸入 09 開頭的 10 碼手機號碼（預設規則） |
| CE-04 | 日期區間錯誤 | 起日不得晚於迄日（預設規則） |
| CE-05 | 系統錯誤 | 系統忙碌中，請稍後再試（預設規則） |

#### 共用驗收條件

| 編號 | 驗收條件 |
|---|---|
| CAC-01 | 必填與格式錯誤依 CF、CE 顯示，未通過時不送出（預設規則） |
| CAC-02 | 送出成功顯示成功訊息，失敗顯示 CE-05 且保留已填內容（預設規則） |

#### 非功能需求

- 瀏覽器、無障礙、安全、個資保護、效能：待確認。
"""


def api_section(a: dict) -> str:
    caller = a.get("caller") or "待確認"
    return f"""<a id="api-{a['id'].lower()}"></a>
### {a['id']}｜{a['name']}

- 目標：{a.get('desc', '')}
- 流程：見流程圖；呼叫方式、欄位與驗證方式待確認。
- 流程圖：`flows/{a['flow']}.svg`；PlantUML：`flows/{a['flow']}.puml`
- 規格狀態：AI 起稿；欄位、驗證、加解密與錯誤碼待確認。
- 開發說明（AI 補充）：
  - 【API 目的】{a.get('desc', '')}
  - 【待確認】網址、傳送與回傳欄位、驗證與加密方式、錯誤碼。
- 開發說明（設計者補充）：

**API 規格（待確認）**

> AI 起稿：各小節待補，不自行補成規格。

#### 介接資訊

| 項目 | 內容 |
|---|---|
| 呼叫方 | {caller} |
| 接收方 | 本平台 |
| 網址 | 待確認 |
| 方法與編碼 | 待確認 |
| 回傳方式 | 待確認 |

#### 傳送欄位

| 欄位 | 英文欄位名稱 | 必填 | 型態 | 欄位大小 | 說明 |
|---|---|---|---|---|---|
| 待確認 | 待確認 | 待確認 | 待確認 | 待確認 | 待確認 |

#### 回傳欄位

| 欄位 | 英文欄位名稱 | 型態 | 欄位大小 | 說明 |
|---|---|---|---|---|
| 待確認 | 待確認 | 待確認 | 待確認 | 待確認 |

#### 加解密方式

- 待確認。
"""


def apply_spec(dr: Draft, legend: list[list[str]], cats: dict[str, list[str]]) -> None:
    import page_stub   # 頁面段落骨架與 page_stub.py 相同
    path = ROOT / SPEC_NAME
    text = read(path)
    d = dr.d
    flows_of: dict[str, list[dict]] = {}
    for f in dr.flows:
        for pid in re.findall(r"[A-Z]+\d+", f.get("order", "")):
            flows_of.setdefault(pid, []).append(f)
    scope = [f"- 專案說明：{d['summary']} {MARK.format(1)}",
             f"- 畫面示意圖：{len(dr.pages)} 頁。", f"- API：{len(dr.apis)} 支。", f"- 跨頁流程圖：{len(dr.flows)} 條。",
             "- 系統架構圖：2 張（系統情境圖、功能架構圖），見「系統架構」章；PlantUML 原稿放 `architecture/`。"]
    if d.get("benchmark"):
        scope += ["", "#### 功能範圍比對", "", MARK.format(5) + " AI 依同類成熟產品常見功能列出，逐項標示第一版是否納入。", "",
                  "| 功能 | 範圍 | 對應頁面 | 說明 |", "|---|---|---|---|"]
        scope += [f"| {b['feature']} | {b['scope']} | {'、'.join(b.get('pages', [])) or '—'} | {b.get('note', '')} |"
                  for b in d["benchmark"]]
    if d.get("journeys"):
        scope += ["", "#### 使用情境走查", "", MARK.format(5) + " 每個角色的主要任務，從進入網站寫到完成；頁面清單與流程依此補齊。", ""]
        for j in d["journeys"]:
            scope.append(f"- **{j.get('role', '')}｜{j.get('task', '')}**")
            scope += [f"  {i}. {st}" for i, st in enumerate(j.get("steps", []), 1)]
            if j.get("exceptions"):
                scope.append("  - 例外：" + "；".join(j["exceptions"]))
    text = replace_section(text, "## 規格範圍", "\n".join(scope))
    text = replace_section(text, "#### 讀圖說明", "\n".join([
        "| 圖 | 讀圖說明 |", "|---|---|",
        f"| 系統情境圖 | 中間的方框是本平台，裡面是對外入口（網站地圖各區）；左邊是使用者，右邊是外部系統。{MARK.format(8)} |",
        f"| 功能架構圖 | 由上往下分三層：入口層是網站地圖各區，中間是業務模組（每塊下方是涵蓋的頁面），下方是共用服務。{MARK.format(6)} |"]))
    text = replace_section(text, "#### 圖例", "\n".join(["| 圖 | 底色 | 框線 | 意義 |", "|---|---|---|---|"]
                                                        + [f"| {a} | {b} | {c} | {m} |" for a, b, c, m in legend]))
    users = [MARK.format(2), "", "| 使用者 | 使用區域 | 說明 |", "|---|---|---|"]
    for role in d.get("roles", []):
        users.append(f"| {role['name']} | {'、'.join(role.get('regions', []))} | {role.get('desc', '')} |")
    text = replace_section(text, "#### 使用者", "\n".join(users))
    ext = ["- 首頁「外部系統串接」區塊直接讀取本表，依需求類別分組顯示，不另外維護。", "", MARK.format(8), ""]
    if d.get("externals"):
        ext += ["| 外部系統 | 需求類別 | 交換資料 | 依據 | 狀態 |", "|---|---|---|---|---|"]
        for e in d["externals"]:
            ext.append(f"| {e['name']} | {e.get('category', '系統需求')} | {e.get('data', '')} | {e.get('basis', '')} | "
                       f"{e.get('status') or '待確認'} |")
    else:
        ext.append("無。")
    text = replace_section(text, "#### 外部系統", "\n".join(ext))
    modules = module_list(dr)
    covered = {pid for _, ids in modules for pid in ids}
    loose = [x["id"] for x in [*dr.apis, *dr.pages] if x["id"] not in covered]
    mod = [MARK.format(6), "", "| 模組 | 涵蓋頁面 |", "|---|---|"] + [f"| {n} | {'、'.join(ids)} |" for n, ids in modules]
    if loose:
        mod += ["", f"- 暫不歸入模組：{'、'.join(loose)}（起稿時未歸類）"]
    text = replace_section(text, "#### 業務模組", "\n".join(mod))
    svc = [MARK.format(6), ""]
    if dr.services:
        svc += ["| 共用服務 | 用途 | 連到的外部系統 |", "|---|---|---|"]
        svc += [f"| {s['name']} | {s.get('use', '')} | {s.get('external') or '—'} |" for s in dr.services]
    else:
        svc.append("無。")
    text = replace_section(text, "#### 共用服務", "\n".join(svc))
    # 流程圖參與者類別：保留說明，重建表格
    labels = {"front": "前台", "member": "會員中心", "mgr": "後台", "cross": "跨區", "api": "API", "service": "平台服務",
              "external": "外部系統", "data": "資料"}
    for r in dr.regions:
        if r["column"] in COLUMN_CAT:
            labels[COLUMN_CAT[r["column"]]] = r["name"]
    table = ["流程圖（flows 目錄的 PUML）參與者依下表上色，由 `flow_sync.py` 自動加上類別與樣式，不手動寫顏色；新增參與者時先加進本表。`database` 一律歸「資料」。",
             "", "| 類別 | 代號 | 底色 | 框線 | 參與者 |", "|---|---|---|---|---|"]
    for code, fill, line in FLOW_CATS:
        who = "（所有 database）" if code == "data" else "、".join(cats.get(code, []))
        table.append(f"| {labels[code]} | {code} | {fill} | {line} | {who} |")
    text = replace_section(text, "#### 流程圖參與者類別", "\n".join(table))
    rules_body = ('<a id="common-rules"></a>\n\n> 各頁「SA 規格」只寫本頁特有內容，以下規則各頁共用，引用時寫編號（如 CF-01）。'
                  "標「（預設規則）」者確認一次即全站適用。\n\n" + COMMON_RULES.format(mark=MARK.format(10)))
    text = replace_section(text, "## 全站共用規則（試做）", rules_body)
    api = ["> 一支 API 對應一個網址。每支 API 以 `### API01｜名稱` 開段，寫法見 `規範/spec-writing.md`「API 規格」。", "",
           MARK.format(9), ""]
    api += [api_section(a) for a in dr.apis] if dr.apis else ["本專案沒有對外 API。"]
    text = replace_section(text, "## API 介接", "\n".join(api))
    pages = ["> 每頁以 `<a id=\"a01\"></a>`、`### A01｜頁面名稱` 開段，含區域、目前說明、SVG 畫面原稿、對應流程、開發說明與 SA 規格；寫法見 `規範/spec-writing.md`。", ""]
    for p in sorted(dr.pages, key=lambda x: id_key(x["id"])):
        region = dr.page_region(p["id"]) or p["_region"]
        block = page_stub.stub(p["id"], p["name"], p["desc"], f"{region['name']}／{p['_node']['title']}")
        fl = flows_of.get(p["id"], [])
        if fl:
            at = next(i for i, ln in enumerate(block) if ln.startswith("- SVG 畫面原稿："))
            block.insert(at + 1, "- 對應流程：" + "、".join(f"[{f['title']}](#flow-{f['key']})" for f in fl))
        # 開發說明（AI 補充）：除了頁面目的，再列描述裡已有的欄位、操作與待確認
        dev_at = block.index("- 開發說明（設計者補充）：")
        def _label(x):
            return (x[0] if isinstance(x, (list, tuple)) else x.get("label", "") if isinstance(x, dict) else str(x)).rstrip("*").strip()
        extra = []
        cols = [_label(x) for x in (p.get("fields") or [])] or list(p.get("columns") or [])
        if cols:
            extra.append(f"  - 【主要欄位】{'、'.join(cols[:10])}（示意，正式欄位見 SA 規格）")
        ops = [_label(x) for x in (p.get("buttons") or [])] + list(p.get("row_actions") or []) + list(p.get("table_actions") or [])
        if ops:
            extra.append(f"  - 【操作】{'、'.join(dict.fromkeys(o for o in ops if o))}")
        if p.get("pending"):
            extra.append(f"  - 【待確認】{'；'.join(p['pending'])}")
        block[dev_at:dev_at] = extra
        # 初版 SA 維持（待補）骨架，只在「摘要｜本頁待確認」列出待確認事項（逐頁細節留到第 11 階段）
        at = block.index("#### 摘要｜本頁待確認") + 1
        pend = list(p.get("pending", [])) + ["欄位、規則與導向是否符合實際作業"]
        block[at:at] = ["", "| 編號 | 問題 | 影響 |", "|---|---|---|",
                        *[f"| Q{i:02d} | {q} | {p['id']} |" for i, q in enumerate(pend, 1)], ""]
        pages += block
    text = replace_section(text, "## 頁面", "\n".join(pages))
    flows = ["> 每條流程以 `<a id=\"flow-<key>\"></a>`、`### 流程名稱` 開段，列頁面、流程摘要、SVG 與 PlantUML 路徑；原稿放 `flows/<key>.puml`。", "",
             MARK.format(7), ""]
    for f in dr.flows:
        pages_ = re.findall(r"[A-Z]+\d+", f.get("order", ""))
        flows += [f'<a id="flow-{f["key"]}"></a>', f"### {f['title']}", "", f"- 頁面：{', '.join(pages_)}",
                  f"- 流程摘要：{f.get('summary', '')}", f"- SVG：`flows/{f['key']}.svg`；PlantUML：`flows/{f['key']}.puml`", ""]
    text = replace_section(text, "## 跨頁流程", "\n".join(flows))
    order_rows = [f"| {f['title']}（{f['key']}） | {f.get('order', '').replace(',', ' → ')} | {f.get('summary', '')} |"
                  for f in dr.flows if len(re.findall(r"[A-Z]+\d+", f.get("order", ""))) > 1]
    intro = ("流程原稿（`flows/*.puml`）以 `@order` 標示頁面先後，供流程圖頁面圖例與燈箱「流程位置」使用。"
             "寫法：逗號分隔先後，`|` 表示並列頁面，例如 `C01,A01|A02`。")
    text = replace_section(text, "## 流程頁面順序", intro + ("\n\n| 流程 | 建議順序 | 說明 |\n|---|---|---|\n" + "\n".join(order_rows)
                                                              if order_rows else ""))
    pend = ["訪談中答不出來的事項以條列寫在這裡。", ""] + [f"- {x}" for x in d.get("pending", [])]
    text = replace_section(text, "## 尚待確認的產品／介接事項", "\n".join(pend))
    text = text.rstrip("\n") + (f"\n- {TODAY}：AI 依起稿描述產生初稿（{len(dr.pages)} 頁、{len(dr.apis)} 支 API、{len(dr.flows)} 條流程），"
                                "標「AI 起稿」者待審閱。\n")
    write(path, text)


# ---------- 第 12 階段：舊系統移轉、相關法規 ----------

def apply_optional(dr: Draft) -> None:
    """選填兩章與 index.html 對應區塊：依起稿描述寫第一輪內容；法規只列領域名稱並標待確認，不寫條文。"""
    spec_path = ROOT / SPEC_NAME
    text = read(spec_path)
    mig = dr.d.get("migration") or {}
    if mig.get("system"):
        mig_lines = [f"- 舊系統：{mig['system']}", f"- 移轉範圍：{mig.get('scope') or '待確認'}",
                     "- 資料對照、切換方式、並行期間與時程：待確認。"]
        mig_html = f"舊系統：{mig['system']}；移轉範圍：{mig.get('scope') or '待確認'}；資料對照、切換方式與時程待確認。"
    else:
        mig_lines = ["- 起稿問答：沒有需要移轉的舊系統。"]
        mig_html = "起稿問答：沒有需要移轉的舊系統。"
    areas = dr.d.get("regulations") or []
    law_lines = (["- 可能涉及的法規領域（AI 依產業常識列出，名稱與適用範圍待確認，不寫條文）："] + [f"  - {a}" for a in areas]
                 if areas else ["- 起稿時未列出，待設計者補充。"])
    law_html = ("可能涉及的法規領域（待確認）：" + "、".join(areas) + "。") if areas else "起稿時未列出，待設計者補充。"
    for key, title, lines in (("migration-plan", "## 舊系統移轉計畫（選填）", mig_lines),
                              ("regulations", "## 相關法規（選填）", law_lines)):
        body = [f'<a id="{key}"></a>', "", "- 狀態：AI 起稿，待審閱。" + MARK.format(12),
                "- 首頁對應：`index.html` 同名折疊區塊。", *lines]
        text = replace_section(text, title, "\n".join(body))
    write(spec_path, text)
    idx = ROOT / "index.html"
    html = read(idx)
    for slot, msg in (("migration", mig_html), ("regulations", law_html)):
        html = re.sub(rf"(<!-- \[slot:{slot}\] -->).*?(<!-- \[/slot:{slot}\] -->)",
                      lambda m: f'{m.group(1)}<p class="arch-intro"><span class="ext-badge">AI 起稿・待審閱</span> {msg}'
                                f'文字版見規格同名章節。</p>{m.group(2)}', html, flags=re.S)
    write(idx, html)
    rules = ROOT / "專案規則.md"
    s = read(rules)
    s = re.sub(r"〔待訪談第 12 階段[^〕]*〕", MARK.format(12) + "已依起稿描述寫入第一輪內容，見規格兩章。", s)
    write(rules, s)


# ---------- 示意圖 ----------

NAMES = ["王小明", "陳怡君", "林志豪", "張雅婷", "李建宏", "黃美玲"]
STATUS_CYCLE = ["啟用", "待審核", "已完成", "停用", "處理中"]


def sample_value(col: str, i: int, p: dict) -> str:
    """依欄位名稱產生像真的示意資料（AI 沒提供 sample 時使用）。"""
    n = i + 1
    if re.search(r"狀態|結果|進度", col):
        ctx = p.get("name", "")
        cycle = (["待審核", "已核准", "審核中", "退回"] if re.search(r"審核|申請|申辦", ctx) else
                 ["已付款", "待付款", "已付款", "失敗"] if re.search(r"交易|繳費|付款|帳單|訂單|發票", ctx) else
                 ["正常", "異常", "正常", "離線"] if re.search(r"設備|異常|監控|辨識", ctx) else STATUS_CYCLE)
        return cycle[i % len(cycle)]
    if re.search(r"編號|單號|代碼|ID|號碼", col):
        return f"{p['id'][0]}-2611{n:03d}"
    if re.search(r"日期|時間|申請日|到期|建立", col):
        return f"2026-11-{20 - i:02d}" + (f" {9 + i:02d}:{(n * 13) % 60:02d}" if "時間" in col else "")
    if re.search(r"姓名|申請人|聯絡人|操作者|負責人|車主|會員", col):
        return NAMES[i % len(NAMES)]
    if re.search(r"Email|信箱", col, re.I):
        return f"user{n}@example.com"
    if re.search(r"電話|手機", col):
        return f"0912-345-{100 + n * 37:03d}"
    if re.search(r"金額|費用|營收|銷售|合計", col):
        return f"{(n * 1350) % 9000 + 500:,}"
    if re.search(r"數量|張數|筆數|次數|剩餘|已用|在場|車位", col):
        return str((n * 37) % 180 + 12)
    if re.search(r"角色|權限", col):
        return ["管理者", "營運人員", "客服人員"][i % 3]
    if re.search(r"費率|價格|單價|方案費用", col):
        return "待確認"   # 費率不推測
    if re.search(r"地址", col):
        return ["台北市信義區松仁路 100 號", "新北市板橋區文化路一段 25 號", "台中市西屯區台灣大道三段 99 號",
                "高雄市前鎮區中華五路 789 號", "桃園市中壢區中正路 210 號"][i % 5]
    if re.search(r"車牌", col):
        return ["ABC-1234", "BDE-5678", "KLM-2468", "RTY-1357", "NPQ-8642"][i % 5]
    if re.search(r"營業時間|時段", col):
        return ["00:00–24:00", "07:00–23:00", "06:00–24:00"][i % 3]
    if re.search(r"Email|信箱", col, re.I):
        return f"user{n}@example.com"
    return f"{col}{'甲乙丙丁戊己'[i % 6]}"


def table_rows(p: dict, columns: list[str], k: int = 5) -> list[list[str]]:
    if p.get("sample"):
        return [list(map(str, r)) for r in p["sample"]]
    p.setdefault("_defaults", []).append("sample")
    return [[sample_value(c, i, p) for c in columns] for i in range(k)]


PRIMARY_RE = r"送出|付款|確認|儲存|登入|申請|開立|核准|新增|建立|下一步|完成|繳費|查詢"


def arrange_buttons(labels: list[str]) -> list:
    """把主要動作（送出、付款、儲存…）放在最後並標為主按鈕；其他照原順序在左。"""
    if not labels:
        return []
    # 主要動作通常寫在最後：從後往前找；「重新查詢」「已有帳號，登入」這類次要動作不算
    secondary = r"^重新|^已有|^返回|^取消|^上一步|^回"
    k = next((i for i in range(len(labels) - 1, -1, -1) if re.search(PRIMARY_RE, labels[i]) and not re.search(secondary, labels[i])),
             len(labels) - 1)
    rest = [l for i, l in enumerate(labels) if i != k]
    return [*rest, {"label": labels[k], "style": "primary"}]


def _block(spec, kind: str, **defaults) -> dict:
    """頁面描述的補充元件可寫成 list（items）或 dict（完整區塊欄位）。"""
    if isinstance(spec, dict):
        return {"type": kind, **defaults, **spec}
    return {"type": kind, **defaults, "items": spec}


def _default(p: dict, what: str) -> None:
    p.setdefault("_defaults", [])
    if what not in p["_defaults"]:
        p["_defaults"].append(what)


def mockup_desc(p: dict) -> dict:
    """依頁面 kind 組出接近真實產品的版面。描述可加：sample、stats、tabs、chart、timeline、cards、notes，
    以及 stepper＋step（多步驟進度）、price（金額明細）、choices（付款方式等選項）、media（插圖：車牌畫面、證件…）、
    map（地圖＋標記）、tiles（狀態格）、hero_art／preview（首頁主視覺右側）、result（結果頁）。工具用預設內容補的地方記在 _defaults。"""
    p["_defaults"] = []
    kind = p.get("kind", "detail")
    out = {"id": p["id"], "name": p["name"], "desc": p["desc"]}
    for key in ("layout", "back", "bare"):
        if p.get(key):
            out[key] = p[key]
    if not p["_region"].get("backend"):
        out["active"] = p.get("active") or p["_node"]["title"]
    if p.get("blocks"):
        out["rows"] = p["blocks"]
        if backend_region(p):
            out["subtitle"] = p["desc"]
        return out
    backend = backend_region(p)
    if not p.get("fields") and kind in ("form", "detail", "result"):
        _default(p, "fields")
    fields = p.get("fields") or ["名稱*", "類型", "說明"]
    if not p.get("columns") and kind in ("list", "dashboard"):
        _default(p, "columns")
    columns = p.get("columns") or ["編號", "名稱", "狀態", "更新時間"]
    caption = [{"type": "caption", "text": "AI 起稿示意：版面、欄位與資料皆為示意，待審閱。", "align": "right"}]
    buttons = [b[0] if isinstance(b, (list, tuple)) else b for b in p.get("buttons", [])]
    stepper = ([{"type": "stepper", "items": p["stepper"], "current": max(0, int(p.get("step", 1)) - 1)}]
               if p.get("stepper") else [])
    extra_rows = []
    if p.get("tiles"):
        extra_rows.append([_block(p["tiles"], "tiles", title="狀態總覽")])
    if kind == "landing":
        out["hero"] = {"eyebrow": p.get("eyebrow") or p["_region"]["name"], "title": p.get("headline") or p["name"],
                       "lead": [p["desc"]] + ([p["lead"]] if p.get("lead") else [])}
        if p.get("hero_art") is not None:
            out["hero"]["art"] = p["hero_art"]
        if p.get("preview"):
            out["hero"]["preview"] = p["preview"]
        if p.get("hero_art") is None and not p.get("preview"):
            _default(p, "hero_art")
        if p.get("search"):
            out["hero"]["search"] = p["search"]
        else:
            out["hero"]["cta"] = buttons[:2] or ["立即使用", "了解更多"]
        if not p.get("cards") and not p.get("items"):
            _default(p, "cards")
        items = p.get("cards") or [{"title": it if isinstance(it, str) else it[0],
                                    "meta": "" if isinstance(it, str) else (it[1] if len(it) > 1 else ""),
                                    "button": "了解更多"} for it in (p.get("items") or ["服務一", "服務二", "服務三"])]
        rows = []
        if p.get("map"):
            rows.append([_block(p["map"], "map") if isinstance(p["map"], dict) else {"type": "map", "pins": p["map"]}])
        rows += [[{"type": "section", "text": p.get("section") or "服務特色"}], [{"type": "cards", "items": items[:6]}]]
        if p.get("stats"):
            rows.append([{"type": "stats", "items": p["stats"]}])
        if p.get("steps"):
            rows.append([{"type": "steps", "title": "如何使用", "items": p["steps"]},
                         {"type": "list", "title": "常見問題", "items": p.get("faq") or ["如何開始使用？", "有哪些方案？", "如何聯絡客服？"]}])
        out["rows"] = rows + extra_rows + [caption]
    elif kind == "list":
        rows = []
        if p.get("tabs"):
            rows.append([{"type": "tabs", "items": p["tabs"]}])
        if not p.get("filters"):
            _default(p, "filters")
        rows.append([{"type": "filters", "fields": p.get("filters") or ["關鍵字", "狀態", "日期區間"]}])
        rows += extra_rows
        readonly = re.search(r"審核|紀錄|記錄|事件|報表|稽核|查詢|監控|日誌|對帳|交易|通知", p["name"])
        admin = p["_region"]["column"] == "admin"
        acts = p.get("table_actions") or ((["匯出"] if readonly else ["匯出", "+ 新增"]) if admin else [])
        table = {"type": "table", "title": p.get("table_title") or p["name"], "columns": columns,
                 "rows": table_rows(p, columns), "actions": acts,
                 "row_actions": p.get("row_actions") or (["檢視", "編輯"] if backend else ["查看"]),
                 "pager": p.get("total") or f"共 {len(p.get('sample') or [0] * 5) * 25 + 3} 筆"}
        if p.get("map"):
            mp = _block(p["map"], "map") if isinstance(p["map"], dict) else {"type": "map", "pins": p["map"]}
            rows.append([{**mp, "flex": 1}, {**table, "flex": 1}])
        else:
            rows.append([table])
        if p.get("stats"):
            out["stats"] = p["stats"]
        out["rows"] = rows + [caption]
    elif kind == "form":
        side_items = p.get("notes") or p.get("steps")
        if not side_items and not p.get("price"):
            _default(p, "notes")
            side_items = ["必填欄位標示 *", "送出前可再次檢查資料", "送出後可在列表查看處理進度"]
        if p.get("price"):
            side = {**_block(p["price"], "price", title="金額明細"), "flex": 1}
        else:
            side = {"type": "steps" if p.get("steps") else "list", "title": "填寫說明" if not p.get("steps") else "申請流程",
                    "items": side_items, "flex": 1}
        form = {"type": "form", "title": p.get("form_title") or p["name"], "fields": fields, "cols": 2, "flex": 2}
        rows = [stepper] if stepper else []
        if p.get("media"):
            rows.append([{**_block(p["media"], "media"), "flex": 2}, side])
            rows.append([form])
        else:
            rows.append([form, side])
        if p.get("choices"):
            rows.append([_block(p["choices"], "choice", title="付款方式")])
        acts = buttons or ["取消", p.get("submit", "送出")]
        out["rows"] = rows + extra_rows + [[{"type": "actions", "buttons": arrange_buttons(acts)}], caption]
    elif kind == "dashboard":
        if not p.get("stats"):
            _default(p, "stats")
        out["stats"] = p.get("stats") or [[s, sample_value("數量", i, p), "本月"] for i, s in
                                          enumerate(p.get("items") or ["待處理", "本月新增", "累計"])][:4]
        if not p.get("chart"):
            _default(p, "chart")
        chart = p.get("chart") or {"title": "近 6 個月趨勢", "labels": ["6月", "7月", "8月", "9月", "10月", "11月"],
                                   "values": [42, 55, 48, 63, 71, 86]}
        if not p.get("todo"):
            _default(p, "todo")
        todo = {"type": "list", "title": "待辦事項", "items": p.get("todo") or [["待審核申請", "3 筆待處理"], ["異常通知", "1 筆未處理"],
                                                                         ["本週到期", "5 筆即將到期"]], "flex": 1}
        out["rows"] = [[{"type": "chart", **chart, "flex": 2}, todo], *extra_rows,
                       [{"type": "table", "title": p.get("table_title") or "最近資料", "columns": columns,
                         "rows": table_rows(p, columns, 4), "row_actions": ["檢視"]}], caption]
    elif kind == "login":
        login_fields = p.get("fields") or ["帳號*", "密碼*"]
        brand = {"type": "text", "title": p.get("welcome") or "歡迎回來",
                 "paragraphs": [p["desc"], p.get("lead") or "登入後即可使用完整服務。"], "flex": 1}
        links = p.get("links") or ["忘記密碼"]
        out["bare"] = True   # 登入頁不顯示側欄與選單
        out["rows"] = [[brand], [{"type": "form", "title": p["name"], "fields": login_fields, "cols": 1}],
                       [{"type": "actions", "buttons": [*links, {"label": p.get("submit", "登入"), "style": "primary"}]}], caption]
    elif kind == "text":
        out["rows"] = [[{"type": "text", "title": p["name"], "paragraphs": [p["desc"]] + list(p.get("paragraphs", [])), "flex": 2},
                        {"type": "list", "title": "相關連結", "items": p.get("items") or ["常見問題", "聯絡客服", "服務條款"], "flex": 1}],
                       caption]
    elif kind == "result":
        res = dict(p.get("result") or {})
        if not p.get("result"):
            _default(p, "result")
        pairs = [f if isinstance(f, (list, tuple)) else [f.rstrip("*"), sample_value(f.rstrip("*"), 0, p)] for f in fields]
        block = {"type": "result", "tone": res.get("tone", "ok"), "title": res.get("title") or p["name"],
                 "text": res.get("text") or p["desc"], "items": pairs, "buttons": buttons or ["回首頁"]}
        rows = [stepper] if stepper else []
        rows.append([block])
        if p.get("notes"):
            rows.append([{"type": "list", "title": p.get("notes_title", "接下來"), "items": p["notes"]}])
        out["rows"] = rows + extra_rows + [caption]
    else:   # detail
        pairs = [f if isinstance(f, (list, tuple)) else [f.rstrip("*"), sample_value(f.rstrip("*"), 0, p)] for f in fields]
        status = p.get("status") or next((v for k, v in pairs if re.search(r"狀態", k)), "處理中")
        summary = {"type": "summary", "title": p.get("record") or f"{p['name']}｜{sample_value('編號', 0, p)}", "status": status,
                   "meta": pairs[:4], "actions": buttons or (["返回", "編輯"] if backend else ["返回"])}
        rows = [stepper] if stepper else []
        rows.append([summary])
        rest = pairs[4:]
        if p.get("media"):
            md = _block(p["media"], "media", title="影像與資料")
            md.setdefault("side", rest)
            rows.append([md] + ([{**_block(p["price"], "price", title="金額明細"), "flex": .7}] if p.get("price") else []))
        else:
            if rest:   # 頁首已顯示前 4 個欄位，其餘放詳細資料
                rows.append([{"type": "kv", "title": "詳細資料", "items": rest, "cols": 3}]
                            + ([{**_block(p["price"], "price", title="金額明細"), "flex": .6}] if p.get("price") else []))
            elif p.get("price"):
                rows.append([_block(p["price"], "price", title="金額明細")])
        rows += extra_rows
        if not p.get("timeline"):
            _default(p, "timeline")
        timeline = p.get("timeline") or [["2026-11-20 14:32", "狀態更新", "由系統更新狀態"], ["2026-11-18 09:10", "建立", "建立資料"]]
        rows.append([{"type": "timeline", "items": timeline}])
        if p.get("actions_bottom"):
            rows.append([{"type": "actions", "buttons": arrange_buttons(p["actions_bottom"])}])
        out["rows"] = rows + [caption]
    if backend and not out.get("layout") == "mobile":
        out["subtitle"] = p["desc"]
    return out


def backend_region(p: dict) -> bool:
    return bool(p["_region"].get("backend"))


# ---------- 執行工具 ----------

def run(args: list[str], label: str) -> bool:
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip().splitlines()
    tail = out[-1] if out else "（無輸出）"
    print(f"  {label}：{tail}")
    if r.returncode != 0:
        print("\n".join("    " + x for x in out[-15:]))
    return r.returncode == 0


def find_plantuml() -> str:
    hit = shutil.which("plantuml")
    if hit:
        return hit
    cfg = json.loads(read(ROOT / "project.json"))
    kit = Path(cfg.get("kit", {}).get("path", "")).expanduser()
    kit = kit if kit.is_absolute() else (ROOT / kit)
    for cand in (kit.parent / "env" / "bin" / "plantuml.cmd", kit.parent / "env" / "bin" / "plantuml"):
        if cand.exists():
            return str(cand)
    return ""


# ---------- 品質提醒（--check 時列出；有提醒時預設不寫入） ----------

SCALE_MIN = {"精簡": 12, "標準": 24, "完整": 40}
PAGE_CATS = {"front", "member", "mgr", "cross"}


def quality(dr: Draft) -> list[str]:
    """依 規範/新專案.md「完整度清單」檢查起稿描述是否太保守或缺漏。"""
    d, w = dr.d, []
    scale = d.get("scale")
    if scale not in SCALE_MIN:
        w.append("缺少 scale（規模：精簡／標準／完整），請依第 4 題填寫")
    elif len(dr.pages) < SCALE_MIN[scale]:
        w.append(f"規模「{scale}」約需 {SCALE_MIN[scale]} 頁以上，目前只有 {len(dr.pages)} 頁：補上各區常見頁面（登入、列表、明細、審核、設定、報表）")
    backends = [r for r in dr.regions if r["prefix"] != "API"]
    for r in dr.regions:
        pages = [p for n in r.get("nodes", []) for p in n.get("pages", [])]
        if r["prefix"] == "API":
            if not r.get("apis"):
                w.append("API 區沒有任何 API：要提供就補上 API，不提供就把 API 區從 regions 拿掉")
            continue
        if not pages:
            w.append(f"{r['name']} 沒有頁面")
            continue
        if r.get("backend") and not any(p.get("kind") == "login" for p in pages):
            w.append(f"{r['name']} 是需要登入的區域，但沒有登入頁（kind: login）")
        lists = [p for p in pages if p.get("kind") in ("list", "dashboard")]
        bare = [p["id"] for p in lists if not p.get("sample")]
        if lists and len(bare) > len(lists) / 2:
            w.append(f"{r['name']} 的列表頁大多沒有 sample（示意資料）：{'、'.join(bare[:6])}；給 3–5 列像真的資料，示意圖才不像草稿")
        detail = [p["id"] for p in pages if p.get("kind") in ("form", "detail") and not p.get("blocks") and len(p.get("fields") or []) < 4]
        if detail:
            w.append(f"{r['name']} 的表單或明細頁欄位太少（少於 4 個）：{'、'.join(detail[:6])}")
    admin = next((r for r in backends if r["column"] == "admin"), None)
    if admin:
        admin_pages = [p for n in admin.get("nodes", []) for p in n.get("pages", [])]
        admin_mods = {p.get("module") for p in admin_pages}
        for p in dr.pages:
            personal = re.search(r"設定|密碼|個人資料|偏好", p["name"])   # 個人設定類表單不需要後台審核頁
            if p["_region"] is not admin and p.get("kind") == "form" and not personal and p.get("module") and p["module"] not in admin_mods:
                w.append(f"{p['id']} {p['name']}（{p['module']}）是申請或交易表單，後台沒有同模組的管理或審核頁")
                admin_mods.add(p["module"])
        if scale in ("標準", "完整"):
            names = " ".join(p["name"] for p in admin_pages)
            if not re.search(r"權限|帳號", names):
                w.append("後台缺少帳號與權限管理頁")
            if not re.search(r"稽核|操作紀錄|日誌", names):
                w.append("後台缺少稽核紀錄頁")
    vague = [p["id"] for p in dr.pages if "待確認" in p.get("desc", "")]
    if dr.pages and len(vague) / len(dr.pages) > 0.3:
        w.append(f"{len(vague)}/{len(dr.pages)} 頁的說明寫了「待確認」（{'、'.join(vague[:8])}…）：一般功能請具體推測並標 AI 起稿，待確認只用在 API、金流、法規、商業政策、費率與期限")
    bad_fields = [f"{p['id']}「{f}」" for p in dr.pages for f in (p.get("fields") or []) + (p.get("columns") or []) if "待確認" in f]
    if bad_fields:
        w.append("欄位名稱夾了「待確認」：" + "、".join(bad_fields[:6]) + "；欄位寫名稱即可，不確定的事寫進該頁 pending")
    for r in dr.regions:
        if r["prefix"] == "API":
            continue
        nodes = r.get("nodes", [])
        n_pages = sum(len(n.get("pages", [])) for n in nodes)
        if n_pages > 6 and len(nodes) < 2:
            w.append(f"{r['name']} 有 {n_pages} 頁卻只有 {len(nodes)} 個節點：每區分 2–5 個節點（節點就是側欄選單項目）")
        for n in nodes:
            if len(n.get("pages", [])) > 6:
                w.append(f"{r['name']}／{n['title']} 有 {len(n['pages'])} 頁，超過 6 頁：拆成多個節點")
    if admin:
        front = [p for p in dr.pages if p["_region"] is not admin]
        linked = [p for p in front if p.get("manage")]
        if front and len(linked) < len(front) / 2:
            w.append(f"前台與會員中心只有 {len(linked)}/{len(front)} 頁寫了 manage（由哪個後台頁管理）：燈箱的「管理頁面」會是空的")
    if dr.pages and sum(1 for p in dr.pages if p.get("similar")) < len(dr.pages) / 4:
        w.append("很少頁面寫 similar（類似頁面）：同節點或功能相近的頁面互相列出，燈箱「相關頁面」才有內容")
    flows = [f for f in dr.flows if not f.get("_auto")]
    if len(flows) < 3:
        w.append(f"跨頁流程只有 {len(flows)} 條，至少寫 3 條主要任務")
    for f in flows:
        n_steps = sum(1 for x in f.get("steps", []) if STEP_RE.match(x))
        if n_steps < 6:
            w.append(f"流程「{f['title']}」只有 {n_steps} 步：寫 6–12 步，含平台服務處理與結果回傳")
    if flows and not any(any(re.match(r"^\s*alt\b", x) for x in f.get("steps", [])) for f in flows):
        w.append("流程都沒有分支：主要流程至少寫一個 alt（成功／失敗或核准／退回），之後補 SA 的驗收條件要用到")
    for f in flows:
        cats = {participant_cat(dr, k, n) for k, n in flow_participants(dr, f)}
        if cats and cats <= PAGE_CATS:
            w.append(f"流程「{f['title']}」只有使用者與頁面，補上處理的平台服務或外部系統")
    bad_cat = sorted({e.get("category", "系統需求") for e in d.get("externals", [])} - {"系統需求", "營運需求"})
    if bad_cat:
        w.append(f"外部系統的需求類別只用「系統需求」「營運需求」兩類（自訂了：{'、'.join(bad_cat)}）；細節寫在交換資料欄")
    name = json.loads(read(ROOT / "project.json")).get("name", "")
    if len(name) > 10 and not d.get("short_name"):
        w.append(f"專案名稱「{name}」較長，示意圖頁首與側欄會被截斷：加 short_name（10 字以內的短品牌名）")
    for e in d.get("externals", []):
        if "是否" in (e.get("data", "") + e.get("status", "")) or "候選" in e.get("name", ""):
            w.append(f"外部系統「{e['name']}」寫成「是否需要」：請寫具體類型，狀態欄寫哪些細節待確認")
    if not d.get("regulations"):
        w.append("regulations 是空的：列出可能涉及的法規領域名稱（例如個人資料保護、消費者保護），不寫條文")
    return w


# ---------- 第二輪品質提醒：情境走查、功能比對、結果頁、畫面文字 ----------

JOURNEY_MIN = {"精簡": 3, "標準": 5, "完整": 7}
BENCH_MIN = {"精簡": 6, "標準": 10, "完整": 14}
TXN_RE = r"付款|繳費|支付|申請|預約|報名|訂購|購買|儲值|續約|退款"
PLACEHOLDER_RE = r"示意|服務[一二三]|選項[一二三]|範例資料|Lorem|XXX|○○|名稱[甲乙丙]"
CORE_DEFAULTS = {"fields", "notes", "result", "hero_art", "cards", "sample", "columns", "timeline"}


def visible_texts(desc: dict) -> list[tuple[str, str]]:
    """頁面描述中會出現在畫面上的文字（略過 caption 與設定鍵）：回傳 [(位置, 文字)]。"""
    skip = {"type", "art", "icon", "layout", "style", "align", "tone", "kind", "id", "region", "flex", "cols", "current",
            "selected", "step", "screen", "seed"}
    out: list[tuple[str, str]] = []

    def walk(x, where):
        if isinstance(x, dict):
            if x.get("type") == "caption":
                return
            for k, v in x.items():
                if k not in skip:
                    walk(v, f"{where}.{k}" if where else k)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v, where)
        elif isinstance(x, str):
            out.append((where, x))
    walk({k: v for k, v in desc.items() if k not in ("id", "name", "desc")}, "")
    return out


def quality_screens(dr: Draft) -> tuple[list[str], list[str]]:
    """依實際會畫出的頁面描述檢查畫面品質：佔位文字、待確認進畫面、表格假資料、預設版型。回傳 (提醒, 建議)。"""
    w, hints = [], []
    placeholder, pending, bad_rows, header_cells = [], [], [], []
    core_ids = journey_pages(dr)
    core_default, other_default = [], []
    for p in dr.pages:
        desc = mockup_desc(p)
        for where, t in visible_texts(desc):
            if re.search(PLACEHOLDER_RE, t):
                placeholder.append(f"{p['id']}「{t[:14]}」")
            if "待確認" in t and not re.search(r"rows", where):
                pending.append(f"{p['id']}「{t[:14]}」")
        for row in desc.get("rows", []):
            for b in (row if isinstance(row, list) else [row]):
                if b.get("type") != "table":
                    continue
                cols = b.get("columns", [])
                for r in b.get("rows", []):
                    vals = [str(v) for v in r]
                    if len(vals) >= 3 and len(set(vals)) == 1:
                        bad_rows.append(f"{p['id']}（整列都是「{vals[0][:10]}」）")
                    for hd, v in zip(cols, vals):
                        if v == hd or re.fullmatch(rf"{re.escape(hd)}[甲乙丙丁戊己]", v):
                            header_cells.append(f"{p['id']}「{hd}」")
                        if "待確認" in v and not re.search(r"費率|收費|價格|方案費|標準", hd):
                            pending.append(f"{p['id']} 表格「{hd}」")
        used = [x for x in p.get("_defaults", []) if x in CORE_DEFAULTS]
        if used:
            (core_default if p["id"] in core_ids else other_default).append(f"{p['id']}（{'、'.join(used)}）")
    no_opts = [f"{p['id']}「{(f.get('label') if isinstance(f, dict) else f[0])}」" for p in dr.pages for f in (p.get("fields") or [])
                if (isinstance(f, dict) and f.get("type") == "radio" and not f.get("options"))
                or (isinstance(f, (list, tuple)) and len(f) > 2 and f[2] == "radio")]
    if no_opts:
        w.append("單選欄位沒有選項，畫面會出現「選項一、選項二」：" + "、".join(no_opts[:6]) +
                 "；改寫成 {\"label\": …, \"type\": \"radio\", \"options\": [\"1 個月\", \"3 個月\"]}")
    if placeholder:
        w.append("畫面上有佔位文字（示意、服務一、範例…）：" + "、".join(dict.fromkeys(placeholder[:8])) +
                 "；改成像真的內容（真實感的名稱、編號、數字），「AI 起稿示意」註記工具會自動加")
    if pending:
        w.append("「待確認」出現在畫面文案或表格：" + "、".join(dict.fromkeys(pending[:8])) +
                 "；畫面寫成真實網站的樣子，不確定的事寫進該頁 pending（費率、收費標準欄位例外）")
    if bad_rows:
        w.append("表格 sample 有整列相同的值：" + "、".join(dict.fromkeys(bad_rows[:6])) + "；每列是一筆資料、每欄是一個欄位")
    if header_cells:
        w.append("表格欄位沒有給 sample，工具只能填「欄名＋甲乙丙」：" + "、".join(dict.fromkeys(header_cells[:8])))
    if core_default:
        w.append("情境走查經過的頁面仍用工具預設內容：" + "、".join(core_default[:8]) +
                 "；主要流程的頁面要給完整欄位、示意資料，並用 stepper／price／choices／media／map 或 blocks 畫出真實版面")
    if other_default:
        hints.append("以下頁面有部分內容是工具預設（可接受，審閱時再補）：" + "、".join(other_default[:10]))
    return w, hints


def journey_pages(dr: Draft) -> set[str]:
    ids = set()
    for j in dr.d.get("journeys", []):
        ids |= set(re.findall(r"\b[A-Z]+\d{2}\b", " ".join(map(str, j.get("steps", []) + j.get("exceptions", [])))))
    return ids


def quality_flow(dr: Draft) -> tuple[list[str], list[str]]:
    """流程想得夠不夠多：情境走查、功能範圍比對、結果頁、註冊與忘記密碼、例外流程、手機版。"""
    d, w, hints = dr.d, [], []
    scale = d.get("scale") if d.get("scale") in JOURNEY_MIN else "標準"
    journeys = d.get("journeys", [])
    if len(journeys) < JOURNEY_MIN[scale]:
        w.append(f"情境走查（journeys）只有 {len(journeys)} 條，規模「{scale}」至少 {JOURNEY_MIN[scale]} 條：每個角色列出最常做的任務，"
                 "從進入網站一路寫到完成（含結果頁），頁面清單依走查補齊")
    for j in journeys:
        pages = re.findall(r"\b[A-Z]+\d{2}\b", " ".join(map(str, j.get("steps", []))))
        if len(pages) < 3:
            w.append(f"情境「{j.get('task')}」只經過 {len(pages)} 頁：寫出每一步看到的畫面（步驟以頁面 ID 開頭）")
        if not j.get("exceptions"):
            w.append(f"情境「{j.get('task')}」沒有寫例外（exceptions）：查無資料、失敗、逾時、資料不符時畫面怎麼呈現")
    roles = {r["name"] for r in d.get("roles", [])}
    covered = {j.get("role") for j in journeys}
    missing = sorted(roles - covered)
    if journeys and missing:
        w.append("以下角色沒有情境走查：" + "、".join(missing))
    jp = journey_pages(dr)
    loose = [p["id"] for p in dr.pages if not backend_region(p) and p.get("kind") in ("form", "result") and p["id"] not in jp]
    if journeys and loose:
        w.append("前台的表單或結果頁沒有出現在任何情境走查：" + "、".join(loose[:8]))
    bench = d.get("benchmark", [])
    if len(bench) < BENCH_MIN[scale]:
        w.append(f"功能範圍比對（benchmark）只有 {len(bench)} 項，至少 {BENCH_MIN[scale]} 項：列出同類成熟產品常見的功能，"
                 "逐項標第一版／之後／不做，第一版的功能要對應到頁面")
    for b in bench:
        if b.get("scope") == "第一版" and not b.get("pages"):
            w.append(f"功能「{b.get('feature')}」標為第一版，但沒有對應頁面（pages）")
    # 交易或申請表單要有結果頁
    results = [p for p in dr.pages if p.get("kind") == "result"]
    for p in dr.pages:
        if backend_region(p) and p["_region"]["column"] == "admin":
            continue
        label = p["name"] + " ".join(str(b) for b in p.get("buttons", []))
        if p.get("kind") == "form" and re.search(TXN_RE, label):
            if not any(r.get("module") == p.get("module") for r in results):
                w.append(f"{p['id']} {p['name']} 送出後沒有結果頁：加一頁 kind: result（成功與失敗狀態），同一個 module")
    # 註冊與忘記密碼
    for r in dr.regions:
        if r["column"] in ("admin", "api"):
            continue
        pages = [p for n in r.get("nodes", []) for p in n.get("pages", [])]
        if any(p.get("kind") == "login" for p in pages) and not d.get("auth_note"):
            names = " ".join(p["name"] for p in dr.pages if not (backend_region(p) and p["_region"]["column"] == "admin"))
            lack = [x for x, pat in (("註冊", r"註冊|開通帳號"), ("忘記密碼", r"忘記密碼|重設密碼")) if not re.search(pat, names)]
            if lack:
                w.append(f"{r['name']} 有登入頁，但沒有{'、'.join(lack)}頁；若用第三方登入或簡訊驗證，寫在 auth_note 說明")
    # 例外流程
    flows = [f for f in dr.flows if not f.get("_auto")]
    with_else = [f for f in flows if any(re.match(r"^\s*else\b", x) for x in f.get("steps", []))]
    need = 1 if scale == "精簡" else 2
    if flows and len(with_else) < need:
        w.append(f"有失敗或例外分支（alt … else）的流程只有 {len(with_else)} 條，至少 {need} 條：付款失敗、審核退回、設備辨識失敗、逾時")
    # 手機版
    if not any(r.get("device") == "mobile" for r in dr.regions) and re.search(r"民眾|車主|消費者|會員|旅客|病患|家長|學生",
                                                                             d.get("summary", "") + json.dumps(d.get("roles", []), ensure_ascii=False)):
        hints.append("前台對象是一般民眾，多半用手機：考慮把前台（或會員中心）設 device: mobile，示意圖改用 390 寬手機版")
    return w, hints


def draw_screens(pages: list[dict]) -> bool:
    """以 mockup.py 產生頁面 SVG；彙整截斷等提醒。"""
    ok, notes = True, []
    with tempfile.TemporaryDirectory() as tmp:
        for p in pages:
            for old in (ROOT / "screens").glob(f"{p['id']}_*.svg"):
                if old.name != f"{p['id']}_{p['name']}.svg":
                    old.unlink()
            jp = Path(tmp) / f"{p['id']}.json"
            jp.write_text(json.dumps(mockup_desc(p), ensure_ascii=False), encoding="utf-8")
            r = subprocess.run([sys.executable, "scripts/mockup.py", str(jp), "--force"], cwd=ROOT, capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                ok = False
                print(f"  mockup {p['id']}：失敗\n" + (r.stdout + r.stderr)[-600:])
            cut = [ln for ln in r.stdout.splitlines() if "截斷" in ln]
            if cut:
                notes.append(f"{p['id']}（{len(cut)} 處，例如{cut[0].split('：', 1)[-1]}）")
    print(f"  mockup.py：已產生 {len(pages)} 張頁面 SVG")
    if notes:
        print("  文字被截斷（縮短文字或調整欄寬）：" + "、".join(notes[:10]))
    return ok


def regenerate_screens(dr: Draft, which: str) -> int:
    """視覺自檢後重畫：只重產指定頁面的 SVG（尚未手動調整過的初稿），再同步畫面文字與首頁資料。"""
    if not which:
        print("用法：draft_apply.py <描述.json> --screens A03,B05（或 all）")
        return 2
    ids = [p["id"] for p in dr.pages] if which == "all" else [x.strip() for x in which.split(",") if x.strip()]
    pages = [dr.page_by_id[i] for i in ids if i in dr.page_by_id]
    unknown = [i for i in ids if i not in dr.page_by_id]
    if unknown:
        print("找不到頁面：" + "、".join(unknown))
        return 1
    if not (ROOT / "screens").exists() or not list((ROOT / "screens").glob("*.svg")):
        print("停止｜專案還沒有起稿；--screens 只用於起稿後重畫")
        return 1
    ok = draw_screens(pages)
    ok &= run(["scripts/sync_screen_text.py", *ids], "sync_screen_text.py")
    for tool in ("svg_bundle.py", "inventory.py", "check.py"):
        ok &= run([f"scripts/{tool}"], tool)
    return 0 if ok else 1


def nested_project() -> Path | None:
    """專案位在另一個畫面規格專案裡面時，回傳外層專案路徑。"""
    for parent in ROOT.parents:
        if (parent / "project.json").exists() and (parent / "規範").is_dir():
            return parent
    return None


def main() -> int:
    args = sys.argv[1:]
    if "--example" in args:
        print(json.dumps(EXAMPLE, ensure_ascii=False, indent=2))
        return 0
    files = [a for a in args if not a.startswith("--")]
    if len(files) != 1:
        print(__doc__)
        return 2
    d = load(Path(files[0]))
    errs = validate(d)
    if errs:
        print("描述有問題，未寫入：")
        print("\n".join(f"  - {e}" for e in errs))
        return 1
    dr = Draft(d)
    print(f"描述 OK｜{len(dr.regions)} 區、{len(dr.pages)} 頁、{len(dr.apis)} 支 API、{len(dr.flows)} 條流程、"
          f"{len(module_list(dr))} 個業務模組")
    warns = quality(dr)
    w2, h2 = quality_flow(dr)
    w3, h3 = quality_screens(dr)
    warns += w2 + w3
    hints = h2 + h3
    if warns:
        print(f"品質提醒（{len(warns)} 項，依 規範/新專案.md「完整度清單」補強描述後再檢查）：")
        print("\n".join(f"  - {x}" for x in warns))
    if hints:
        print(f"建議（{len(hints)} 項，不擋寫入）：")
        print("\n".join(f"  - {x}" for x in hints))
    outer = nested_project()
    if outer:
        print(f"停止｜這個專案位在另一個畫面規格專案（{outer}）裡面；請把專案建在其他資料夾")
        return 1
    if "--check" in args:
        return 0
    if "--screens" in args:
        return regenerate_screens(dr, args[args.index("--screens") + 1] if len(args) > args.index("--screens") + 1 else "")
    if warns and "--accept-warnings" not in args:
        print("停止｜還有品質提醒，未寫入。補強描述後再試；確定要保留（例如使用者選了精簡）才加 --accept-warnings，並向使用者說明原因")
        return 1
    if list((ROOT / "screens").glob("*.svg")) and "--force" not in args:
        print("停止｜專案已有頁面示意圖；起稿只用於剛建立的專案（既有專案請依 規範/修改專案.md 修改）")
        return 1
    name = json.loads(read(ROOT / "project.json")).get("name", "")
    apply_project(dr)
    apply_sitemap(dr)
    apply_rules(dr)
    apply_hero(dr)
    apply_summary_card(dr)
    legend = apply_architecture(dr, name)
    cats = apply_flows(dr)
    apply_spec(dr, legend, cats)
    apply_optional(dr)
    print("已寫入｜project.json、網站地圖.md、專案規則.md、規格、architecture/、flows/")
    ok = draw_screens(dr.pages)
    if dr.pages:
        ok &= run(["scripts/sync_screen_text.py", *[p["id"] for p in dr.pages]], "sync_screen_text.py")
    ok &= run(["scripts/index_build.py"], "index_build.py")
    ok &= run(["scripts/flow_sync.py"], "flow_sync.py")
    puml = find_plantuml()
    targets = [str(p) for p in sorted((ROOT / "flows").glob("*.puml")) + sorted((ROOT / "architecture").glob("*.puml"))]
    if puml:
        r = subprocess.run([puml, "-tsvg", *targets], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("  plantuml：" + ("已渲染流程與架構圖" if r.returncode == 0 else "渲染失敗 " + (r.stdout + r.stderr)[-400:]))
        ok &= r.returncode == 0
    else:
        print("  plantuml：找不到本機 plantuml，流程與架構圖 SVG 未產生（執行安裝腳本後再跑 plantuml -tsvg flows/*.puml architecture/*.puml）")
        ok = False
    for tool in ("ai_entry.py", "dev_notes.py", "svg_bundle.py", "inventory.py", "check.py"):
        ok &= run([f"scripts/{tool}"], tool)
    print("起稿完成｜下一步：python3 scripts/preview.py 產生全部頁面縮圖，依 規範/新專案.md「視覺自檢」逐頁看過並修正"
          "（改描述後用 --screens 重畫），再請使用者打開 index.html。"
          if ok else "起稿有錯誤，見上方訊息")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
