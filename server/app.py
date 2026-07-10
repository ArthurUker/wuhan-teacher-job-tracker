#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自托管后端服务（方案 B）：
  - 托管 frontend/ 静态前端
  - 提供 /api/jobs 读取最新招聘数据（data/jobs.json）
  - 使用 APScheduler 按计划后台运行爬虫与链接刷新，实现“一直运行、持续更新”
  - 通过 waitress 在生产环境提供 HTTP 服务（Nginx 反代到 127.0.0.1:8000）

计划（Asia/Shanghai）：
  爬取主爬虫 : 0:00 / 12:00   （对应原 GitHub Actions 的 UTC 0:00/12:00）
  刷新公众号 : 0:30 / 6:30 / 12:30 / 18:30
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime

from flask import Flask, send_from_directory, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

# ---- 路径解析（基于本文件位置，不受 cwd 影响）----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
DATA_FILE = os.path.join(BASE_DIR, 'data', 'jobs.json')
CRAWLER_DIR = os.path.join(BASE_DIR, 'crawler')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, 'server.log'), encoding='utf-8'),
    ],
)
logger = logging.getLogger('wuhan-job')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')


def run_crawler_script(script_name):
    """在 crawler/ 目录下运行爬虫脚本，并记录输出。"""
    logger.info('=== 启动脚本: %s ===', script_name)
    try:
        proc = subprocess.run(
            [sys.executable, script_name],
            cwd=CRAWLER_DIR,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        logger.info('脚本结束: %s (returncode=%d)', script_name, proc.returncode)
        if proc.stdout:
            logger.info('STDOUT(尾部):\n%s', proc.stdout[-2000:])
        if proc.stderr:
            logger.warning('STDERR(尾部):\n%s', proc.stderr[-2000:])
    except subprocess.TimeoutExpired:
        logger.error('脚本超时(>3600s): %s', script_name)
    except Exception:
        logger.exception('脚本执行异常: %s', script_name)


def crawl_job():
    run_crawler_script('main.py')


def refresh_job():
    run_crawler_script('refresh_wechat_links.py')


@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/api/jobs')
def api_jobs():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    # 不缓存，确保拿到最新数据
    resp = jsonify(data)
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/api/status')
def api_status():
    info = {
        'ok': True,
        'time': datetime.now().isoformat(timespec='seconds'),
        'jobs_count': _count_jobs(),
    }
    return jsonify(info)


def _count_jobs():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return len(json.load(f))
    except Exception:
        return -1


def init_scheduler():
    sched = BackgroundScheduler(timezone='Asia/Shanghai')
    # 主爬虫：每天 0:00 / 12:00（北京时间）
    sched.add_job(crawl_job, 'cron', hour='0,12', minute=0, id='crawl')
    # 刷新公众号链接：每天 0:30 / 6:30 / 12:30 / 18:30（北京时间）
    sched.add_job(refresh_job, 'cron', hour='0,6,12,18', minute=30, id='refresh')
    sched.start()
    logger.info('调度器已启动（Asia/Shanghai）：爬取 0/12点，刷新 0:30/6:30/12:30/18:30')


if __name__ == '__main__':
    init_scheduler()
    # 生产环境用 waitress；如需本地调试可改为 app.run(...)
    from waitress import serve
    logger.info('Wuhan Teacher Job Tracker 启动，监听 0.0.0.0:8000')
    serve(app, host='0.0.0.0', port=8000)
