#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时刷新微信公众号文章链接脚本
原理：用 Playwright 模拟真实用户搜索 → 点击链接 → 获取 mp.weixin.qq.com 永久链接
用法：
  python3 refresh_wechat_links.py          # 刷新所有微信来源条目
  python3 refresh_wechat_links.py --dry-run  # 只打印，不写入
  python3 refresh_wechat_links.py --limit 10  # 只处理前10条
"""

import json
import sys
import os
import time
import re
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_FILE = os.path.join(BASE_DIR, 'data', 'jobs.json')


def get_wechat_real_url(title, headless=True):
    """
    用 Playwright 模拟真实用户：
      1. 打开搜狗微信搜索
      2. 输入标题搜索
      3. 点击第一篇结果
      4. 等待跳转到 mp.weixin.qq.com 文章页
      5. 返回真实链接
    返回 (success: bool, url: str)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ❌ 未安装 playwright，请运行: pip install playwright && playwright install chromium")
        return False, ''

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=['--no-sandbox', '--disable-dev-shm-usage'],  # Linux/CI 环境必需
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 800},
                locale='zh-CN',
            )
            page = context.new_page()

            real_url = None

            def _on_response(response):
                nonlocal real_url
                url = response.url
                if 'mp.weixin.qq.com' in url:  # 兑容 /s/xxx 和 /s?__biz=xxx 两种格式
                    real_url = url

            page.on('response', _on_response)

            # Step1: 打开搜狗微信搜索首页
            print(f"    [PW] 打开搜狗微信...")
            page.goto('https://weixin.sogou.com/', timeout=20000, wait_until='domcontentloaded')
            time.sleep(1)

            # Step2: 输入搜索词（模拟真实用户）
            search_input = page.query_selector('#query')
            if not search_input:
                print(f"    ❌ 未找到搜索框")
                browser.close()
                return False, ''

            # 逐字输入（模拟人类）
            clean_title = re.sub(r'【.*?】', '', title)
            clean_title = re.sub(r'截止\d+月\d+[日号]', '', clean_title).strip()
            search_term = clean_title[:30]

            search_input.click()
            for char in search_term:
                search_input.type(char, delay=50)
            time.sleep(0.5)

            # 按回车搜索
            search_input.press('Enter')
            time.sleep(3)  # 等待搜索结果加载

            # Step3: 点击第一篇结果
            links = page.query_selector_all('.txt-box a')
            if not links:
                print(f"    ❌ 搜索结果为空")
                browser.close()
                return False, ''

            # 实际点击链接（而非直接 goto）
            print(f"    [PW] 点击第一篇结果...")
            links[0].click()
            time.sleep(4)  # 等待跳转完成

            final_url = page.url
            browser.close()

            if real_url:
                return True, real_url
            if 'mp.weixin.qq.com' in final_url and '/s/' in final_url:
                return True, final_url

            print(f"    ⚠️ 跳转后非微信原文: {final_url[:80]}")
            return False, ''

    except Exception as e:
        print(f"    ❌ Playwright 执行失败: {e}")
        return False, ''


def clean_title(title):
    """清理标题，去除干扰词"""
    t = re.sub(r'【.*?】', '', title)
    t = re.sub(r'截止\d+月\d+[日号]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def refresh_links(dry_run=False, limit=None):
    """主函数：刷新 jobs.json 中所有微信公众号文章的链接"""
    print("=" * 60)
    print("微信公众号链接刷新脚本（Playwright 模拟真实用户）")
    print("=" * 60)

    with open(JOBS_FILE, 'r', encoding='utf-8') as f:
        jobs = json.load(f)

    wechat_jobs = [j for j in jobs if j.get('source') == '微信公众号']
    print(f"总条目: {len(jobs)} 条")
    print(f"微信公众号条目: {len(wechat_jobs)} 条")
    print()

    if limit:
        wechat_jobs = wechat_jobs[:limit]
        print(f"（限制处理前 {limit} 条）")
        print()

    updated = 0
    failed = 0
    skipped = 0
    total = len(wechat_jobs)

    for i, job in enumerate(wechat_jobs):
        title = job.get('title', '')
        old_url = job.get('url', '')

        # 已经是正确的微信永久链接，跳过
        if 'mp.weixin.qq.com' in old_url and '/s/' in old_url:
            skipped += 1
            continue

        print(f"[{i+1}/{total}] {title[:50]}")

        success, real_url = get_wechat_real_url(title, headless=True)

        if success:
            print(f"    ✅ 获取成功: {real_url[:80]}...")
            if not dry_run:
                job['url'] = real_url
            updated += 1
        else:
            print(f"    ❌ 获取失败")
            failed += 1

        time.sleep(2)  # 礼貌延迟

    print()
    print("=" * 60)
    print(f"刷新完成:")
    print(f"  已更新: {updated} 条")
    print(f"  跳过(已有永久链接): {skipped} 条")
    print(f"  失败: {failed} 条")
    print("=" * 60)

    if not dry_run and updated > 0:
        with open(JOBS_FILE, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        print(f"\n已写入: {JOBS_FILE}")
    elif dry_run:
        print("\n[dry-run 模式，未写入文件]")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='刷新微信公众号文章链接')
    parser.add_argument('--dry-run', action='store_true', help='只打印，不写入')
    parser.add_argument('--limit', type=int, default=None, help='只处理前 N 条')
    args = parser.parse_args()

    refresh_links(dry_run=args.dry_run, limit=args.limit)
