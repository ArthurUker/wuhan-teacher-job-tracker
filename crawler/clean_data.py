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

# 添加当前目录到 path，以便导入 crawl_utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawl_utils import is_valid_job_posting, extract_teacher_tag


def clean_jobs():
    """清洗 jobs.json 数据"""
    input_file = '../data/jobs.json'
    output_file = '../data/jobs.json'

    print("=" * 60)
    print("数据清洗开始（使用 crawl_utils.py 统一过滤规则）")
    print("=" * 60)

    # 读取原始数据
    with open(input_file, 'r', encoding='utf-8') as f:
        jobs = json.load(f)

    print(f"清洗前条目总数：{len(jobs)} 条")

    # 过滤 + 重新打标签
    cleaned = []
    removed = []

    for job in jobs:
        title = job.get('title', '')
        if is_valid_job_posting(title):
            # 重新生成标签（动态）
            job['type'] = extract_teacher_tag(title)
            cleaned.append(job)
        else:
            removed.append(title)

    print("=" * 60)
    print(f"清洗完成：")
    print(f"  清洗后保留：{len(cleaned)} 条")
    print(f"  被清除：{len(removed)} 条")
    print("=" * 60)

    # 输出被清除的条目（供人工抽样核验）
    if removed:
        print("\n被清除的条目标题列表：")
        for i, title in enumerate(removed, 1):
            print(f"  {i}. {title}")

    # 写回文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"\n已保存到: {output_file}")

    # 随机抽样 10 条确认
    if cleaned:
        sample_size = min(10, len(cleaned))
        sampled = random.sample(cleaned, sample_size)
        print(f"\n随机抽样 {sample_size} 条保留条目（供人工确认）：")
        for i, job in enumerate(sampled, 1):
            print(f"  {i}. [{job.get('type', '未知')}] {job.get('title', '')}")


if __name__ == '__main__':
    clean_jobs()
