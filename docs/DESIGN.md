# 自托管部署设计方案（方案 B：Flask 常驻进程）

> 适用环境：腾讯云 CVM，Ubuntu 22.04.5 LTS（x86_64），systemd，无域名，公网 IP 直接访问。
> 目标：把"网页 + 爬虫"从 GitHub Pages / GitHub Actions 迁移到自有服务器，常驻运行、不被 Actions 额度限制。

## 1. 整体架构

```
┌─────────────── 腾讯云 CVM (Ubuntu 22.04) ───────────────┐
│                                                          │
│   浏览器 http://<公网IP>/                                 │
│        │ :80                                              │
│        ▼                                                 │
│   ┌─────────┐   127.0.0.1:8000   ┌────────────────────┐  │
│   │  Nginx  │ ──── 反代 ─────────▶│  Flask + waitress  │  │
│   │ (入口)  │                    │  server/app.py     │  │
│   └─────────┘                    └─────────┬──────────┘  │
│                                            │             │
│                       ┌────────────────────┼──────────┐  │
│                       ▼                    ▼          ▼  │
│               托管 frontend/         GET /api/jobs   APScheduler │
│              (index.html 等)         读 data/jobs.json  定时后台跑爬虫 │
│                                            │             │
│                                            ▼             │
│                                   data/jobs.json (单一数据源) │
│                                            ▲             │
│                       subprocess(venv):  crawler/main.py   │
│                                         crawler/refresh_*.py │
└──────────────────────────────────────────────────────────┘
```

**一句话**：一个常驻 Flask 进程既托管网页、又按计划后台跑爬虫；Nginx 只做 80 端口反代。GitHub 退化为"纯代码仓库 + 手动备用 workflow"。

## 2. 组件职责

| 组件 | 文件 | 职责 |
|---|---|---|
| 后端服务 | `server/app.py` | 托管前端；`/api/jobs` 读数据；`/api/status` 健康检查；APScheduler 定时调用爬虫 |
| 定时调度 | `server/app.py`（APScheduler，`Asia/Shanghai`） | 主爬虫 `0:00/12:00`；刷新公众号 `0:30/6:30/12:30/18:30` |
| 爬虫层 | `crawler/main.py`、`crawler/refresh_wechat_links.py` | 复用现有逻辑，由后端以 venv python 子进程调用，写 `data/jobs.json` |
| 数据层 | `data/jobs.json` | 单一本地数据源：前端只读，爬虫只写 |
| 运行保障 | `server/setup.sh` + systemd + Nginx | venv 隔离、Playwright 安装、systemd 保活（`Restart=on-failure`）、Nginx 反代 |

## 3. 数据流

- **看数据**：浏览器 → Nginx:80 → Flask:8000 → `GET /api/jobs` → `data/jobs.json`
- **自动更新**：APScheduler 到点 → `subprocess(venv/python crawler/main.py)`（cwd=crawler）→ 写 `data/jobs.json` → 下次刷新页面见新数据

## 4. 与旧方案对比

| 维度 | 旧（GitHub） | 新（自托管） |
|---|---|---|
| 网页 | GitHub Pages | 自有服务器 Flask 托管 |
| 定时抓取 | GitHub Actions cron | 本机 APScheduler |
| 手动抓取 | Cloudflare Worker 触发 | 已移除（按需求） |
| 数据落地 | 提交到 GitHub 仓库 | 写本机 `data/jobs.json` |
| 资源限制 | 受 Actions 额度限制 | 无限制，一直运行 |

## 5. 关键设计决策

1. **单进程 vs 前后端分离**：选单进程（调度内嵌后端），一个 systemd 单元搞定，运维最简单。
2. **JSON 文件 vs 数据库**：保持 `jobs.json`，零迁移、前端不用改。
3. **调度时区**：显式 `Asia/Shanghai`，对齐原北京时刻（原 GitHub UTC 0:00/12:00 = 北京 8:00/20:00）。
4. **并发读写原子性**：爬虫用 `json.dump` 直接覆盖（非原子）。读取端已做容错（异常返回空/500）。风险极低；若要更稳可改成"先写临时文件再 `rename` 原子替换"。
5. **GitHub Actions 定时已关闭**，`workflow_dispatch` 保留作手动备用，不再耗额度。

## 6. 待确认事项（当前默认值）

| 项 | 当前默认 | 备注 |
|---|---|---|
| 监听端口 | Nginx `listen 80` | 若安全组不便开 80，可改 `8080`（改 `server/nginx-wuhan-job.conf`） |
| 抓取频率 | 主爬虫 12h / 刷新 6h | 可更密（如主爬虫每小时） |
| 手动触发接口 | 不提供 | 如需自测可加带鉴权的 `/api/crawl` |
| HTTPS | 暂不做（无域名，HTTP） | 有域名后改 `server_name` + certbot |
| 数据备份 | 不自动备份 | 可选：定时 `git push` 回 GitHub 作异地备份 |

## 7. 部署概览（详细见 README）

```bash
git clone https://github.com/ArthurUker/wuhan-teacher-job-tracker.git ~/wuhan-teacher-job-tracker
cd ~/wuhan-teacher-job-tracker
sudo bash server/setup.sh
# 腾讯云安全组放通 80 端口 → 访问 http://<公网IP>/
```

- 日志：`sudo journalctl -u wuhan-job -f`
- 数据文件：`~/wuhan-teacher-job-tracker/data/jobs.json`
- 重启：`sudo systemctl restart wuhan-job`
