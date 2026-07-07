#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鄂州市教育局招聘信息爬虫
目标网站：https://jyj.ezhou.gov.cn/xxgk/zc/gsgg/
重要说明：
- 距离武汉最近（仅60km）
- 很多武汉人可能在鄂州找工作
- 招聘信息丰富（页面有15+条招聘相关信息）
- 无反爬，静态HTML，数据非常丰富
"""

import requests
from bs4 import BeautifulSoup
import json
from crawl_utils import is_valid_job_posting, is_recent_date, extract_date_from_element, build_full_url, extract_teacher_tag

def crawl_ezhou():
    """爬取鄂州市教育局招聘信息"""
    base_url = "https://jyj.ezhou.gov.cn"
    target_url = f"{base_url}/xxgk/zc/gsgg/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    jobs = []
    
    try:
        print(f"正在爬取: {target_url}")
        response = requests.get(target_url, headers=headers, timeout=30)
        response.encoding = response.apparent_encoding or 'utf-8'
        
        if response.status_code != 200:
            print(f"访问失败，状态码: {response.status_code}")
            return jobs
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a')
        
        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not is_valid_job_posting(title, source='鄂州市教育局'):
                continue
            
            full_url = build_full_url(href, base_url, target_url)
            if not full_url:
                continue
            
            date_str = extract_date_from_element(link)
            if not date_str:
                date_str = '未知日期'
            
            job = {
                'title': title,
                'url': full_url,
                'date': date_str,
                'source': '鄂州市教育局',
                'type': extract_teacher_tag(title)
            }
            jobs.append(job)
            print(f"✓ 发现招聘信息: {title} ({date_str})")
        
        print(f"\n鄂州市教育局爬取完成，共找到 {len(jobs)} 条有效招聘信息")
        
    except Exception as e:
        print(f"爬取鄂州市教育局时发生错误: {str(e)}")
    
    return jobs

if __name__ == '__main__':
    jobs = crawl_ezhou()
    print(json.dumps(jobs, ensure_ascii=False, indent=2))
