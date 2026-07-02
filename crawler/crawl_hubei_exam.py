#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
湖北省教育考试院教师招聘信息爬虫
目标网站：http://www.hbea.edu.cn/html/jszp/index.html
"""

import requests
from bs4 import BeautifulSoup
import json
from crawl_utils import is_valid_job_posting, is_recent_date, extract_date_from_element, build_full_url, extract_teacher_tag

def crawl_hubei_exam():
    """爬取湖北省教育考试院教师招聘页面"""
    base_url = "http://www.hbea.edu.cn"
    target_url = f"{base_url}/html/jszp/index.html"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
                'source': '湖北省教育考试院',
                'type': extract_teacher_tag(title)
            }
            jobs.append(job)
            print(f"✓ 发现招聘信息: {title} ({date_str})")
        
        print(f"\n湖北省教育考试院爬取完成，共找到 {len(jobs)} 条有效招聘信息")
        
    except Exception as e:
        print(f"爬取湖北省教育考试院时发生错误: {str(e)}")
    
    return jobs

if __name__ == '__main__':
    jobs = crawl_hubei_exam()
    print(json.dumps(jobs, ensure_ascii=False, indent=2))
