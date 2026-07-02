#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武汉市教育局官网招聘信息爬虫
目标网站：https://jyj.wuhan.gov.cn/zwdt/tsgg/
重要说明：
- 该栏目列表为 JS 动态渲染（AJAX 异步加载），requests 无法拿到列表内容
- 改用 Playwright 渲染后再用 BeautifulSoup 解析
"""

from bs4 import BeautifulSoup
import json
from crawl_utils import is_valid_job_posting, is_recent_date, extract_date_from_element, build_full_url


def _render_with_playwright(url):
    """使用 Playwright 渲染 JS 动态页面，返回渲染后的 HTML"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            locale='zh-CN',
        )
        page = context.new_page()
        # domcontentloaded 后再等待 AJAX 异步加载完成
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        # 等待列表渲染（尝试等待常见列表容器，最多等 5 秒）
        for selector in ('ul.news_list', 'ul.list', '.news-list', 'table', '.list-content', 'div.list'):
            try:
                page.wait_for_selector(selector, timeout=5000)
                break
            except Exception:
                continue
        # 额外等待，确保异步数据加载完成
        page.wait_for_timeout(2500)
        html = page.content()
        context.close()
        browser.close()
        return html


def crawl_wuhan_education():
    """爬取武汉市教育局通知公告页面"""
    base_url = "https://jyj.wuhan.gov.cn"
    target_url = f"{base_url}/zwdt/tsgg/"

    jobs = []

    try:
        print(f"正在爬取: {target_url}")
        html = _render_with_playwright(target_url)

        soup = BeautifulSoup(html, 'html.parser')

        # 只取内容列表区的链接，避免遍历全页导航/页脚等无关 <a>
        content_area = (
            soup.find('div', class_='list') or
            soup.find('div', class_='news-list') or
            soup.find('ul', class_='news_list') or
            soup.find('div', class_='content') or
            soup.find('div', id='content') or
            soup
        )
        links = content_area.find_all('a')

        print(f"  页面渲染完成，内容区共解析到 {len(links)} 个链接")

        filtered_count = 0
        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href', '')

            if not title or len(title) < 5:
                continue

            if not is_valid_job_posting(title):
                filtered_count += 1
                continue

            full_url = build_full_url(href, base_url, target_url)
            if not full_url:
                continue

            date_str = extract_date_from_element(link)
            if not date_str:
                date_str = '未知日期'

            if not is_recent_date(date_str, title, months=6):
                print(f"跳过旧信息: {title} ({date_str})")
                continue

            job = {
                'title': title,
                'url': full_url,
                'date': date_str,
                'source': '武汉市教育局',
                'type': '教师招聘'
            }
            jobs.append(job)
            print(f"✓ 发现招聘信息: {title} ({date_str})")

        if filtered_count > 0:
            print(f"  注：{filtered_count} 个链接被过滤（非招聘信息）")

        print(f"\n武汉市教育局爬取完成，共找到 {len(jobs)} 条有效招聘信息")

    except Exception as e:
        print(f"爬取武汉市教育局时发生错误: {str(e)}")

    return jobs

if __name__ == '__main__':
    jobs = crawl_wuhan_education()
    print(json.dumps(jobs, ensure_ascii=False, indent=2))
