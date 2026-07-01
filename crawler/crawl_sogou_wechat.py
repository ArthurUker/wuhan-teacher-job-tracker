"""
搜狗微信搜索爬虫
使用 Playwright 模拟浏览器搜索微信公众号文章中的教师招聘信息
"""
import time
import random
import re
from datetime import datetime, timedelta
from urllib.parse import quote
from playwright.sync_api import sync_playwright

# 搜索关键词（每个城市一个关键词）
SEARCH_KEYWORDS = [
    "武汉 教师招聘",
    "湖北 教师招聘",
    "黄石 教师招聘",
    "鄂州 教师招聘",
    "黄冈 教师招聘",
    "孝感 教师招聘",
]

# 需要排除的关键词（非招聘类/广告类）
EXCLUDE_TITLES = [
    '成绩', '体检', '面试名单', '拟聘用', '公示',
    '报名入口', '准考证', '考场', '核减',
    '递补', '资格复审', '面试成绩', '综合成绩',
    '培训', '会议',
]

# 需要排除的来源（广告号/营销号/非官方渠道）
EXCLUDE_SOURCES = [
    '南宁租房宝',  # 与教师招聘无关
    '租房',
]

WEIXIN_SOGOU_BASE = 'https://weixin.sogou.com'


def create_browser_context(playwright):
    """创建浏览器上下文，模拟真实浏览器"""
    browser = playwright.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent=(
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        locale='zh-CN',
    )
    return browser, ctx


def parse_wechat_time(date_text):
    """
    解析搜狗微信搜索中的时间格式
    支持: "2026-6-24", "4小时前", "2天前", "2026-06-24"
    """
    date_text = date_text.strip()

    # 格式: "X小时前"
    m = re.match(r'(\d+)小时前', date_text)
    if m:
        hours = int(m.group(1))
        dt = datetime.now() - timedelta(hours=hours)
        return dt.strftime('%Y-%m-%d')

    # 格式: "X天前"
    m = re.match(r'(\d+)天前', date_text)
    if m:
        days = int(m.group(1))
        dt = datetime.now() - timedelta(days=days)
        return dt.strftime('%Y-%m-%d')

    # 格式: "X分钟前" -> 当作今天
    if '分钟前' in date_text:
        return datetime.now().strftime('%Y-%m-%d')

    # 格式: "昨天"
    if '昨天' in date_text:
        dt = datetime.now() - timedelta(days=1)
        return dt.strftime('%Y-%m-%d')

    # 格式: "2026-6-24" 或 "2026-06-24"
    m = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_text)
    if m:
        y, mon, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # 验证日期合法性
        if 2020 <= y <= 2030 and 1 <= mon <= 12 and 1 <= d <= 31:
            return f'{y}-{mon:02d}-{d:02d}'

    return '未知日期'


def is_relevant_job(title, summary=''):
    """判断是否为教师招聘相关信息"""
    text = title + ' ' + summary

    # 必须包含招聘相关词
    recruit_words = ['招聘', '招考', '引进', '教师', '老师']
    if not any(w in text for w in recruit_words):
        return False

    # 排除非招聘内容
    for kw in EXCLUDE_TITLES:
        if kw in title:
            return False

    return True


def is_within_months(date_str, months=6):
    """判断日期是否在指定月数内"""
    if date_str == '未知日期':
        return False  # 微信搜索结果日期未知的一律过滤掉

    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        cutoff = datetime.now() - timedelta(days=months * 30)
        return date_obj >= cutoff
    except:
        return False


def crawl_sogou_wechat():
    """爬取搜狗微信搜索结果"""
    jobs = []
    seen = set()  # 用于去重

    with sync_playwright() as p:
        browser, ctx = create_browser_context(p)

        for keyword in SEARCH_KEYWORDS:
            try:
                print(f'正在搜索微信公众号: "{keyword}"')
                page = ctx.new_page()

                # 关键：先访问搜狗首页
                page.goto('https://www.sogou.com/', timeout=15000)
                time.sleep(random.uniform(0.5, 1.0))

                # 再访问微信搜索
                encoded = quote(keyword)
                search_url = f'{WEIXIN_SOGOU_BASE}/weixin?type=2&query={encoded}'
                page.goto(search_url, timeout=15000)
                time.sleep(random.uniform(1.5, 2.5))

                # 检查是否被反爬
                content = page.content()
                if '验证码' in content or 'antispider' in content.lower():
                    print(f'  ⚠️ 触发反爬，跳过关键词: {keyword}')
                    page.close()
                    time.sleep(random.uniform(5, 10))
                    continue

                # 提取文章列表
                items = page.query_selector_all('ul.news-list2 li, ul.news-list li')
                print(f'  找到 {len(items)} 个结果')

                for item in items:
                    try:
                        # 提取标题
                        title_el = item.query_selector('h3 a, h3, .tit a')
                        if not title_el:
                            continue
                        title = title_el.inner_text().strip()

                        # 提取链接
                        link_el = item.query_selector('a[data-z="art"]')
                        if not link_el:
                            link_el = title_el
                        href = link_el.get_attribute('href', '')
                        if href.startswith('/'):
                            url = WEIXIN_SOGOU_BASE + href
                        else:
                            url = href

                        # 提取完整文本用于解析来源和日期
                        full_text = item.inner_text().strip()
                        lines = full_text.split('\n')

                        # 最后一行通常包含来源和日期
                        last_line = ''
                        for line in reversed(lines):
                            line = line.strip()
                            if line:
                                last_line = line
                                break

                        # 解析来源和日期: "湖北敏捷就业资讯2026-6-24"
                        date_match = re.search(
                            r'(\d{4}-\d{1,2}-\d{1,2}|\d+小时前|\d+天前|\d+分钟前|昨天)',
                            last_line
                        )

                        date_str = '未知日期'
                        source = '微信公众号'

                        if date_match:
                            date_str = parse_wechat_time(date_match.group(1))
                            # 日期之前的部分是来源
                            source = last_line[:date_match.start()].strip()
                            if not source or len(source) > 20:
                                source = '微信公众号'
                        else:
                            # 可能最后一行就是公众号名字，没有日期
                            if len(last_line) < 20:
                                source = last_line
                            else:
                                source = '微信公众号'

                        # 过滤
                        if not is_relevant_job(title):
                            continue

                        if any(kw in source for kw in EXCLUDE_SOURCES):
                            continue

                        if not is_within_months(date_str, months=6):
                            continue

                        # 去重
                        dedup_key = title[:40]
                        if dedup_key in seen:
                            continue
                        seen.add(dedup_key)

                        # 提取摘要
                        summary = ''
                        summary_lines = [
                            l.strip() for l in lines[1:] if l.strip()
                            and l.strip() != source + (date_match.group(0) if date_match else '')
                        ]
                        if summary_lines:
                            summary = summary_lines[0][:100]

                        job = {
                            'title': title,
                            'url': url,
                            'date': date_str,
                            'source': f'微信公众号({source})',
                            'type': '公众号文章',
                            'summary': summary,
                        }
                        jobs.append(job)
                        print(f'  ✓ {title[:50]} | {date_str} | {source}')

                    except Exception as e:
                        continue

                page.close()
                # 关键词之间随机延迟
                delay = random.uniform(3, 6)
                print(f'  等待 {delay:.1f} 秒后搜索下一个关键词...')
                time.sleep(delay)

            except Exception as e:
                print(f'  搜索关键词 "{keyword}" 失败: {e}')

        browser.close()

    print(f'\n搜狗微信搜索完成，共找到 {len(jobs)} 条有效信息')
    return jobs


if __name__ == '__main__':
    jobs = crawl_sogou_wechat()
    for j in jobs:
        print(f'  [{j["date"]}] {j["title"][:60]} | {j["source"]}')
