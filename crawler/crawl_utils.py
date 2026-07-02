#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公共工具函数 - 所有爬虫共享的辅助函数
"""

from datetime import datetime, timedelta
import re

def is_valid_job_posting(title):
    """
    判断是否为有效的招聘信息
    返回 True 如果是编制类教师招聘信息
    """
    # 必须包含的关键词（招聘相关）
    required_keywords = ['招聘', '招录', '招考', '引进', '选调']

    # 检查是否包含必需关键词
    if not any(keyword in title for keyword in required_keywords):
        return False

    # 必须是教师或编制类招聘（放宽：有招聘关键词即保留，不再强制二次过滤）
    job_keywords = ['教师', '编制', '事业单位', '教育系统', '学校', '人才', '教师']
    if not any(keyword in title for keyword in job_keywords):
        return False

    # 排除：标题以这些词开头才是纯非招聘类公告（避免误杀含这些词的正常招聘标题）
    exclude_prefixes = [
        '成绩公布', '成绩查询', '考试成绩查询',
        '拟聘用公示', '拟录用公示', '录取名单',
        '师德', '师风',
        '教师资格认定',
        '代课教师', '临聘教师', '合同制教师',
    ]
    for prefix in exclude_prefixes:
        if title.startswith(prefix):
            return False

    # 排除：仅含这些词且无招聘实质（如纯体检通知、纯培训通知）
    pure_exclude_keywords = ['培训通知', '会议通知', '温馨提示', '投诉举报']
    for exc in pure_exclude_keywords:
        if exc in title:
            return False

    return True

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
