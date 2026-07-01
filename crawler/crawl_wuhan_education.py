#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武汉市教育局官网招聘信息爬虫
目标网站：https://jyj.wuhan.gov.cn/zwdt/tsgg/
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re

def crawl_wuhan_education():
    """爬取武汉市教育局通知公告页面"""
    base_url = "https://jyj.wuhan.gov.cn"
    target_url = f"{base_url}/zwdt/tsgg/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    jobs = []
    
    try:
        print(f"正在爬取: {target_url}")
        response = requests.get(target_url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"访问失败，状态码: {response.status_code}")
            return jobs
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有链接，筛选包含"招聘"、"教师"、"编制"等关键词的
        links = soup.find_all('a')
        
        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            # 筛选与教师招聘相关的信息
            keywords = ['招聘', '教师', '编制', '教师资格', '教育系统']
            if any(keyword in title for keyword in keywords):
                # 构建完整URL
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    full_url = base_url + href
                else:
                    full_url = target_url + href
                
                # 尝试从标题或链接中提取日期
                date_match = re.search(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})', title)
                if date_match:
                    date_str = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
                else:
                    date_str = datetime.now().strftime('%Y-%m-%d')
                
                job = {
                    'title': title,
                    'url': full_url,
                    'date': date_str,
                    'source': '武汉市教育局',
                    'type': '教育局公告'
                }
                jobs.append(job)
                print(f"发现招聘信息: {title}")
        
        print(f"武汉市教育局爬取完成，共找到 {len(jobs)} 条相关信息")
        
    except Exception as e:
        print(f"爬取武汉市教育局时发生错误: {str(e)}")
    
    return jobs

if __name__ == '__main__':
    jobs = crawl_wuhan_education()
    print(json.dumps(jobs, ensure_ascii=False, indent=2))
