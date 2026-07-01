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
    
    # 爬取武汉市人社局
    try:
        from crawl_wuhan_hr import crawl_wuhan_hr
        wuhan_hr_jobs = crawl_wuhan_hr()
        all_jobs.extend(wuhan_hr_jobs)
    except Exception as e:
        print(f"爬取武汉市人社局失败: {str(e)}")
    
    print()
    
    # 爬取湖北省教育考试院
    try:
        from crawl_hubei_exam import crawl_hubei_exam
        hubei_jobs = crawl_hubei_exam()
        all_jobs.extend(hubei_jobs)
    except Exception as e:
        print(f"爬取湖北省教育考试院失败: {str(e)}")
    
    print()
    
    # 爬取武汉东湖新技术开发区（光谷）
    try:
        from crawl_optics_valley import crawl_optics_valley
        optics_valley_jobs = crawl_optics_valley()
        all_jobs.extend(optics_valley_jobs)
    except Exception as e:
        print(f"爬取武汉东湖新技术开发区失败: {str(e)}")
    
    print()
    
    # 爬取汉阳区人民政府
    try:
        from crawl_hanyang import crawl_hanyang
        hanyang_jobs = crawl_hanyang()
        all_jobs.extend(hanyang_jobs)
    except Exception as e:
        print(f"爬取汉阳区人民政府失败: {str(e)}")
    
    print()
    
    # 爬取蔡甸区人民政府
    try:
        from crawl_caidian import crawl_caidian
        caidian_jobs = crawl_caidian()
        all_jobs.extend(caidian_jobs)
    except Exception as e:
        print(f"爬取蔡甸区人民政府失败: {str(e)}")
    
    print()
    
    # 爬取鄂州市教育局
    try:
        from crawl_ezhou import crawl_ezhou
        ezhou_jobs = crawl_ezhou()
        all_jobs.extend(ezhou_jobs)
    except Exception as e:
        print(f"爬取鄂州市教育局失败: {str(e)}")
    
    print()
    
    # 爬取黄石市教育局
    try:
        from crawl_huangshi import crawl_huangshi
        huangshi_jobs = crawl_huangshi()
        all_jobs.extend(huangshi_jobs)
    except Exception as e:
        print(f"爬取黄石市教育局失败: {str(e)}")
    
    print()
    
    # 爬取黄冈市教育局
    try:
        from crawl_huanggang import crawl_huanggang
        huanggang_jobs = crawl_huanggang()
        all_jobs.extend(huanggang_jobs)
    except Exception as e:
        print(f"爬取黄冈市教育局失败: {str(e)}")
    
    print()
    
    # 爬取孝感市教育局
    try:
        from crawl_xiaogan import crawl_xiaogan
        xiaogan_jobs = crawl_xiaogan()
        all_jobs.extend(xiaogan_jobs)
    except Exception as e:
        print(f"爬取孝感市教育局失败: {str(e)}")
    
    print()
    
    # 爬取搜狗微信搜索（公众号文章）
    try:
        from crawl_sogou_wechat import crawl_sogou_wechat
        sogou_jobs = crawl_sogou_wechat()
        all_jobs.extend(sogou_jobs)
    except Exception as e:
        print(f"爬取搜狗微信搜索失败: {str(e)}")
    
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
