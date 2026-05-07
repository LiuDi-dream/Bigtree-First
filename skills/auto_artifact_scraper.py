#!/usr/bin/env python3
"""
圣遗物页签原始信息爬虫
1. 遍历圣遗物频道页下的所有子页面
2. 进入每个圣遗物详情页
3. 原样摘录“获取途径”相关表格内容到字典

说明：
- 不做强解析，只保留页面表格的原始行列文本。
- 适合先收集样本，后续再按真实页面格式设计解析规则。
"""

import asyncio
import json
import os
from typing import Any, Dict, List


CHANNEL_URL = (
    "https://baike.mihoyo.com/ys/obc/channel/map/189/218"
    "?bbs_presentation_style=no_header&visit_device=pc"
)
DETAIL_URL_TEMPLATE = (
    "https://baike.mihoyo.com/ys/obc/content/{content_id}/detail"
    "?bbs_presentation_style=no_header&visit_device=pc"
)
OUTPUT_PATH = "memory/artifact_get_methods_raw.json"


async def scroll_until_stable(page, pause_ms: int = 700, max_rounds: int = 30) -> None:
    """滚动页面直到内容不再增长，用于触发懒加载。"""
    previous_count = -1
    stable_rounds = 0

    for _ in range(max_rounds):
        current_count = await page.evaluate(
            """() => document.querySelectorAll('a[href*="/ys/obc/content/"]').length"""
        )
        if current_count == previous_count:
            stable_rounds += 1
        else:
            stable_rounds = 0
            previous_count = current_count

        if stable_rounds >= 3:
            break

        await page.evaluate("() => window.scrollBy(0, 2600)")
        await page.wait_for_timeout(pause_ms)

    await page.evaluate("() => window.scrollTo(0, 0)")
    await page.wait_for_timeout(400)


async def collect_artifact_pages(page) -> List[Dict[str, Any]]:
    """收集圣遗物页签下的所有子页面链接。"""
    await page.goto(CHANNEL_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(1500)
    await scroll_until_stable(page)

    pages = await page.evaluate(
        r"""
        () => {
            const seen = new Set();
            const items = [];
            const anchors = Array.from(document.querySelectorAll('a[href*="/ys/obc/content/"]'));

            for (const anchor of anchors) {
                const href = anchor.href || anchor.getAttribute('href') || '';
                const match = href.match(/\/ys\/obc\/content\/(\d+)\/detail/);
                if (!match) continue;

                const contentId = parseInt(match[1], 10);
                if (!contentId || seen.has(contentId)) continue;

                seen.add(contentId);
                items.push({
                    content_id: contentId,
                    title: (anchor.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 120),
                    url: href,
                });
            }

            return items;
        }
        """
    )

    return pages


async def extract_raw_getting_tables(page, content_id: int, title: str) -> Dict[str, Any]:
    """提取详情页中和“获取途径”相关的表格原文。"""
    url = DETAIL_URL_TEMPLATE.format(content_id=content_id)
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(1400)

    raw = await page.evaluate(
        r"""
        () => {
            const keywordHints = ['获取途径', '获取方式', '获取方法', '来源', '获取'];
            const tables = Array.from(document.querySelectorAll('table')).map((table, index) => {
                const rows = Array.from(table.querySelectorAll('tr')).map((row) => {
                    return Array.from(row.querySelectorAll('th,td')).map((cell) => {
                        return (cell.innerText || cell.textContent || '').replace(/\s+/g, ' ').trim();
                    });
                });

                const text = (table.innerText || table.textContent || '').replace(/\s+/g, ' ').trim();
                return { index, rows, text };
            });

            const matched = tables.filter((table) => {
                if (!table.rows.length) return false;
                if (keywordHints.some((keyword) => table.text.includes(keyword))) return true;
                return table.rows.some((row) => row.some((cell) => keywordHints.some((keyword) => cell.includes(keyword))));
            });

            return {
                title: document.querySelector('h1')?.textContent?.trim() || document.title || '',
                tables,
                matched,
            };
        }
        """
    )

    return {
        "content_id": content_id,
        "title": raw.get("title") or title,
        "url": url,
        "matched_tables": raw.get("matched", []),
        "table_count": len(raw.get("tables", [])),
    }


async def scrape_all_artifacts_async() -> Dict[str, Any]:
    """异步爬取所有圣遗物详情页的获取途径原始数据。"""
    from playwright.async_api import async_playwright

    result: Dict[str, Any] = {}

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()

        print("\n🚀 正在收集圣遗物页签下的子页面...")
        pages = await collect_artifact_pages(page)
        print(f"✅ 收集到 {len(pages)} 个圣遗物子页面")

        for index, item in enumerate(pages, 1):
            content_id = int(item["content_id"])
            title = item.get("title", "")
            print(f"[{index}/{len(pages)}] {title or content_id}")

            try:
                payload = await extract_raw_getting_tables(page, content_id, title)
                result[str(content_id)] = payload

                matched_count = len(payload.get("matched_tables", []))
                if matched_count:
                    print(f"  ✅ 提取到 {matched_count} 个匹配表格")
                else:
                    print("  ⚠️  未找到匹配表格，已保留基础页面信息")
            except Exception as exc:
                print(f"  ❌ 提取失败: {str(exc)}")
                result[str(content_id)] = {
                    "content_id": content_id,
                    "title": title,
                    "url": item.get("url", DETAIL_URL_TEMPLATE.format(content_id=content_id)),
                    "error": str(exc),
                    "matched_tables": [],
                }

            if index < len(pages):
                await page.wait_for_timeout(400)

        await browser.close()

    return result


def scrape_all_artifacts() -> Dict[str, Any]:
    """同步入口：爬取并保存全部结果。"""
    artifact_dict = asyncio.run(scrape_all_artifacts_async())

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(artifact_dict, file, ensure_ascii=False, indent=2)

    total_tables = sum(len(item.get("matched_tables", [])) for item in artifact_dict.values())
    print("\n" + "=" * 70)
    print("✅ 圣遗物原始抓取完成")
    print("=" * 70)
    print(f"📊 成功页面数: {len(artifact_dict)}")
    print(f"📊 匹配到的表格数: {total_tables}")
    print(f"📁 已保存到: {OUTPUT_PATH}")

    return artifact_dict


if __name__ == "__main__":
    print("=" * 70)
    print("圣遗物页签原始信息爬虫 v1.0")
    print("=" * 70)
    print()

    try:
        scrape_all_artifacts()
    except Exception as exc:
        print(f"\n❌ 爬虫运行出错: {str(exc)}")
        print("\n💡 建议:")
        print("  1. 检查网络连接")
        print("  2. 确保代理设置正确")
        print("  3. 重新运行脚本")