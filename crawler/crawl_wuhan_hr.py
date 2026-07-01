#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武汉市人力资源和社会保障局招聘信息爬虫
目标网站：http://rsj.wuhan.gov.cn/
主要爬取事业单位招聘（包含教师编制岗位）
"""

import requests
from bs4 import BeautifulSoup
import json
from crawl_utils import is_valid_job_posting, is_recent_date, extract_date_from_element, build_full_url

def crawl_wuhan_hr():
    """爬取武汉市人力资源和社会保障局招聘信息"""
    base_url = "http://rsj.wuhan.gov.cn"
    # 事业单位招聘页面（多个候选路径）
    target_urls = [
        f"{base_url}/zwgk_17/zfgkml/zkly/",     # 招考录用
        f"{base_url}/sy_20/jgzydwzp/",           # 旧路径1
        f"{base_url}/sy_20/zyjnbmzp/",           # 旧路径2
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    jobs = []
    
    for target_url in target_urls:
        try:
            print(f"正在爬取: {target_url}")
            response = requests.get(target_url, headers=headers, timeout=30)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"访问失败，状态码: {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a')
            
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
                    'source': '武汉市人社局',
                    'type': '事业单位招聘'
                }
                jobs.append(job)
                print(f"✓ 发现招聘信息: {title} ({date_str})")
            
            print(f"完成爬取: {target_url}\n")
            
        except Exception as e:
            print(f"爬取 {target_url} 时发生错误: {str(e)}\n")
            continue
    
    print(f"武汉市人社局爬取完成，共找到 {len(jobs)} 条有效招聘信息")
    
    return jobs

if __name__ == '__main__':
    jobs = crawl_wuhan_hr()
    print(json.dumps(jobs, ensure_ascii=False, indent=2))
