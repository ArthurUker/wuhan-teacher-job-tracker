#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
湖北省教育考试院教师招聘信息爬虫
目标网站：http://www.hbea.edu.cn/html/jszp/index.html
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re

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
        
        # 查找所有链接
        links = soup.find_all('a')
        
        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            # 筛选教师招聘相关信息
            keywords = ['教师', '招聘', '笔试', '面试', '成绩', '公示']
            if any(keyword in title for keyword in keywords) and len(title) > 5:
                # 构建完整URL
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('../'):
                    full_url = base_url + '/' + href.replace('../', '')
                elif href.startswith('./'):
                    full_url = target_url.replace('index.html', '') + href.replace('./', '')
                elif href.startswith('/'):
                    full_url = base_url + href
                else:
                    continue
                
                # 提取日期
                date_match = re.search(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})', title)
                if not date_match:
                    date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', href)
                
                if date_match:
                    date_str = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
                else:
                    date_str = '未知日期'
                
                job = {
                    'title': title,
                    'url': full_url,
                    'date': date_str,
                    'source': '湖北省教育考试院',
                    'type': '考试院公告'
                }
                jobs.append(job)
                print(f"发现招聘信息: {title}")
        
        print(f"湖北省教育考试院爬取完成，共找到 {len(jobs)} 条相关信息")
        
    except Exception as e:
        print(f"爬取湖北省教育考试院时发生错误: {str(e)}")
    
    return jobs

if __name__ == '__main__':
    jobs = crawl_hubei_exam()
    print(json.dumps(jobs, ensure_ascii=False, indent=2))
