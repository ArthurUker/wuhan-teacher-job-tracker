#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜狗微信搜索爬虫 - 搜索公众号文章
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime, timedelta


# ========== 过滤规则 ==========

# 需要保留的模式（即使包含"学院/大学"，也保留）
KEEP_PATTERNS = [
    '赴高校', '附属中学', '附中', '附属学校', '大学附属', '附小',
    '教育局', '事业单位', '公招', '编制', '公开招聘', '教师公开招聘',
    '中小学', '中学', '小学', '初中', '高中',
]

# 需要直接排除的模式（标题匹配即丢弃）
BLOCK_PATTERNS = [
    # 高校/职业类
    '职业学院', '职业技术学院', '技工学校',
    '辅导员', '博士后', '博士研究生', '硕士研究生',
    '人才引进.*高校', '高校.*招聘.*教师',
    # 高校作为雇主的招聘（大学/学院 + 第X批/次/轮 + 招聘）
    r'.*大学.*第\d+.*[批次轮次].*招聘',
    r'.*学院.*第\d+.*[批次轮次].*招聘',
    r'.*大学.*公开招聘.*公告',
    r'.*学院.*公开招聘.*公告',
    # 考试资料/真题/试题（非招聘公告）
    '真题', '试题', '试卷', '题库', '练习题',
    '历年真题', '模拟题', '押题',
    '笔试.*资料', '面试.*资料', '备考.*资料',
    '考试资料', '备考资料', '复习资料',
    # 培训/课程
    '培训课程', '网课', '直播课', '录播课',
    '辅导班', '培训班', '冲刺班',
    # 资料/下载
    '资料下载', '免费领取', '打包下载',
    # 其他非招聘内容
    '考试大纲', '考点汇总', '知识点',
]

# 高校雇主关键词（出现在"招聘"之前则判定为高校招聘）
UNIVERSITY_EMPLOYER_KEYS = ['大学', '学院']


def should_keep_article(title):
    """
    判断是否为中小学/公立学校教师招聘信息。
    返回 True 表示保留，False 表示丢弃。

    过滤优先级：
    1. 先检查排除模式（BLOCK_PATTERNS）- 直接丢弃
    2. 再检查是否为高校作为雇主的招聘 - 丢弃
    3. 最后检查保留模式（KEEP_PATTERNS）- 保留
    4. 默认保留
    """
    if not title:
        return False

    # 1. 先检查排除模式（正则）- 匹配即丢弃
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, title):
            return False

    # 2. 检查是否为高校作为雇主的招聘
    # 找所有 "招聘" 的位置，检查每个位置前面是否有大学/学院（且不是搜索关键词前缀）
    recruit_positions = [m.start() for m in re.finditer('招聘', title)]
    for recruit_idx in recruit_positions:
        prefix = title[:recruit_idx]
        # 去掉搜索关键词前缀（武汉教师/湖北教师等），检查剩余部分是否包含大学/学院
        stripped = prefix
        for prefix_keyword in ['武汉教师', '湖北教师', '黄石教师', '鄂州教师', 
                               '孝感教师', '黄冈教师', '咸宁教师', '武汉事业单位']:
            stripped = stripped.replace(prefix_keyword, '')
        for key in UNIVERSITY_EMPLOYER_KEYS:
            if key in stripped:
                return False

    # 3. 再检查保留模式
    for pattern in KEEP_PATTERNS:
        if pattern in title:
            return True

    # 4. 默认保留
    return True


# ========== 时间提取工具 ==========

def extract_title_date(title):
    """
    从标题中提取日期（优先）。
    支持格式：2026-07-02, 2026年07月02日, 7月2日, 7月等。
    返回格式：YYYY-MM-DD 或 YYYY-MM 或 '未知日期'。
    """
    now = datetime.now()

    # 完整日期：2026-07-02 或 2026年07月02日
    m = re.search(r'(\d{4})[年\-](\d{1,2})[月\-](\d{1,2})', title)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"

    # 月日：7月2日 或 07月02日（默认当年）
    m = re.search(r'(\d{1,2})月(\d{1,2})[日号]', title)
    if m:
        return f"{now.year}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}"

    # 仅月份：2026年7月 或 7月
    m = re.search(r'(\d{4})年(\d{1,2})月', title)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}"
    m = re.search(r'(\d{1,2})月', title)
    if m:
        return f"{now.year}-{m.group(1).zfill(2)}"

    return None


def parse_publish_time(publish_time_str):
    """
    解析公众号发布时间字符串，返回标准日期字符串。
    支持：2026-07-02, 2026年07月02日, 3天前, 5小时前, 昨天等。
    """
    now = datetime.now()

    if not publish_time_str or publish_time_str == '未知时间':
        return '未知日期'

    # 标准格式
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', publish_time_str)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    m = re.match(r'(\d{4})年(\d{2})月(\d{2})日', publish_time_str)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # 相对时间
    m = re.match(r'(\d+)天前', publish_time_str)
    if m:
        d = now - timedelta(days=int(m.group(1)))
        return d.strftime('%Y-%m-%d')

    m = re.match(r'(\d+)小时前', publish_time_str)
    if m:
        return now.strftime('%Y-%m-%d')

    m = re.match(r'昨天', publish_time_str)
    if m:
        d = now - timedelta(days=1)
        return d.strftime('%Y-%m-%d')

    return '未知日期'


def extract_deadline(title, summary=''):
    """
    从标题或摘要中提取报名/截止日期。
    返回：截止日期字符串（YYYY-MM-DD）或 None。
    """
    text = title + ' ' + summary

    # 截止/报名截止/报名截止时间
    patterns = [
        r'截止.{0,3}?(\d{4})[年\-](\d{1,2})[月\-](\d{1,2})',
        r'截止.{0,3}?(\d{1,2})月(\d{1,2})[日号]',
        r'报名.{0,5}?(\d{4})[年\-](\d{1,2})[月\-](\d{1,2})',
        r'报名.{0,5}?(\d{1,2})月(\d{1,2})[日号]',
        r'时间为.*?(\d{4})[年\-](\d{1,2})[月\-](\d{1,2})',
    ]

    for pat in patterns:
        m = re.search(pat, text)
        if m:
            if len(m.groups()) == 3:
                return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
            elif len(m.groups()) == 2:
                now = datetime.now()
                return f"{now.year}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}"

    return None


def is_urgent(deadline_str):
    """
    判断截止日期是否临近（3天内）。
    """
    if not deadline_str or deadline_str == '未知日期':
        return False
    try:
        d = datetime.strptime(deadline_str, '%Y-%m-%d')
        now = datetime.now()
        return (d - now).days <= 3
    except ValueError:
        return False

# 搜索关键词列表 - 覆盖武汉及周边地市各类教师招聘信息
SEARCH_KEYWORDS = [
    # 武汉及周边地市教师招聘
    "武汉教师招聘",
    "湖北教师招聘",
    "武汉事业单位招聘教师",
    "黄石教师招聘",
    "鄂州教师招聘",
    "黄冈教师招聘",
    "孝感教师招聘",
    "咸宁教师招聘",
    # 编制/公招类
    "湖北事业单位招聘教师",
    "教师公招",
    "编制教师招聘",
    # 重点中学招聘（很多重点中学通过公众号自主招聘）
    "中学招聘教师",
    "高中招聘教师",
    "武汉外国语学校招聘",
    "华师一附中招聘",
]


def crawl_sogou_wechat(keywords=None, max_pages=2):
    """
    爬取搜狗微信搜索结果
    keywords: 搜索关键词列表，默认使用 SEARCH_KEYWORDS
    """
    if keywords is None:
        keywords = SEARCH_KEYWORDS

    base_url = "https://weixin.sogou.com/weixin"
    articles = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://weixin.sogou.com/',
        'Connection': 'keep-alive',
    }

    for keyword in keywords:
        try:
            print(f"正在搜索关键词: {keyword}")
            keyword_articles = []

            for page in range(1, max_pages + 1):
                try:
                    params = {
                        'type': 2,  # 2=文章搜索
                        'query': keyword,
                        'page': page
                    }

                    print(f"  正在爬取第 {page} 页")
                    response = requests.get(base_url, params=params, headers=headers, timeout=30)

                    if response.status_code != 200:
                        print(f"  请求失败，状态码: {response.status_code}")
                        break

                    soup = BeautifulSoup(response.text, 'html.parser')

                    # 查找文章列表
                    article_divs = soup.find_all('div', class_='txt-box')

                    if not article_divs:
                        print(f"  未找到文章，可能已到最后一页")
                        break

                    print(f"  找到 {len(article_divs)} 篇文章")

                    for div in article_divs:
                        try:
                            # 提取标题和链接
                            title_link = div.find('a')
                            if not title_link:
                                continue

                            title = title_link.get_text(strip=True)
                            sogou_url = title_link.get('href', '')

                            # 构建完整URL
                            if sogou_url.startswith('/'):
                                sogou_url = 'https://weixin.sogou.com' + sogou_url

                            # 提取公众号名称
                            account_name = '未知公众号'
                            account_elem = div.find('span', class_='all-time-y2')
                            if account_elem:
                                account_name = account_elem.get_text(strip=True)
                            else:
                                for span in div.find_all('span'):
                                    text = span.get_text(strip=True)
                                    if text and ('湖北' in text or '武汉' in text or '教育' in text or '教师' in text):
                                        account_name = text
                                        break

                            # 提取发布时间（公众号发布时间）
                            publish_time_raw = '未知时间'
                            time_text = div.get_text()
                            time_patterns = [
                                r'(\d{4}-\d{2}-\d{2})',
                                r'(\d{4}年\d{2}月\d{2}日)',
                                r'(\d+天前)',
                                r'(\d+小时前)',
                            ]
                            for pattern in time_patterns:
                                match = re.search(pattern, time_text)
                                if match:
                                    publish_time_raw = match.group(1)
                                    break

                            publish_time = parse_publish_time(publish_time_raw)

                            # 从标题提取日期（优先于发布时间）
                            title_date = extract_title_date(title)
                            final_date = title_date if title_date else publish_time

                            # 提取摘要
                            summary = ''
                            summary_elem = div.find('p')
                            if summary_elem:
                                summary = summary_elem.get_text(strip=True)[:200]

                            # 提取截止日期
                            deadline = extract_deadline(title, summary)
                            urgent = is_urgent(deadline)

                            article = {
                                'title': title,
                                'url': sogou_url,
                                'account_name': account_name,
                                'publish_time': publish_time,   # 公众号发布日期
                                'title_date': title_date or '', # 标题中提取的日期
                                'date': final_date,            # 优先用标题日期，其次用发布日期
                                'deadline': deadline or '',    # 截止日期
                                'urgent': urgent,              # 是否临近截止
                                'summary': summary,
                                'source': '微信公众号',
                                'type': '公众号文章',
                                'keyword': keyword,
                            }

                            # 过滤非中小学教师招聘信息
                            if not should_keep_article(title):
                                print(f"    跳过非中小学招聘: {title[:60]}")
                                continue

                            keyword_articles.append(article)

                        except Exception as e:
                            print(f"  解析单篇文章时出错: {e}")
                            continue

                    # 礼貌延迟
                    time.sleep(2)

                except Exception as e:
                    print(f"爬取第 {page} 页时出错: {e}")
                    break

            # 对当前关键词去重（按标题）
            seen_titles = set()
            for art in keyword_articles:
                if art['title'] not in seen_titles:
                    seen_titles.add(art['title'])
                    articles.append(art)

            print(f"  关键词「{keyword}」共获取 {len(keyword_articles)} 篇（去重后 {len([a for a in keyword_articles if a['title'] in seen_titles])} 篇）")

            # 不同关键词之间延迟
            time.sleep(3)

        except Exception as e:
            print(f"搜索关键词 {keyword} 时出错: {e}")
            continue

    print(f"\n搜狗微信搜索完成，共找到 {len(articles)} 篇文章（{len(keywords)} 个关键词）")
    return articles


def main():
    """主函数 - 测试爬虫"""
    print("=" * 60)
    print("测试搜狗微信搜索爬虫")
    print("=" * 60)

    all_articles = crawl_sogou_wechat(max_pages=1)

    # 保存结果
    import json
    output_file = '../data/wechat_articles.json'

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    print(f"\n所有文章已保存到: {output_file}")
    print(f"总共有 {len(all_articles)} 篇公众号文章")

    # 显示前3篇
    if all_articles:
        print("\n前3篇文章:")
        for i, article in enumerate(all_articles[:3], 1):
            print(f"\n{i}. {article['title']}")
            print(f"   公众号: {article['account_name']}")
            print(f"   时间: {article['publish_time']}")
            print(f"   摘要: {article['summary'][:50]}...")


if __name__ == '__main__':
    main()
