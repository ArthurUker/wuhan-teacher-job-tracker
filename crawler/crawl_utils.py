#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公共工具函数 - 所有爬虫共享的辅助函数
"""

from datetime import datetime, timedelta
import re


# ========== 公共过滤规则（供所有爬虫统一调用） ==========

# 需要直接排除的模式（标题匹配即丢弃）- 正则支持
BLOCK_PATTERNS = [
    # 高校/职业类
    '职业学院', '职业技术学院', '技工学校',
    '辅导员', '博士后', '博士研究生', '硕士研究生',
    '人才引进.*高校', '高校.*招聘.*教师',
    # 高校作为雇主的招聘（大学/学院 + 第X批/次/轮 + 招聘）
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

# 强指向教师词（命中即判为教师招聘）
STRONG_TEACHER_KEYWORDS = [
    '教师', '中学', '小学', '初中', '高中', '幼儿园',
    '附属中学', '附中', '附属学校', '附小',
    '学科教师', '教师岗', '师资',
    '公办学校', '民办学校', '实验学校',
    '教研室', '教育局招聘', '教育系统招聘',
    '学校',  # "学校"强指向教育机构招聘
    '校园招聘',  # 教育局/学校的校园招聘
]

# 泛化词（仅命中这些词、未命中强指向词时，不足以判定为教师招聘）
GENERIC_KEYWORDS = [
    '事业单位', '人才', '编制', '教育系统',
]

# 高校雇主关键词（出现在"招聘"之前则判定为高校招聘，需排除）
UNIVERSITY_EMPLOYER_KEYS = ['大学', '学院', '高校']

# 保留例外词（即使命中高校雇主关键词，含这些词仍保留）
UNIVERSITY_EXCEPTION_KEYS = [
    '赴高校', '附属中学', '附中', '附属学校', '大学附属', '附小',
    '教育局', '中小学',
]


def is_valid_job_posting(title):
    """
    判断是否为有效的教师招聘信息。
    采用分级判定逻辑，避免综合事业单位招聘被误收。

    判定流程：
    Step 1: 必须包含招聘动作词（招聘/招录/招考/引进/选调），否则 False
    Step 2: 命中 BLOCK_PATTERNS 直接判 False（高校职教、考试资料、培训等）
    Step 3: 命中强指向教师词（STRONG_TEACHER_KEYWORDS）直接判 True
    Step 4: 仅命中泛化词（GENERIC_KEYWORDS）但未命中强指向词，判 False
    Step 5: 高校雇主检查——"大学/学院/高校"出现在"招聘"之前且不含例外词，判 False

    返回 True 如果是编制类教师招聘信息，否则返回 False。
    """
    if not title:
        return False

    # Step 1: 必须包含招聘动作词（支持"招教师"等简写形式）
    action_keywords = ['招聘', '招录', '招考', '引进', '选调', '招']
    if not any(keyword in title for keyword in action_keywords):
        return False

    # Step 2: 命中排除模式（正则）直接丢弃
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, title):
            return False

    # Step 3: 命中强指向教师词 → 直接保留
    if any(keyword in title for keyword in STRONG_TEACHER_KEYWORDS):
        return True

    # Step 4: 仅命中泛化词（事业单位/人才/编制/学校等）但未命中强指向词 → 丢弃
    # 这说明标题描述的是综合事业单位招聘，而非专门的教师岗
    if any(keyword in title for keyword in GENERIC_KEYWORDS):
        # 命中了泛化词，但没有强指向词，说明不是专门的教师招聘
        return False

    # Step 5: 高校雇主检查
    # 判断逻辑：标题里"大学/学院/高校"出现在"招聘"之前，且不含保留例外词
    recruit_idx = title.find('招聘')
    if recruit_idx >= 0:
        prefix = title[:recruit_idx]
        is_univ_employer = any(k in prefix for k in UNIVERSITY_EMPLOYER_KEYS)
        is_keep = any(k in title for k in UNIVERSITY_EXCEPTION_KEYS)
        if is_univ_employer and not is_keep:
            return False

    # 已通过 Step 1 检查（有招聘动作词），但未命中任何教师相关关键词
    # 为安全起见，不再宽松放行，返回 False
    return False


def extract_teacher_tag(title):
    """
    根据标题内容动态生成标签（type 字段）。
    替换原先硬编码的 '教师招聘' 赋值。

    判定优先级（从上到下，命中即返回）：
    1. 含"幼儿园" → "幼教招聘"
    2. 含"小学"   → "小学教师招聘"
    3. 含"初中"   → "初中教师招聘"
    4. 含"高中"   → "高中教师招聘"
    5. 含"中学"   → "中学教师招聘"
    6. 含"编制"或"事业单位" → "编制教师招聘"
    7. 默认         → "教师招聘"
    """
    if not title:
        return '教师招聘'

    if '幼儿园' in title:
        return '幼教招聘'
    if '小学' in title:
        return '小学教师招聘'
    if '初中' in title:
        return '初中教师招聘'
    if '高中' in title:
        return '高中教师招聘'
    if '中学' in title or '附中' in title or '附属中学' in title:
        return '中学教师招聘'
    if '编制' in title or '事业单位' in title:
        return '编制教师招聘'

    return '教师招聘'


def is_recent_date(date_str, title='', months=6):
    """
    判断日期是否在最近 N 个月内
    months: 保留最近多少个月的信息
    title: 可选，当日期未知时从标题检测旧年份
    """
    try:
        # 如果日期未知，尝试从标题中检测旧年份
        if date_str == '未知日期':
            old_years = ['2018年', '2019年', '2020年', '2021年']
            if any(y in title for y in old_years):
                return False
            return True
        
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        
        return date_obj >= cutoff_date
    except:
        return True  # 解析失败时也保留


def extract_date_from_text(text):
    """从文本中提取日期"""
    if not text:
        return None
    
    # 尝试多种日期格式
    patterns = [
        r'(\d{4})[年\-/.](\d{1,2})[月\-/.](\d{1,2})',  # 2026年1月1日 / 2026-01-01
        r'(\d{4})(\d{2})(\d{2})',  # 20260101 (8位纯数字)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                try:
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                        return f"{year:04d}-{month:02d}-{day:02d}"
                except:
                    pass
    return None


def extract_date_from_element(link_element):
    """
    从链接元素的父/兄弟元素中提取日期
    常见模式：
    - <li><a>标题</a><span>2026-01-01</span></li>
    - <tr><td>2026-01-01</td><td><a>标题</a></td></tr>
    """
    if link_element is None:
        return None
    
    # 1. 查找父元素的文本（包含日期）
    parent = link_element.parent
    if parent:
        parent_text = parent.get_text(strip=True)
        date = extract_date_from_text(parent_text)
        if date:
            return date
    
    # 2. 查找兄弟 span/td 中的日期
    if parent:
        for sibling in parent.find_all(['span', 'td', 'em', 'i']):
            sibling_text = sibling.get_text(strip=True)
            date = extract_date_from_text(sibling_text)
            if date:
                return date
    
    # 3. 查找 tr 父元素中的所有 td
    tr_parent = link_element.find_parent('tr')
    if tr_parent:
        for td in tr_parent.find_all('td'):
            td_text = td.get_text(strip=True)
            date = extract_date_from_text(td_text)
            if date:
                return date
    
    return None


def build_full_url(href, base_url, target_url):
    """构建完整的URL"""
    if not href:
        return None
    
    if href.startswith('http'):
        return href
    elif href.startswith('//'):
        return 'https:' + href
    elif href.startswith('/'):
        return base_url + href
    elif href.startswith('./'):
        return target_url.replace('index.html', '') + href.replace('./', '')
    elif href.startswith('../'):
        return base_url + '/' + href.replace('../', '')
    else:
        # 相对路径
        if target_url.endswith('/'):
            return target_url + href
        else:
            return target_url.rsplit('/', 1)[0] + '/' + href


def retry_request(url, headers=None, timeout=30, retries=3, backoff=2):
    """
    带重试的 HTTP GET 请求，应对偶发网络错误（如 DNS 抖动、连接被重置）。
    对 IP 级封锁无效，但能恢复瞬时网络故障。
    """
    import requests
    import time

    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36'
        }

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return requests.get(url, headers=headers, timeout=timeout)
        except requests.exceptions.RequestException as e:
            last_err = e
            if attempt < retries:
                wait = backoff ** (attempt - 1)
                print(f"  请求失败({attempt}/{retries})，{wait}秒后重试: {e}")
                time.sleep(wait)
    raise last_err
