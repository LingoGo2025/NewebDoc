"""scripts/ 共用的路徑與解析函式（規格、網站地圖、SVG、index.html）。

專案專屬設定（檔名、頁面 ID 規則、網站地圖區域、架構圖、用語檢查）讀自專案根目錄的 project.json；
文件格式慣例（章節標題、標記文字）屬於工具本身，寫在這裡。
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

# Windows 的主控台與管線預設不是 UTF-8，中文訊息會出錯；一律以 UTF-8 輸出
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "project.json"
if not CONFIG_PATH.exists():
    raise SystemExit(f"找不到專案設定 {CONFIG_PATH}（scripts/ 需要 project.json）")
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

SPEC = ROOT / CONFIG["files"]["spec"]
SITEMAP = ROOT / CONFIG["files"]["sitemap"]
INDEX = ROOT / CONFIG["files"]["index"]
SCREENS = ROOT / "screens"
FLOWS = ROOT / "flows"
ARCH = ROOT / "architecture"   # 系統架構圖（不是流程，不受 flows 檢查）
ARCH_FIGURES: dict[str, str] = CONFIG["architecture"]["figures"]
FUNCTIONAL_FIGURE: str = CONFIG["architecture"].get("functional_figure", "")
TEXT_MARKER = "**畫面文字（依 SVG 順序）**"

# ---------- 主題與示意圖預設（project.json › theme、mockup、brand） ----------
THEME_DEFAULT = {
    "font": '"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif',
    "primary": "#087e78", "primary_dark": "#24675c", "primary_soft": "#e6f2eb",
    "sidebar": "#153f3b", "page_bg": "#f5f6f2", "surface": "#fffefa",
    "ink": "#203f3c", "heading": "#2b4a44", "text": "#526b63", "muted": "#75877f", "border": "#e1e8e2",
    "nav_text": "#284944", "nav_active": "#356e63",
}
_THEME_CFG = CONFIG.get("theme", {})
THEME: dict[str, str] = {**THEME_DEFAULT, **{k: v for k, v in _THEME_CFG.items() if k in THEME_DEFAULT}}
MOCKUP: dict[str, dict] = {k: v for k, v in CONFIG.get("mockup", {}).items() if not k.startswith("_")}
BRAND: dict = CONFIG.get("brand", {})


def region_theme(column: str) -> dict[str, str]:
    """某區（regions › column）的配色：全站主題再套上 theme › regions › <column> 覆寫。"""
    return {**THEME, **_THEME_CFG.get("regions", {}).get(column, {})}


# ---------- 頁面 ID（project.json › ids） ----------
_IDS = CONFIG["ids"]
_DIGITS = int(_IDS.get("digits", 2))
PAGE_PREFIXES: list[str] = _IDS["page_prefixes"]
API_PREFIX: str = _IDS.get("api_prefix", "API")
# 不含錨點的片段，可嵌入其他正規式；較長的字首排前面，避免 A 先吃掉 API 的 A
PAGE_ID = "(?:" + "|".join(map(re.escape, sorted(PAGE_PREFIXES, key=len, reverse=True))) + rf")\d{{{_DIGITS}}}"
API_ID = re.escape(API_PREFIX) + rf"\d{{{_DIGITS}}}"
ANY_ID = f"(?:{API_ID}|{PAGE_ID})"
ID_RE = re.compile(rf"^{ANY_ID}$")
PAGE_RE = re.compile(rf"^{PAGE_ID}$")
API_RE = re.compile(rf"^{API_ID}$")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def expand_ids(spec: str) -> list[str]:
    """'A04–A09、A11' → ['A04', ..., 'A09', 'A11']。"""
    ids: list[str] = []
    for prefix, start, end in re.findall(r"([A-Z]+)(\d+)(?:\s*[–\-~]\s*(?:[A-Z]+)?(\d+))?", spec):
        width = len(start)
        last = int(end) if end else int(start)
        ids += [f"{prefix}{n:0{width}d}" for n in range(int(start), last + 1)]
    return ids


# ---------- 網站地圖區域（project.json › regions） ----------

REGIONS: list[str] = [r["name"] for r in CONFIG["regions"]]
INDEX_COLUMN: dict[str, str] = {r["name"]: r["column"] for r in CONFIG["regions"]}
_REGION_PAGES = {r["name"]: set(expand_ids(r.get("pages", ""))) for r in CONFIG["regions"]}
_REGION_PREFIX = sorted(((r["prefix"], r["name"]) for r in CONFIG["regions"] if r.get("prefix")),
                        key=lambda x: len(x[0]), reverse=True)


def expected_region(pid: str) -> str:
    """頁面應在的網站地圖區域：先看各區明列的 pages，再看 prefix；都不符回傳「?」。"""
    for region, ids in _REGION_PAGES.items():
        if pid in ids:
            return region
    for prefix, region in _REGION_PREFIX:
        if re.fullmatch(rf"{re.escape(prefix)}\d+", pid):
            return region
    return "?"


# ---------- SVG ----------

MOBILE_DIR = SCREENS / "mobile"          # 手機版示意圖：screens/mobile/<ID>_<名稱>.svg（桌機版仍是主要畫面）
MOBILE_KEY = "- 手機版示意圖："           # 規格各頁：寫 SVG 路徑，或「無相關設計（原因）」
MOBILE_NONE = "無相關設計"


NOTE_ATTR = re.compile(r'data-note="([^"]+)"')   # 說明對照：SVG 區塊上的記號，值是開發說明的【標籤】


def note_label(text: str) -> str:
    """開發說明一條的標籤：「【專戶資訊】…」→「專戶資訊」。"""
    m = re.match(r"\s*【([^】]+)】", text or "")
    return m.group(1).strip() if m else ""


def note_markers(path: Path) -> list[str]:
    """SVG 裡的說明對照記號（依出現順序）。"""
    return NOTE_ATTR.findall(path.read_text(encoding="utf-8")) if path.exists() else []


def mobile_files() -> dict[str, Path]:
    """手機版示意圖（每頁最多一張）；沒有資料夾時為空。"""
    return {p.name.split("_", 1)[0]: p for p in sorted(MOBILE_DIR.glob("*.svg"))} if MOBILE_DIR.exists() else {}


def screen_files() -> dict[str, Path]:
    found: dict[str, list[Path]] = {}
    for path in sorted(SCREENS.glob("*.svg")):
        found.setdefault(path.name.split("_", 1)[0], []).append(path)
    return {k: v[0] for k, v in found.items()}  # 重複檔名由 duplicate_screen_ids() 回報


def duplicate_screen_ids() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in sorted(SCREENS.glob("*.svg")):
        found.setdefault(path.name.split("_", 1)[0], []).append(path.name)
    return {k: v for k, v in found.items() if len(v) > 1}


def screen_name(path: Path) -> str:
    return path.stem.split("_", 1)[1] if "_" in path.stem else path.stem


def svg_texts(path: Path) -> list[str]:
    values = []
    for node in ET.parse(path).iter():
        if node.tag.rsplit("}", 1)[-1] == "text":
            value = "".join(node.itertext()).strip()
            if value:
                values.append(value)
    return values


# ---------- 規格 Markdown ----------

@dataclass
class Section:
    anchor: str          # a05、flow-xxx、api-api01
    heading: str         # A05｜<頁面名稱>
    start: int           # 1-based 行號（anchor 行）
    end: int
    body: str            # 不含畫面文字清單
    text_list: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        """頁面 ID（A05、API01）或流程 key（flow-xxx）。"""
        m = re.match(rf"({ANY_ID})｜", self.heading)
        return m.group(1) if m else self.anchor


def spec_sections(text: str | None = None) -> list[Section]:
    text = read(SPEC) if text is None else text
    lines = text.split("\n")
    sections: list[Section] = []
    cur = None
    for i, line in enumerate(lines + ["## <end>"]):
        m = re.match(r'<a id="([^"]+)"></a>', line)
        if m or line.startswith("## "):
            if cur:
                cur_lines = lines[cur[1]:i]
                body_lines, items, in_list = [], [], False
                for ln in cur_lines:
                    if ln.strip() == TEXT_MARKER:
                        in_list = True
                        continue
                    if in_list:
                        if ln.startswith("- "):
                            items.append(ln[2:])
                        continue
                    body_lines.append(ln)
                heading = next((ln[4:] for ln in cur_lines if ln.startswith("### ")), cur[0])
                sections.append(Section(cur[0], heading, cur[1] + 1, i,
                                        "\n".join(body_lines).strip(), items))
            cur = (m.group(1), i) if m else None
    return sections


# ---------- 網站地圖 Markdown ----------

def sitemap_buttons(text: str | None = None) -> dict[str, list[tuple[str, str, int]]]:
    """區域 → [(ID, 節點標題, 行號)]，只讀「網站地圖節點」章節。"""
    text = read(SITEMAP) if text is None else text
    out: dict[str, list[tuple[str, str, int]]] = {r: [] for r in REGIONS}
    region = node = None
    in_nodes = False
    for n, line in enumerate(text.split("\n"), 1):
        if line.startswith("## "):
            in_nodes = line.strip() == "## 網站地圖節點"
            continue
        if not in_nodes:
            continue
        if line.startswith("### "):
            region = line[4:].strip()
        elif line.startswith("#### "):
            node = line[5:].strip()
        elif region in out:
            m = re.match(rf"- \[({PAGE_ID})\]", line) or re.search(rf"按鈕（({API_ID})）", line)
            if m:
                out[region].append((m.group(1), node or "", n))
    return out


def sitemap_nodes(text: str | None = None) -> dict[str, list[str]]:
    text = read(SITEMAP) if text is None else text
    out: dict[str, list[str]] = {r: [] for r in REGIONS}
    region, in_nodes = None, False
    for line in text.split("\n"):
        if line.startswith("## "):
            in_nodes = line.strip() == "## 網站地圖節點"
        elif in_nodes and line.startswith("### "):
            region = line[4:].strip()
        elif in_nodes and line.startswith("#### ") and region in out:
            out[region].append(line[5:].strip())
    return out


@dataclass
class MapButton:
    id: str
    text: str            # 網站地圖上的名稱（頁面為規格標題簡稱；API 為反引號內名稱）
    line: int
    desc: str = ""       # 子項「- 說明：」→ 燈箱說明
    similar: list[str] = field(default_factory=list)   # 子項「- 類似：」
    manage: list[str] = field(default_factory=list)    # 子項「- 管理：」
    flow: str = ""       # API 按鈕的流程圖 SVG（節點內「- 流程圖：`…`」）


@dataclass
class MapNode:
    title: str
    desc: str            # 節點第一段完整說明
    map_desc: str        # 「- 地圖說明：」簡短版（index.html 卡片用）；沒有時用 desc
    buttons: list[MapButton] = field(default_factory=list)


@dataclass
class MapRegion:
    name: str
    subtitle: str        # 區域標題下的 _斜體_ 說明
    map_desc: str        # 「- 地圖說明：」簡短版；沒有時用 subtitle
    nodes: list[MapNode] = field(default_factory=list)


def sitemap_tree(text: str | None = None) -> list[MapRegion]:
    """完整解析「網站地圖節點」章節：區域 → 節點 → 按鈕（含說明、類似、管理、API 流程圖）。"""
    text = read(SITEMAP) if text is None else text
    regions: list[MapRegion] = []
    region: MapRegion | None = None
    node: MapNode | None = None
    button: MapButton | None = None
    in_nodes = False
    split_ids = lambda v: [x for x in re.split(r"[、，,\s]+", v.strip()) if x]
    for n, line in enumerate(text.split("\n"), 1):
        if line.startswith("## "):
            in_nodes = line.strip() == "## 網站地圖節點"
            continue
        if not in_nodes:
            continue
        if line.startswith("### "):
            region = MapRegion(line[4:].strip(), "", "")
            regions.append(region)
            node = button = None
        elif region is None:
            continue
        elif line.startswith("#### "):
            node = MapNode(line[5:].strip(), "", "")
            region.nodes.append(node)
            button = None
        elif line.startswith("- 地圖說明："):
            value = line.split("：", 1)[1].strip()
            if node is None:
                region.map_desc = value
            else:
                node.map_desc = value
        elif node is None:
            m = re.fullmatch(r"_(.+)_", line.strip())
            if m and not region.subtitle:
                region.subtitle = m.group(1)
        elif m := (re.match(rf"- \[({PAGE_ID})\]\([^)]*\)\s*(.*)", line)
                   or re.match(rf"- 按鈕（({API_ID})）：`([^`]+)`", line)):
            button = MapButton(m.group(1), m.group(2).strip(), n)
            node.buttons.append(button)
        elif line.startswith("  - ") and button is not None:
            key, _, value = line[4:].partition("：")
            if key == "說明":
                button.desc = value.strip()
            elif key == "類似":
                button.similar = split_ids(value)
            elif key == "管理":
                button.manage = split_ids(value)
        elif m := re.match(r"- 流程圖：`([^`]+)`", line):
            if button is not None:
                button.flow = m.group(1)
        elif line.strip() and not node.desc and not line.startswith(("-", "頁面／按鈕")):
            node.desc = line.strip()
    for r in regions:
        r.map_desc = r.map_desc or r.subtitle
        for nd in r.nodes:
            nd.map_desc = nd.map_desc or nd.desc
    return regions


@dataclass
class Menu:
    key: str
    title: str
    style: str
    pages: list[str]
    items: list[str]
    active: dict[str, str]   # 頁面 ID → 選單項目
    line: int


def sitemap_menus(text: str | None = None) -> list[Menu]:
    text = read(SITEMAP) if text is None else text
    lines = text.split("\n")
    menus: list[Menu] = []
    for n, line in enumerate(lines):
        m = re.match(r"### (.+?)（nav: (\w+)）", line)
        if not m:
            continue
        style, pages, items, active = "", [], [], {}
        for ln in lines[n + 1:]:
            if ln.startswith("#"):
                break
            if ln.startswith("- 樣式："):
                style = ln.split("：", 1)[1].strip()
            elif ln.startswith("- 套用頁面："):
                pages = expand_ids(ln.split("：", 1)[1])
            else:
                row = re.match(r"\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|", ln)
                if row:
                    items.append(row.group(1))
                    for pid in row.group(2).split():
                        active[pid] = row.group(1)
        menus.append(Menu(m.group(2), m.group(1), style, pages, items, active, n + 1))
    return menus


# ---------- 系統架構（規格「## 系統架構」章） ----------

@dataclass
class Architecture:
    modules: list[tuple[str, list[str]]]   # [(模組名稱, 涵蓋頁面 ID)]
    excluded: set[str]                     # 「暫不歸入模組：」列出的 ID
    aliases: dict[str, str]                # 舊名稱 → 統一名稱（不含與統一名稱相同者）
    tables: dict[str, dict] = field(default_factory=dict)   # 小節標題 → {head, rows}
    guides: dict[str, str] = field(default_factory=dict)    # 圖名 → 讀圖說明
    legends: dict[str, list] = field(default_factory=dict)  # 圖名 → [{fill, line, dashed, meaning}]（「圖例」表）


def architecture_spec(text: str | None = None) -> Architecture:
    text = read(SPEC) if text is None else text
    arch = Architecture([], set(), {})
    in_chapter, table = False, None
    for line in text.split("\n"):
        if line.startswith("## "):
            in_chapter = line.startswith("## 系統架構")
            table = None
            continue
        if not in_chapter:
            continue
        if line.startswith("#### "):
            table = line[5:].strip()
            continue
        if line.startswith("- 暫不歸入模組："):
            arch.excluded |= set(expand_ids(line.split("：", 1)[1].split("（")[0]))
        if not line.startswith("|") or re.fullmatch(r"\|[\s|:-]+\|", line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        tbl = arch.tables.setdefault(table or "", {"head": None, "rows": []})
        if tbl["head"] is None:
            tbl["head"] = cells
        else:
            tbl["rows"].append(cells)
        if table == "讀圖說明" and cells[0] != "圖":
            arch.guides[cells[0]] = cells[1]
        if table == "圖例" and cells[0] != "圖" and len(cells) >= 4:
            line = cells[2].split()[0] if cells[2] else ""
            arch.legends.setdefault(cells[0], []).append(
                {"fill": cells[1], "line": line, "dashed": "虛線" in cells[2], "meaning": cells[3]})
        if table == "業務模組" and cells[0] != "模組":
            arch.modules.append((cells[0], expand_ids(cells[1])))
        elif table == "統一名稱" and cells[0] != "統一名稱":
            for old in re.split(r"[、，,]", cells[1]):
                old = old.strip()
                if old and old != cells[0]:
                    arch.aliases[old] = cells[0]
    return arch


FLOW_DATA_CATEGORY = "data"   # database 一律歸「資料」


def flow_palette(arch: "Architecture | None" = None) -> tuple[dict[str, dict], dict[str, str]]:
    """規格「系統架構 › 流程圖參與者類別」表 → ({代號: {name, fill, line}}, {參與者名稱: 代號})。"""
    arch = arch or architecture_spec()
    table = arch.tables.get("流程圖參與者類別") or {"rows": []}
    cats: dict[str, dict] = {}
    members: dict[str, str] = {}
    for row in table["rows"]:
        if len(row) < 5:
            continue
        name, code, fill, line, who = row[:5]
        cats[code] = {"name": name, "fill": fill, "line": line}
        for person in re.split(r"[、，,]", who):
            person = person.strip()
            if person and not person.startswith("（"):
                members[person] = code
    return cats, members


def arch_label(label: str) -> tuple[str, list[str]]:
    """PlantUML 方塊文字 → (去掉頁面 ID 與空白的名稱, 頁面 ID)。"""
    text = label.replace("\\n", " ")
    ids = expand_ids(text)
    name = re.sub(r"(?:[A-Z]+\d+(?:\s*[–\-~]\s*[A-Z]*\d+)?)", "", text)
    return re.sub(r"\s+", "", name), ids


def norm_name(name: str) -> str:
    return re.sub(r"\s+", "", name)


# ---------- flows ----------

def puml_meta(path: Path) -> dict:
    text = read(path)
    meta = {"key": path.stem, "source": text}
    for name in ("title", "pages", "order", "summary"):
        m = re.search(rf"^' @{name} (.*)$", text, re.M)
        meta[name] = m.group(1).strip() if m else ""
    meta["pages"] = [p.strip() for p in meta["pages"].split(",") if p.strip()]
    meta["order"] = parse_order(meta["order"])
    return meta


def parse_order(raw: str) -> list[list[str]]:
    """`C21,A14|A15` → [["C21"], ["A14", "A15"]]（逗號分先後，`|` 為並列）。"""
    return [[p.strip() for p in step.split("|") if p.strip()] for step in raw.split(",") if step.strip()]


def flow_list() -> list[dict]:
    return [puml_meta(p) for p in sorted(FLOWS.glob("*.puml"))]


# ---------- index.html ----------

def index_refs(text: str | None = None) -> list[dict]:
    """所有帶 data-screen-id 的連結（網站地圖按鈕；頁面示意圖圖庫已移除）。"""
    text = read(INDEX) if text is None else text
    refs = []
    for m in re.finditer(r"<a class=\"([^\"]+)\"([^>]*data-screen-id=\"[^\"]+\"[^>]*)>", text):
        attrs = dict(re.findall(r'data-([\w-]+)="([^"]*)"', m.group(2)))
        attrs["class"] = m.group(1)
        attrs["pos"] = m.start()
        refs.append(attrs)
    return refs


def index_flow_data(text: str | None = None) -> list[dict]:
    text = read(INDEX) if text is None else text
    m = re.search(r'<script type="application/json" id="sequence-flow-data">(.*?)</script>', text, re.S)
    return json.loads(m.group(1)) if m else []
