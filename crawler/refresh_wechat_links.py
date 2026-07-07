#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时刷新微信公众号文章链接脚本

原理：用 Playwright 模拟真实用户搜索 → 点击链接 → 获取 mp.weixin.qq.com 永久链接。
原脚本每篇文章启动一次浏览器（极慢），现改为复用单个浏览器/上下文，并支持数量上限，
以便接入 GitHub Actions（每 2 小时）批量刷新，把搜狗临时链接逐步替换为永久链接。

用法：
  python3 refresh_wechat_links.py                 # 刷新前 80 条非永久链接（默认上限）
  python3 refresh_wechat_links.py --dry-run      # 只打印，不写入
  python3 refresh_wechat_links.py --limit 20     # 只处理前 20 条
  python3 refresh_wechat_links.py --cap 200      # 设置默认上限为 200
"""

import json
import sys
import os
import time
import re
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_FILE = os.path.join(BASE_DIR, 'data', 'jobs.json')

DEFAULT_LIMIT = 80  # CI 单次的默认刷新上限，避免运行过久

USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
             '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
VIEWPORT = {'width': 1280, 'height': 800}


def clean_title(title):
    """清理标题，去除干扰词"""
    t = re.sub(r'【.*?】', '', title)
    t = re.sub(r'截止\d+月\d+[日号]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def get_wechat_real_url(title, context=None, headless=True):
    """
    用 Playwright 跟随搜狗跳转，获取真实的 mp.weixin.qq.com 文章链接。
    如果传入共享 context 则复用（高效）；否则自建浏览器（兼容单次调用）。
    返回 (success: bool, url: str)
    """
    own = False
    if context is None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("  ❌ 未安装 playwright，请运行: pip install playwright && playwright install chromium")
            return False, ''
        p = sync_playwright().start()
        browser = p.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        context = browser.new_context(
            user_agent=USER_AGENT, viewport=VIEWPORT, locale='zh-CN',
        )
        own = True

    page = None
    try:
        page = context.new_page()
        real_url = None

        def _on_response(response):
            nonlocal real_url
            url = response.url
            if 'mp.weixin.qq.com' in url:
                real_url = url

        page.on('response', _on_response)

        print(f"    [PW] 打开搜狗微信...")
        page.goto('https://weixin.sogou.com/', timeout=20000, wait_until='domcontentloaded')
        time.sleep(1)

        search_input = page.query_selector('#query')
        if not search_input:
            print(f"    ❌ 未找到搜索框")
            return False, ''

        clean = clean_title(title)
        search_term = clean[:30]

        search_input.click()
        for char in search_term:
            search_input.type(char, delay=50)
        time.sleep(0.5)
        search_input.press('Enter')
        time.sleep(3)

        links = page.query_selector_all('.txt-box a')
        if not links:
            print(f"    ❌ 搜索结果为空")
            return False, ''

        links[0].click()
        time.sleep(4)

        final_url = page.url
        if real_url:
            return True, real_url
        if 'mp.weixin.qq.com' in final_url and '/s/' in final_url:
            return True, final_url

        print(f"    ⚠️ 跳转后非微信原文: {final_url[:80]}")
        return False, ''
    except Exception as e:
        print(f"    ❌ Playwright 执行失败: {e}")
        return False, ''
    finally:
        if page is not None:
            page.close()
        if own:
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
                p.stop()
            except Exception:
                pass


def refresh_links(dry_run=False, limit=None, headless=True):
    """主函数：刷新 jobs.json 中所有微信公众号文章的链接（尽力而为，不抛异常）。"""
    print("=" * 60)
    print("微信公众号链接刷新脚本（复用单浏览器，高效模式）")
    print("=" * 60)

    try:
        with open(JOBS_FILE, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
    except Exception as e:
        print(f"读取 {JOBS_FILE} 失败: {e}")
        return

    wechat_jobs = [j for j in jobs if j.get('source') == '微信公众号']
    print(f"总条目: {len(jobs)} 条 | 微信公众号条目: {len(wechat_jobs)} 条")

    if limit:
        wechat_jobs = wechat_jobs[:limit]
        print(f"（限制处理前 {limit} 条）")

    updated = skipped = failed = 0
    total = len(wechat_jobs)

    # 复用单个浏览器/上下文，跨条目共享，避免反复启动
    browser = None
    context = None
    pw = None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("⚠️ 未安装 playwright，跳过刷新（不影响主流程）")
        return

    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        context = browser.new_context(
            user_agent=USER_AGENT, viewport=VIEWPORT, locale='zh-CN',
        )

        for i, job in enumerate(wechat_jobs):
            title = job.get('title', '')
            old_url = job.get('url', '')

            # 已是永久链接，跳过
            if 'mp.weixin.qq.com' in old_url and '/s/' in old_url:
                skipped += 1
                continue

            print(f"[{i+1}/{total}] {title[:50]}")
            success, real_url = get_wechat_real_url(title, context=context, headless=headless)

            if success:
                print(f"    ✅ 获取成功: {real_url[:80]}...")
                if not dry_run:
                    job['url'] = real_url
                updated += 1
            else:
                print(f"    ❌ 获取失败（保留原临时链接）")
                failed += 1

            time.sleep(2)
    except Exception as e:
        print(f"⚠️ 刷新过程中出现异常（已尽力处理已有条目）: {e}")
    finally:
        try:
            if context is not None:
                context.close()
        except Exception:
            pass
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass
        try:
            if pw is not None:
                pw.stop()
        except Exception:
            pass

    print()
    print("=" * 60)
    print(f"刷新完成: 已更新 {updated} 条 | 跳过(已永久) {skipped} 条 | 失败 {failed} 条")
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
    parser.add_argument('--limit', type=int, default=DEFAULT_LIMIT,
                        help=f'只处理前 N 条（默认 {DEFAULT_LIMIT}）')
    parser.add_argument('--cap', type=int, default=None,
                        help='设置默认上限（覆盖 DEFAULT_LIMIT）')
    args = parser.parse_args()

    limit = args.limit
    if args.cap is not None:
        limit = args.cap
    refresh_links(dry_run=args.dry_run, limit=limit)
