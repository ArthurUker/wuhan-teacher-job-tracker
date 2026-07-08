#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据清洗脚本 - 对已有的 jobs.json 重新应用过滤规则
使用 crawl_utils.py 中的统一过滤函数
"""

import json
import sys
import os
import random
import re
from datetime import datetime, timedelta

# 添加当前目录到 path，以便导入 crawl_utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawl_utils import is_valid_job_posting, extract_teacher_tag


def clean_jobs():
    """清洗 jobs.json 数据：过滤 + 去重 + 重打标签"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_file = os.path.join(base_dir, 'data', 'jobs.json')
    output_file = input_file

    print("=" * 60)
    print("数据清洗开始（使用 crawl_utils.py 统一过滤规则）")
    print("=" * 60)

    # 读取原始数据
    with open(input_file, 'r', encoding='utf-8') as f:
        jobs = json.load(f)

    original_count = len(jobs)
    print(f"原始条目总数：{original_count} 条")

    # ===== Step 1: 过滤无效招聘 =====
    filtered = []
    removed_by_filter = []

    for job in jobs:
        title = job.get('title', '')
        if is_valid_job_posting(title, source=job.get('source')):
            filtered.append(job)
        else:
            removed_by_filter.append(title)

    print(f"Step1 过滤后：{len(filtered)} 条（清除 {len(removed_by_filter)} 条非教师招聘）")

    # ===== Step 2: 按标题去重（保留最新的一条）=====
    seen_titles = {}
    for job in filtered:
        title = job.get('title', '').strip()
        if not title:
            continue
        if title not in seen_titles:
            seen_titles[title] = job
        else:
            # 保留有日期更新的、或字段更完整的那条
            existing = seen_titles[title]
            existing_date = existing.get('date') or existing.get('pubDate') or ''
            new_date = job.get('date') or job.get('pubDate') or ''
            if new_date >= existing_date:
                seen_titles[title] = job

    deduped = list(seen_titles.values())
    dupe_count = len(filtered) - len(deduped)
    print(f"Step2 去重后：{len(deduped)} 条（去除 {dupe_count} 条重复数据）")

    # ===== Step 2.5: 过期清理（与 main.py 保持一致的逻辑）=====
    # 非编制类：保留最近 6 个月；编制类：保留最近 12 个月；绝对上限 24 个月
    now = datetime.now()
    cutoff_regular = now - timedelta(days=365)
    cutoff_other = now - timedelta(days=180)
    cutoff_absolute = now - timedelta(days=730)

    def extract_date_for_cleanup(job):
        """为过期清理提取条目日期，未知时从标题回填年份。"""
        date_str = job.get('date', '未知日期')
        if date_str != '未知日期':
            try:
                if len(date_str) == 7:
                    return datetime.strptime(date_str + '-01', '%Y-%m-%d')
                return datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                pass
        title = job.get('title', '')
        m = re.search(r'(20(1[5-9]|2[0-6]))年', title)
        if m:
            year, month = int(m.group(1)), 6
            mm = re.search(r'(\d{1,2})月', title)
            if mm:
                month = min(int(mm.group(1)), 12)
            return datetime(year, month, 1)
        return None

    cleaned_by_age = []
    expired_by_age = 0
    for job in deduped:
        is_regular = '编制' in job.get('type', '')
        job_date = extract_date_for_cleanup(job)
        cutoff = cutoff_regular if is_regular else cutoff_other

        if job_date is None:
            cleaned_by_age.append(job)
            continue
        if job_date < cutoff_absolute:
            expired_by_age += 1
            continue
        if job_date >= cutoff:
            cleaned_by_age.append(job)
        else:
            expired_by_age += 1

    deduped = cleaned_by_age
    print(f"Step2.5 过期清理后：{len(deduped)} 条（清除 {expired_by_age} 条过期数据）")

    # ===== Step 3: 重新打标签 + 排序（按日期降序）=====
    cleaned = []
    for job in deduped:
        title = job.get('title', '')
        job['type'] = extract_teacher_tag(title)
        cleaned.append(job)

    # 按日期降序排列（最新的在前）
    cleaned.sort(
        key=lambda x: x.get('date') or x.get('pubDate') or '',
        reverse=True,
    )

    print("=" * 60)
    print(f"清洗完成：")
    print(f"  原始总数：{original_count} 条")
    print(f"  过滤清除：{len(removed_by_filter)} 条")
    print(f"  去重清除：{dupe_count} 条")
    print(f"  最终保留：{len(cleaned)} 条")
    print("=" * 60)

    # 输出被过滤掉的条目
    if removed_by_filter:
        print("\n【被过滤的非教师招聘】共 {} 条：".format(len(removed_by_filter)))
        for i, title in enumerate(removed_by_filter[:20], 1):
            print("  {}. {}".format(i, title))
        if len(removed_by_filter) > 20:
            print("  ... 还有 {} 条".format(len(removed_by_filter) - 20))

    # 写回文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"\n已保存到: {output_file}")

    # 按来源统计
    source_stats = {}
    for job in cleaned:
        src = job.get('source', '未知')
        source_stats[src] = source_stats.get(src, 0) + 1
    print("\n按来源统计：")
    for src, cnt in sorted(source_stats.items(), key=lambda x: -x[1]):
        print("  {}: {} 条".format(src, cnt))

    # 随机抽样 10 条确认
    if cleaned:
        sample_size = min(10, len(cleaned))
        sampled = random.sample(cleaned, sample_size)
        print(f"\n随机抽样 {sample_size} 条保留条目（供人工确认）：")
        for i, job in enumerate(sampled, 1):
            print(f"  {i}. [{job.get('type', '未知')}] {job.get('title', '')}")


if __name__ == '__main__':
    clean_jobs()
