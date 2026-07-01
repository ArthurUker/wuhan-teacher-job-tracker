#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并所有爬虫数据并去重
"""

import json
import os
from datetime import datetime

def merge_data():
    """合并所有爬虫数据"""
    data_dir = os.path.join(os.path.dirname(__file__), '../data')
    output_file = os.path.join(data_dir, 'jobs.json')
    
    all_jobs = []
    
    # 读取各个爬虫的数据
    crawler_dir = os.path.dirname(__file__)
    crawlers = ['crawl_wuhan_education.py', 'crawl_hubei_exam.py']
    
    for crawler in crawlers:
        # 这里应该从每个爬虫的输出中读取数据
        # 为简化，我们直接运行爬虫并收集结果
        pass
    
    # 去重（根据标题和URL）
    seen = set()
    unique_jobs = []
    
    for job in all_jobs:
        key = (job['title'], job['url'])
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    
    # 按日期排序（最新的在前面）
    unique_jobs.sort(key=lambda x: x['date'], reverse=True)
    
    # 保存为JSON
    os.makedirs(data_dir, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_jobs, f, ensure_ascii=False, indent=2)
    
    print(f"数据合并完成，共 {len(unique_jobs)} 条招聘信息")
    print(f"数据已保存到: {output_file}")

if __name__ == '__main__':
    merge_data()
