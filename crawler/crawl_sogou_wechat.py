#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜狗微信搜索爬虫 - 搜索公众号文章
"""

import requests
from bs4 import BeautifulSoup
import time
import re

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

                            # 提取发布时间
                            publish_time = '未知时间'
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
                                    publish_time = match.group(1)
                                    break

                            # 提取摘要
                            summary = ''
                            summary_elem = div.find('p')
                            if summary_elem:
                                summary = summary_elem.get_text(strip=True)[:200]

                            article = {
                                'title': title,
                                'url': sogou_url,
                                'account_name': account_name,
                                'publish_time': publish_time,
                                'summary': summary,
                                'source': '微信公众号',
                                'type': '公众号文章',
                                'keyword': keyword,
                                'date': publish_time if publish_time != '未知时间' else '未知日期'
                            }

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
