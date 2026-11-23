#!/usr/bin/env python3
"""維護者用（一般請用 sync_kit.py，會一併升版與自我測試）：從一個已驗證的專案匯出引擎到 plugin（engine/scripts/、engine/index.template.html）。

用法：
  python3 tools/build_engine.py <專案資料夾>            # 匯出
  python3 tools/build_engine.py <專案資料夾> --check    # 只比對 plugin 引擎是否與專案一致

引擎＝專案的 scripts/*.py、規範/（共用設計規範）與 index.html 中「內容區、產生區以外」的部分（見 slots.py）。
範本的內容區換成下方 SKELETON 的通用骨架（{{name}}、{{subtitle}}、{{footer}} 由 init_project.py 代入），
產生區清空（初始化後由 index_build.py、flow_sync.py 重產）。
"""
from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path

import slots

KIT = Path(__file__).resolve().parents[1]
ENGINE = KIT / "engine"
RULES = KIT / "規範"

ARCH_CARD = ('<article class="arch-card"><a class="arch-preview" data-arch="{key}" href="architecture/{key}.svg" data-lightbox="1" '
             'data-image="architecture/{key}.svg" data-svg="architecture/{key}.svg" data-title="{title}" data-description="{desc}" '
             'aria-label="放大 {title}"><img loading="lazy" src="architecture/{key}.svg" alt="{title}"></a>'
             '<div class="arch-meta"><h3>{title}</h3><p>{desc}</p></div></article>')
SKELETON = {
    "title": "<title>{{name}}｜網站地圖與頁面示意圖</title>",
    "project-css": "",
    "hero": '<h1>{{name}}</h1><p class="hero-subtitle">{{subtitle}}</p>',
    "architecture": ('<p class="arch-intro">說明平台邊界、外部系統與功能模組；文字版（外部系統、模組涵蓋頁面、共用服務、統一名稱）見規格「系統架構」章。</p>'
                     '<div class="arch-cards">'
                     + ARCH_CARD.format(key="system_context", title="系統情境圖",
                                        desc="平台與使用者、外部系統的邊界與交換資料；標「待確認」者依正式規格補上。")
                     + ARCH_CARD.format(key="functional_architecture", title="功能架構圖",
                                        desc="入口層（網站地圖各區）→ 業務模組（標示涵蓋頁面）→ 共用服務；技術與部署架構由 SD 決定。")
                     + "</div>"),
    "cards": "\n",
    "external-intro": '<p class="arch-intro">平台與外部系統的串接依需求類別分組；內容取自規格「系統架構 › 外部系統」表，標「待確認」者依正式規格補上。</p>',
    "migration": '<p class="arch-intro"><span class="ext-badge">選填・待補</span> 此區預留給舊系統移轉到本平台的計畫，目前只標出位置，內容待設計者補充；文字版見規格「舊系統移轉計畫（選填）」章。</p>',
    "regulations": '<p class="arch-intro"><span class="ext-badge">選填・待補</span> 此區預留給平台適用的相關法規，目前只標出位置，內容之後補上；文字版見規格「相關法規（選填）」章。</p>',
    "footer": "版本：頁面示意稿 0.1｜{{footer}}",
    "sitemap": "",
    "project-config": "{}",
    "project-theme": ":root{}",
    "sequence-flow-data": "[]",
}


def engine_scripts(project: Path) -> list[Path]:
    return sorted((project / "scripts").glob("*.py"))


def rules_diff(project: Path) -> list[str]:
    """專案 規範/ 與 plugin 規範/ 不同的檔案。"""
    mine = {p.name: p for p in (project / "規範").glob("*.md")} if (project / "規範").exists() else {}
    theirs = {p.name: p for p in RULES.glob("*.md")} if RULES.exists() else {}
    out = [f"規範/{n}" for n in sorted(mine) if n not in theirs or not filecmp.cmp(mine[n], theirs[n], shallow=False)]
    out += [f"規範/{n}（專案已刪除）" for n in sorted(set(theirs) - set(mine))]
    return out


def make_template(index_text: str) -> str:
    missing = [n for n in slots.SLOTS + list(slots.GENERATED) if n not in slots.extract(index_text)]
    if missing:
        raise SystemExit("專案 index.html 缺少區域標記：" + "、".join(missing))
    return slots.fill(index_text, SKELETON)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    project = Path(args[0]).resolve()
    template = make_template((project / "index.html").read_text(encoding="utf-8"))
    if "--check" in sys.argv:
        diffs = [p.name for p in engine_scripts(project)
                 if not (ENGINE / "scripts" / p.name).exists() or not filecmp.cmp(p, ENGINE / "scripts" / p.name, shallow=False)]
        tpl = ENGINE / "index.template.html"
        if not tpl.exists() or tpl.read_text(encoding="utf-8") != template:
            diffs.append("index.template.html")
        diffs += rules_diff(project)
        print("OK｜plugin 引擎與專案一致" if not diffs else "不同｜" + "、".join(diffs))
        return 1 if diffs else 0
    main_export(project, template)
    return 0


def main_export(project: Path, template: str | None = None) -> None:
    """匯出引擎：engine/scripts/ 換成專案 scripts/*.py，engine/index.template.html 換成專案 index.html 的範本版。"""
    if template is None:
        template = make_template((project / "index.html").read_text(encoding="utf-8"))
    (ENGINE / "scripts").mkdir(parents=True, exist_ok=True)
    for old in (ENGINE / "scripts").glob("*.py"):
        old.unlink()
    for p in engine_scripts(project):
        shutil.copy2(p, ENGINE / "scripts" / p.name)
    (ENGINE / "index.template.html").write_text(template, encoding="utf-8")
    if (project / "規範").exists():
        if RULES.exists():
            shutil.rmtree(RULES)
        shutil.copytree(project / "規範", RULES)
    print(f"已匯出｜{len(engine_scripts(project))} 個工具、index.template.html、規範/ → plugin")


if __name__ == "__main__":
    sys.exit(main())
