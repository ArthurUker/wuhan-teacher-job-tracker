#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄冈市教育局招聘信息爬虫
目标网站：https://jyj.hg.gov.cn/
重要说明：
- 教育强市，教师需求大
- 有"优师计划"等专项招聘
- 无反爬，静态HTML
- 注意：GitHub Actions 境外 runner 可能无法直连该站点（Network unreachable），
  已接入重试机制，偶发网络抖动可自动恢复；若为 IP 级封锁则仍会失败。
"""

from bs4 import BeautifulSoup
import json
from crawl_utils import is_valid_job_posting, is_recent_date, extract_date_from_element, build_full_url, retry_request

def crawl_huanggang():
    """爬取黄冈市教育局招聘信息"""
    base_url = "https://jyj.hg.gov.cn"
    # 通知公告页面
    target_url = f"{base_url}/zwgk/public/column/6636171?type=4&catId=7026845&action=list&nav=3"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    jobs = []

    try:
        print(f"正在爬取: {target_url}")
        response = retry_request(target_url, headers=headers, timeout=30)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            print(f"访问失败，状态码: {response.status_code}")
            return jobs

        soup = BeautifulSoup(response.text, 'html.parser')

        # 只取内容列表区的链接
        content_area = (
            soup.find('div', class_='list') or
            soup.find('ul', class_='news_list') or
            soup.find('div', class_='content') or
            soup.find('div', id='content') or
            soup
        )
        links = content_area.find_all('a')

        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href', '')

            if not is_valid_job_posting(title):
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
                'source': '黄冈市教育局',
                'type': '教师招聘'
            }
            jobs.append(job)
            print(f"✓ 发现招聘信息: {title} ({date_str})")

        print(f"\n黄冈市教育局爬取完成，共找到 {len(jobs)} 条有效招聘信息")

    except Exception as e:
        print(f"爬取黄冈市教育局时发生错误: {str(e)}")

    return jobs

if __name__ == '__main__':
    jobs = crawl_huanggang()
    print(json.dumps(jobs, ensure_ascii=False, indent=2))
