#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
武汉市人力资源和社会保障局招聘信息爬虫
目标网站：http://rsj.wuhan.gov.cn/
主要爬取事业单位招聘（包含教师编制岗位）
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import re

def is_valid_job_posting(title):
    """
    判断是否为有效的招聘信息
    返回 True 如果是编制类教师招聘信息
    """
    # 必须包含的关键词（招聘相关）
    required_keywords = ['招聘', '招录', '招考', '引进']
    
    # 排除的关键词（非招聘信息）
    exclude_keywords = [
        '成绩公布', '成绩查询', '考试成绩', '分数',
        '公示名单', '拟聘用', '拟录用', '录取',
        '体检', '考察', '政审',
        '温馨提示', '考前提醒', '注意事项',
        '加分', '面试公告', '面试时间',
        '培训', '会议', '通知',
        '投诉', '举报', '违纪',
    ]
    
    # 检查是否包含必需关键词
    if not any(keyword in title for keyword in required_keywords):
        return False
    
    # 检查是否包含排除关键词
    for exclude in exclude_keywords:
        if exclude in title:
            return False
    
    # 必须是教师或事业单位招聘（编制类）
    job_keywords = ['教师', '编制', '事业单位', '学校', '教育系统']
    if not any(keyword in title for keyword in job_keywords):
        return False
    
    return True

def is_recent_date(date_str, months=12):
    """
    判断日期是否在最近 N 个月内
    months: 保留最近多少个月的信息
    """
    try:
        # 尝试解析日期
        if date_str == '未知日期':
            return False
        
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        
        return date_obj >= cutoff_date
    except:
        return False

def crawl_wuhan_hr():
    """爬取武汉市人力资源和社会保障局招聘信息"""
    base_url = "http://rsj.wuhan.gov.cn"
    # 事业单位招聘页面
    target_urls = [
        f"{base_url}/sy_20/jgzydwzp/",
        f"{base_url}/sy_20/zyjnbmzp/",
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
            
            # 查找所有链接
            links = soup.find_all('a')
            
            for link in links:
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                # 过滤条件1：判断是否为有效的招聘信息
                if not is_valid_job_posting(title):
                    continue
                
                # 构建完整URL
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    full_url = base_url + href
                else:
                    continue
                
                # 提取日期
                date_match = re.search(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})', title)
                if not date_match:
                    date_match = re.search(r'/(\d{8})/', href)
                
                if date_match:
                    if len(date_match.group(0)) == 8:  # YYYYMMDD format
                        date_str = f"{date_match.group(0)[:4]}-{date_match.group(0)[4:6]}-{date_match.group(0)[6:8]}"
                    else:
                        date_str = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
                else:
                    date_str = '未知日期'
                
                # 过滤条件2：只保留最近12个月的招聘信息
                if not is_recent_date(date_str, months=12):
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
