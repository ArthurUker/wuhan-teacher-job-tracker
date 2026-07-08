#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序：运行所有爬虫并合并数据
"""

import sys
import os
import json
import re
from datetime import datetime, timedelta

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
    
    # 读取已有的数据（增量更新模式）
    data_dir = os.path.join(os.path.dirname(__file__), '../data')
    os.makedirs(data_dir, exist_ok=True)
    output_file = os.path.join(data_dir, 'jobs.json')

    existing_jobs = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_jobs = json.load(f)
            print(f"读取已有数据: {len(existing_jobs)} 条")
        except Exception as e:
            print(f"读取已有数据失败: {str(e)}，将从头开始")
            existing_jobs = []

    # 合并已有数据和新爬取的数据
    # 使用 (title, source) 作为唯一键去重，保留最新的
    # 对于微信公众号，每次爬取 URL 可能变化，用此键可避免重复
    seen = {}

    # 先放入已有数据
    for job in existing_jobs:
        key = (job['title'], job['source'])
        seen[key] = job

    # 再处理新数据（同名键会覆盖，新键会新增）
    new_count = 0
    updated_count = 0
    for job in all_jobs:
        key = (job['title'], job['source'])
        if key not in seen:
            new_count += 1
        else:
            # 已有记录，检查 URL 是否变化（如微信临时链接刷新）
            existing = seen[key]
            if existing.get('url') != job.get('url'):
                updated_count += 1
        seen[key] = job

    merged_jobs = list(seen.values())
    all_merged = merged_jobs  # 清理前全量，供低频源兜底使用

    # ===== 过期清理 =====
    # 非编制类：保留最近 6 个月；编制类：保留最近 12 个月；绝对上限 24 个月
    now = datetime.now()
    cutoff_regular = now - timedelta(days=365)   # 编制类 12 个月
    cutoff_other = now - timedelta(days=180)      # 非编制类 6 个月
    cutoff_absolute = now - timedelta(days=730)   # 绝对上限：任何条目不超过 24 个月

    def extract_date_for_cleanup(job):
        """为过期清理提取条目日期。优先用 date 字段，未知时从标题回填年份。"""
        date_str = job.get('date', '未知日期')

        if date_str != '未知日期':
            try:
                if len(date_str) == 7:
                    return datetime.strptime(date_str + '-01', '%Y-%m-%d')
                return datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                pass

        # 回填：从标题中提取年份（如 "2018年鄂城区农村义务教育..." → 2018-06-01）
        title = job.get('title', '')
        m = re.search(r'(20(1[5-9]|2[0-6]))年', title)
        if m:
            year = int(m.group(1))
            # 尝试同时提取月份
            mm = re.search(r'(\d{1,2})月', title)
            month = int(mm.group(1)) if mm else 6
            return datetime(year, min(month, 12), 1)

        # 完全无法判断 → 视为极旧（会被绝对上限清除），但不被普通 cutoff 删
        return None

    expired_count = 0
    kept_jobs = []
    for job in merged_jobs:
        is_regular = '编制' in job.get('type', '')
        job_date = extract_date_for_cleanup(job)

        cutoff = cutoff_regular if is_regular else cutoff_other

        if job_date is None:
            # 标题也无年份线索 → 保留（可能是近期发布但格式特殊）
            kept_jobs.append(job)
            continue

        if job_date < cutoff_absolute:
            # 超过绝对上限（24 个月），无论编制与否一律清除
            expired_count += 1
            continue

        if job_date >= cutoff:
            kept_jobs.append(job)
        else:
            expired_count += 1

    merged_jobs = kept_jobs
    print(f"过期清理: 删除 {expired_count} 条过期数据")

    # ===== 低频源兜底 =====
    # 某些政府教育站点发招聘很少，最新一条也超过清理期限，会被全部删光、长期空白，
    # 让人误以为爬虫故障。若某来源清理后为空，则保留其清理前的最新 1 条。
    surviving_sources = {j.get('source') for j in merged_jobs}
    emptied = {}
    for job in all_merged:
        src = job.get('source')
        if src not in surviving_sources:
            emptied.setdefault(src, []).append(job)
    for src, items in emptied.items():
        if not items:
            continue
        items.sort(
            key=lambda x: x.get('date') if x.get('date') != '未知日期' else '2000-01-01',
            reverse=True,
        )
        merged_jobs.append(items[0])
        print(f"低频源兜底: 为「{src}」保留最新 1 条: {items[0].get('title', '')[:40]}")

    # 按日期排序
    merged_jobs.sort(key=lambda x: x['date'] if x['date'] != '未知日期' else '2000-01-01', reverse=True)

    # 保存数据
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_jobs, f, ensure_ascii=False, indent=2)

    print(f"爬取完成！")
    print(f"本次爬取: {len(all_jobs)} 条")
    print(f"新增条目: {new_count} 条")
    print(f"更新条目: {updated_count} 条（如链接刷新）")
    print(f"合并后共: {len(merged_jobs)} 条信息")
    print(f"数据已保存到: {output_file}")
    print("=" * 50)

if __name__ == '__main__':
    main()
