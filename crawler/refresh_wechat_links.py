#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时刷新微信公众号文章链接（独立维护，不与全量搜索耦合）

策略（B 为主、A 兜底）：
  B（主）：直接对 jobs.json 中已有的公众号「临时链接」，跟随搜狗跳转解析为
          mp.weixin.qq.com 永久链接。先用 requests 快速尝试，失败再用 Playwright。
  A（兜底）：若 B 仍拿不到永久链接，则按标题重新搜狗搜索，取最新链接
          （优先永久链接，否则取最新临时链接续命）。

与 crawl_sogou_wechat.py 解耦：本脚本只维护“已有数据”的链接新鲜度，
不再做 16 关键词 × 2 页的全量搜索，因此更轻、反爬压力更小。

用法：
  python3 refresh_wechat_links.py                 # 刷新前 80 条非永久链接（默认上限）
  python3 refresh_wechat_links.py --dry-run      # 只打印，不写入
  python3 refresh_wechat_links.py --limit 20     # 只处理前 20 条
  python3 refresh_wechat_links.py --cap 120      # 设置 Playwright 操作上限
"""

import json
import sys
import os
import time
import re
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_FILE = os.path.join(BASE_DIR, 'data', 'jobs.json')

DEFAULT_LIMIT = 80      # 单次处理的非永久链接条数上限
DEFAULT_PW_CAP = 120    # Playwright 操作总数上限，避免单次运行过久

USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
             '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
VIEWPORT = {'width': 1280, 'height': 800}

# 复用 crawl_sogou_wechat 中已有的跳转/搜索逻辑，避免重复实现
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crawl_sogou_wechat import (
    follow_sogou_redirect_requests,
)


def is_permanent(url):
    """判断是否为 mp.weixin.qq.com 永久链接（/s/ 短链或 /s? 完整链）。"""
    return 'mp.weixin.qq.com' in (url or '') and '/s/' in url


def clean_title(title):
    """清理标题，去除干扰词，用于搜索匹配。"""
    t = re.sub(r'【.*?】', '', title)
    t = re.sub(r'截止\d+月\d+[日号]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def search_fresh_link(title, context=None, headless=True):
    """
    A 兜底：用 Playwright 按标题重新搜狗搜索，从结果 HTML 读取文章的 /link? 临时链接，
    再复用 B 逻辑（requests 快速 + Playwright 跟随）解析为永久链接。
    若传入共享 context 则复用（高效）；否则自建浏览器（兼容单次调用）。
    返回 (success: bool, url: str)，url 为永久链接或正规的 /link? 临时链接；
    绝不返回搜狗搜索结果页本身。
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
        print(f"    [A][PW] 搜狗搜索标题...")
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

        # 直接从结果 HTML 读取文章的搜狗临时链接（正规 /link? 形式）
        href = links[0].get_attribute('href') or ''
        if not href:
            return False, ''
        if href.startswith('http'):
            sogou_temp = href
        elif href.startswith('/'):
            sogou_temp = 'https://weixin.sogou.com' + href
        else:
            sogou_temp = 'https://weixin.sogou.com/' + href

        if '/link?' not in sogou_temp:
            # 不是文章临时链接，放弃
            return False, ''

        print(f"    [A] 命中搜索结果，解析: {sogou_temp[:60]}...")

        # 复用 B 逻辑拿到永久链接
        ok, u = follow_sogou_redirect_requests(sogou_temp)
        if ok:
            return True, u

        # Playwright 跟随（用当前 page）
        real_url = None

        def _on_response(response):
            nonlocal real_url
            if 'mp.weixin.qq.com' in response.url:
                real_url = response.url

        page.on('response', _on_response)
        try:
            page.goto(sogou_temp, timeout=20000, wait_until='domcontentloaded')
        except Exception:
            pass
        time.sleep(3)
        final_url = page.url
        if real_url:
            return True, real_url
        if 'mp.weixin.qq.com' in final_url and '/s/' in final_url:
            return True, final_url

        # 都没拿到永久链接，但至少有正规的 /link? 临时链接（比原失效链接好）
        return True, sogou_temp
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


def pw_follow_existing(sogou_url, context):
    """B 的 Playwright 部分：用共享 context 跟随现有临时链接，捕获永久链接。"""
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
        print(f"    [B][PW] 跟随跳转: {sogou_url[:60]}...")
        try:
            page.goto(sogou_url, timeout=20000, wait_until='domcontentloaded')
        except Exception:
            pass
        time.sleep(3)
        final_url = page.url
        if real_url:
            return real_url
        if 'mp.weixin.qq.com' in final_url and '/s/' in final_url:
            return final_url
        return None
    except Exception as e:
        print(f"    ❌ 跟随失败: {e}")
        return None
    finally:
        if page is not None:
            page.close()


def refresh_links(dry_run=False, limit=None, pw_cap=DEFAULT_PW_CAP, headless=True):
    """主函数：刷新 jobs.json 中所有微信公众号文章的链接（尽力而为，不抛异常）。"""
    print("=" * 60)
    print("微信公众号链接刷新脚本（B 解析永久链接为主 / A 按标题重搜兜底）")
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

    updated = skipped = failed = pw_used = 0
    total = len(wechat_jobs)

    # 准备共享浏览器（Playwright 可用时），跨条目复用，避免反复启动
    pw = None
    browser = None
    context = None
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        context = browser.new_context(
            user_agent=USER_AGENT, viewport=VIEWPORT, locale='zh-CN',
        )
    except Exception as e:
        print(f"⚠️ 未能初始化 Playwright（将仅用 requests 解析）: {e}")
        pw = browser = context = None

    try:
        for i, job in enumerate(wechat_jobs):
            title = job.get('title', '')
            old_url = job.get('url', '')

            # 已是永久链接，跳过
            if is_permanent(old_url):
                skipped += 1
                continue

            print(f"[{i+1}/{total}] {title[:50]}")

            new_url = None

            # ===== B（主）：解析现有临时链接为永久链接 =====
            # B1: requests 快速跟随（无浏览器开销）
            ok, u = follow_sogou_redirect_requests(old_url)
            if ok:
                new_url = u
                print(f"    ✅ [B][requests] 永久链接: {new_url[:80]}...")
            else:
                # B2: Playwright 跟随（受上限约束）
                if context is not None and pw_used < pw_cap:
                    pw_used += 1
                    u2 = pw_follow_existing(old_url, context)
                    if u2:
                        new_url = u2
                        print(f"    ✅ [B][PW] 永久链接: {new_url[:80]}...")

            # ===== A（兜底）：按标题重新搜狗搜索 =====
            if not (new_url and is_permanent(new_url)):
                if context is not None and pw_used < pw_cap:
                    pw_used += 1
                    ok2, u3 = search_fresh_link(title, context=context, headless=headless)
                    if ok2 and u3:
                        new_url = u3
                        tag = '永久链接' if is_permanent(u3) else '最新临时链接'
                        print(f"    ✅ [A] 获取{tag}: {new_url[:80]}...")
                else:
                    print(f"    ⏭️ 已达 Playwright 上限({pw_cap})，保留原链接")

            # 应用结果
            if new_url and new_url != old_url:
                if not dry_run:
                    job['url'] = new_url
                updated += 1
            else:
                failed += 1
                print(f"    ❌ 仍无有效链接，保留原临时链接")

            time.sleep(1.5)
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
    print(f"刷新完成: 已更新 {updated} 条 | 跳过(已永久) {skipped} 条 | "
          f"未改善 {failed} 条 | Playwright 使用 {pw_used} 次")
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
                        help=f'只处理前 N 条非永久链接（默认 {DEFAULT_LIMIT}）')
    parser.add_argument('--cap', type=int, default=DEFAULT_PW_CAP,
                        help=f'Playwright 操作总数上限（默认 {DEFAULT_PW_CAP}）')
    args = parser.parse_args()

    refresh_links(dry_run=args.dry_run, limit=args.limit, pw_cap=args.cap)
