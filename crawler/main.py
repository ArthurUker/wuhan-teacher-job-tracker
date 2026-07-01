#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序：运行所有爬虫并合并数据
"""

import sys
import os
import json
from datetime import datetime

# 添加爬虫目录到路径
sys.path.insert(0, os.path.dirname(__file__))

def main():
    """运行所有爬虫并保存数据"""
    print("=" * 50)
    print("武汉教师招聘信息爬虫 - 开始运行")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    all_jobs = []
    
    # 爬取武汉市教育局
    try:
        from crawl_wuhan_education import crawl_wuhan_education
        wuhan_jobs = crawl_wuhan_education()
        all_jobs.extend(wuhan_jobs)
    except Exception as e:
        print(f"爬取武汉市教育局失败: {str(e)}")
    
    print()
    
    # 爬取湖北省教育考试院
    try:
        from crawl_hubei_exam import crawl_hubei_exam
        hubei_jobs = crawl_hubei_exam()
        all_jobs.extend(hubei_jobs)
    except Exception as e:
        print(f"爬取湖北省教育考试院失败: {str(e)}")
    
    print()
    print("=" * 50)
    
    # 去重
    seen = set()
    unique_jobs = []
    
    for job in all_jobs:
        key = (job['title'], job['url'])
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    
    # 按日期排序
    unique_jobs.sort(key=lambda x: x['date'] if x['date'] != '未知日期' else '2000-01-01', reverse=True)
    
    # 保存数据
    data_dir = os.path.join(os.path.dirname(__file__), '../data')
    os.makedirs(data_dir, exist_ok=True)
    output_file = os.path.join(data_dir, 'jobs.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_jobs, f, ensure_ascii=False, indent=2)
    
    print(f"爬取完成！")
    print(f"共爬取 {len(all_jobs)} 条信息")
    print(f"去重后 {len(unique_jobs)} 条信息")
    print(f"数据已保存到: {output_file}")
    print("=" * 50)

if __name__ == '__main__':
    main()
