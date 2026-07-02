#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据清洗脚本 - 对已有的 jobs.json 重新应用过滤规则
"""

import json
import re

# ========== 过滤规则（与 crawl_sogou_wechat.py 保持一致）==========

# 需要保留的模式（即使包含"学院/大学"，也保留）
KEEP_PATTERNS = [
    '赴高校', '附属中学', '附中', '附属学校', '大学附属', '附小',
    '教育局', '事业单位', '公招', '编制', '公开招聘', '教师公开招聘',
    '中小学', '中学', '小学', '初中', '高中',
]

# 需要直接排除的模式（标题匹配即丢弃）
BLOCK_PATTERNS = [
    # 高校/职业类
    '职业学院', '职业技术学院', '技工学校',
    '辅导员', '博士后', '博士研究生', '硕士研究生',
    '人才引进.*高校', '高校.*招聘.*教师',
    r'.*大学.*第\d+.*[批次轮次].*招聘',
    r'.*学院.*第\d+.*[批次轮次].*招聘',
    r'.*大学.*公开招聘.*公告',
    r'.*学院.*公开招聘.*公告',
    # 考试资料/真题/试题（非招聘公告）
    '真题', '试题', '试卷', '题库', '练习题',
    '历年真题', '模拟题', '押题',
    '笔试.*资料', '面试.*资料', '备考.*资料',
    '考试资料', '备考资料', '复习资料',
    # 培训/课程
    '培训课程', '网课', '直播课', '录播课',
    '辅导班', '培训班', '冲刺班',
    # 资料/下载
    '资料下载', '免费领取', '打包下载',
    # 其他非招聘内容
    '考试大纲', '考点汇总', '知识点',
]

# 高校雇主关键词
UNIVERSITY_EMPLOYER_KEYS = ['大学', '学院']


def should_keep_article(title):
    """
    判断是否为中小学/公立学校教师招聘信息。
    返回 True 表示保留，False 表示丢弃。

    过滤优先级：
    1. 先检查排除模式（BLOCK_PATTERNS）- 直接丢弃
    2. 再检查是否为高校作为雇主的招聘 - 丢弃
    3. 最后检查保留模式（KEEP_PATTERNS）- 保留
    4. 默认保留
    """
    if not title:
        return False

    # 1. 先检查排除模式（正则）- 匹配即丢弃
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, title):
            return False

    # 2. 检查是否为高校作为雇主的招聘
    recruit_positions = [m.start() for m in re.finditer('招聘', title)]
    for recruit_idx in recruit_positions:
        prefix = title[:recruit_idx]
        # 去掉搜索关键词前缀，检查剩余部分是否包含大学/学院
        stripped = prefix
        for prefix_keyword in ['武汉教师', '湖北教师', '黄石教师', '鄂州教师',
                               '孝感教师', '黄冈教师', '咸宁教师', '武汉事业单位']:
            stripped = stripped.replace(prefix_keyword, '')
        for key in UNIVERSITY_EMPLOYER_KEYS:
            if key in stripped:
                return False

    # 3. 再检查保留模式
    for pattern in KEEP_PATTERNS:
        if pattern in title:
            return True

    # 4. 默认保留
    return True


def clean_jobs():
    """清洗 jobs.json 数据"""
    input_file = '../data/jobs.json'
    output_file = '../data/jobs.json'

    print("=" * 60)
    print("数据清洗开始")
    print("=" * 60)

    # 读取原始数据
    with open(input_file, 'r', encoding='utf-8') as f:
        jobs = json.load(f)

    print(f"原始数据：{len(jobs)} 条")

    # 过滤
    cleaned = []
    removed = []

    for job in jobs:
        title = job.get('title', '')
        if should_keep_article(title):
            cleaned.append(job)
        else:
            removed.append(title)
            print(f"  ❌ 移除: {title[:80]}")

    print("=" * 60)
    print(f"清洗完成：")
    print(f"  保留：{len(cleaned)} 条")
    print(f"  移除：{len(removed)} 条")
    print("=" * 60)

    # 写回文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"\n已保存到: {output_file}")


if __name__ == '__main__':
    clean_jobs()
