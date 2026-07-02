#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武汉东湖新技术开发区（光谷）招聘信息爬虫
目标网站：https://www.wehdz.gov.cn/2022/zfxxgk/fdzdgk/zkzl/
重要说明：
- 独立招聘体系，不通过市级统一招聘
- 待遇好，招聘频繁（2023-2026年每年多次）
- 无反爬，静态HTML
"""

import requests
from bs4 import BeautifulSoup
import json
from crawl_utils import is_valid_job_posting, is_recent_date, extract_date_from_element, build_full_url, extract_teacher_tag

def crawl_optics_valley():
    """爬取武汉东湖新技术开发区招聘信息"""
    base_url = "https://www.wehdz.gov.cn"
    target_url = f"{base_url}/2022/zfxxgk/fdzdgk/zkzl/"
    
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
        links = soup.find_all('a')
        
        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not is_valid_job_posting(title):
                continue
            
            full_url = build_full_url(href, base_url, target_url)
            if not full_url:
                continue
            
            # 优先从标题提取日期，然后从兄弟/父元素提取
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
                'source': '武汉东湖新技术开发区',
                'type': extract_teacher_tag(title)
            }
            jobs.append(job)
            print(f"✓ 发现招聘信息: {title} ({date_str})")
        
        print(f"\n武汉东湖新技术开发区爬取完成，共找到 {len(jobs)} 条有效招聘信息")
        
    except Exception as e:
        print(f"爬取武汉东湖新技术开发区时发生错误: {str(e)}")
    
    return jobs

if __name__ == '__main__':
    jobs = crawl_optics_valley()
    print(json.dumps(jobs, ensure_ascii=False, indent=2))
