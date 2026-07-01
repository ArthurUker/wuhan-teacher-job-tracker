#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
孝感市教育局招聘信息爬虫
目标网站：https://jyj.xiaogan.gov.cn/c/xgsjyj/zkly/
重要说明：
- 距离武汉100km
- 有WAF（Web应用防火墙），但返回200 OK，可能可以爬取
- 需要测试反爬措施
"""

import requests
from bs4 import BeautifulSoup
import json
from crawl_utils import is_valid_job_posting, is_recent_date, extract_date_from_element, build_full_url

def crawl_xiaogan():
    """爬取孝感市教育局招聘信息"""
    base_url = "https://jyj.xiaogan.gov.cn"
    target_url = f"{base_url}/c/xgsjyj/zkly/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
    }
    
    jobs = []
    
    try:
        print(f"正在爬取: {target_url}")
        print("⚠️ 注意：该网站可能有WAF防护，正在尝试访问...")
        
        response = requests.get(target_url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"访问失败，状态码: {response.status_code}")
            return jobs
        
        # 检查是否被WAF拦截
        if 'waf' in response.text.lower() or '防火墙' in response.text or '非法请求' in response.text:
            print("⚠️ 警告：可能触发了WAF防护，尝试降低请求频率或添加更多请求头")
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
                'source': '孝感市教育局',
                'type': '教师招聘'
            }
            jobs.append(job)
            print(f"✓ 发现招聘信息: {title} ({date_str})")
        
        print(f"\n孝感市教育局爬取完成，共找到 {len(jobs)} 条有效招聘信息")
        
    except Exception as e:
        print(f"爬取孝感市教育局时发生错误: {str(e)}")
    
    return jobs

if __name__ == '__main__':
    jobs = crawl_xiaogan()
    print(json.dumps(jobs, ensure_ascii=False, indent=2))
