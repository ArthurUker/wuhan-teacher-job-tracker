#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武汉市人力资源和社会保障局招聘信息爬虫
目标网站：https://rsj.wuhan.gov.cn/
重要说明：
- 原 /zwgk_17/zfgkml/zkly/、/sy_20/jgzydwzp/ 等路径已全部 404（网站改版）
- 改用 Playwright 渲染首页，自适应发现"招聘/招考/人事/通知公告"等栏目真实链接，
  再逐个渲染解析，避免写死易失效的 URL
- 主要爬取事业单位招聘（包含教师编制岗位）
"""

from bs4 import BeautifulSoup
import json
from crawl_utils import is_valid_job_posting, is_recent_date, extract_date_from_element, build_full_url


def _render_page(context, url, wait_ms=2500):
    """用 Playwright 渲染页面并返回 HTML"""
    page = context.new_page()
    page.goto(url, timeout=30000, wait_until='domcontentloaded')
    page.wait_for_timeout(wait_ms)
    html = page.content()
    page.close()
    return html


def crawl_wuhan_hr():
    """爬取武汉市人力资源和社会保障局招聘信息（自适应栏目发现）"""
    base_url = "https://rsj.wuhan.gov.cn"

    jobs = []

    try:
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

            # 1. 渲染首页，自适应发现招聘相关栏目
            print(f"正在渲染首页: {base_url}")
            home_html = _render_page(context, base_url, wait_ms=2500)
            home_soup = BeautifulSoup(home_html, 'html.parser')

            nav_keywords = ['招聘', '招考', '录用', '招录', '事业单位', '人事', '通知公告', '公告']
            candidate_urls = []
            seen = set()
            for a in home_soup.find_all('a'):
                text = a.get_text(strip=True)
                href = a.get('href', '')
                if not text or not href:
                    continue
                if any(k in text for k in nav_keywords):
                    full = build_full_url(href, base_url, base_url + '/')
                    if full and full not in seen and 'rsj.wuhan.gov.cn' in full:
                        seen.add(full)
                        candidate_urls.append((text, full))

            print(f"  首页发现 {len(candidate_urls)} 个候选栏目")
            # 限制数量，控制运行时长
            candidate_urls = candidate_urls[:6]

            # 2. 逐个渲染栏目页解析
            for name, cu in candidate_urls:
                try:
                    print(f"正在爬取栏目[{name}]: {cu}")
                    sub_html = _render_page(context, cu, wait_ms=2500)
                    sub_soup = BeautifulSoup(sub_html, 'html.parser')

                    # 只取内容列表区的链接
                    content_area = (
                        sub_soup.find('div', class_='list') or
                        sub_soup.find('ul', class_='news_list') or
                        sub_soup.find('div', class_='content') or
                        sub_soup.find('div', id='content') or
                        sub_soup
                    )
                    links = content_area.find_all('a')

                    print(f"  栏目页内容区共解析到 {len(links)} 个链接")

                    for link in links:
                        title = link.get_text(strip=True)
                        href = link.get('href', '')

                        if not title or len(title) < 5:
                            continue

                        if not is_valid_job_posting(title):
                            continue

                        full_url = build_full_url(href, base_url, cu)
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
                            'source': '武汉市人社局',
                            'type': '事业单位招聘'
                        }
                        jobs.append(job)
                        print(f"✓ 发现招聘信息: {title} ({date_str})")
                except Exception as e:
                    print(f"爬取栏目 {cu} 失败: {str(e)}")
                    continue

            browser.close()

    except Exception as e:
        print(f"爬取武汉市人社局时发生错误: {str(e)}")

    print(f"武汉市人社局爬取完成，共找到 {len(jobs)} 条有效招聘信息")
    return jobs

if __name__ == '__main__':
    jobs = crawl_wuhan_hr()
    print(json.dumps(jobs, ensure_ascii=False, indent=2))
