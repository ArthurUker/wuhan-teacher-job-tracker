# 武汉教师招聘信息追踪系统

🎓 实时监控武汉市及湖北省中小学教师招聘信息，自动爬取、去重、过滤，并通过 Web 界面集中展示。

> 当前部署形态：**自托管**（自有服务器上 Flask 常驻进程 + APScheduler 定时爬取），
> 不再依赖 GitHub Pages / GitHub Actions 额度。设计细节见 [docs/DESIGN.md](docs/DESIGN.md)。

## 功能特点

- ✅ 多源自动爬取：市/区教育局、人社局、省考试院、微信公众号（搜狗）
- ✅ 智能过滤：排除高校招教、事业单位综合招聘、公示/结果类等非中小学教师招聘
- ✅ 自动去重与过期清理（按发布日期，带标题年份回填）
- ✅ 微信公众号临时链接自动刷新为永久链接
- ✅ 常驻后台按计划更新，"一直运行、持续更新"
- ✅ 友好的 Web 界面：来源筛选、分页、卡片/列表视图

## 技术栈

- **爬虫**：Python + requests + BeautifulSoup + lxml + Playwright（搜狗微信）
- **后端**：Flask + APScheduler + waitress
- **前端**：原生 HTML + CSS + JavaScript（无框架）
- **部署**：Ubuntu + systemd + Nginx（自托管）

## 数据来源

### 武汉市及各区

1. **武汉市教育局官网** - https://jyj.wuhan.gov.cn/zwdt/tsgg/
2. **武汉市人力资源和社会保障局** - http://rsj.wuhan.gov.cn/sy_20/jgzydwzp/
3. **武汉东湖新技术开发区（光谷）** - https://www.wehdz.gov.cn/2022/zfxxgk/fdzdgk/zkzl/
   - ⭐⭐⭐⭐⭐ 高价值：独立招聘体系，待遇好，招聘频繁
4. **汉阳区人民政府（教育局）** - https://www.hanyang.gov.cn/zwgk_38/xxgkml/zlzk/
   - ⭐⭐⭐⭐ 高价值

### 武汉周边城市（1小时生活圈）

5. **鄂州市教育局** - https://jyj.ezhou.gov.cn/xxgk/zc/gsgg/
   - ⭐⭐⭐⭐ 高价值：距离武汉仅60km，数据丰富
6. **黄石市教育局** - http://jyj.huangshi.gov.cn/dt/zytz/index.html
   - ⭐⭐⭐⭐ 高价值：距离武汉80km
7. **黄冈市教育局** - https://jyj.hg.gov.cn/
   - ⭐⭐⭐⭐ 高价值：教育强市，有"优师计划"
8. **蔡甸区人民政府（教育局）** - https://www.caidian.gov.cn/qgdwxxgk/qjbm/jyj_21923/zkly/
   - ⭐⭐⭐ 中等价值
9. **孝感市教育局** - https://jyj.xiaogan.gov.cn/c/xgsjyj/zkly/
   - ⭐⭐⭐ 中等价值：有 WAF 防护

### 省级数据源

10. **湖北省教育考试院** - http://www.hbea.edu.cn/html/jszp/index.html

### 微信公众号（搜狗微信搜索）

11. **搜狗微信搜索** - https://weixin.sogou.com/
    - ⭐⭐⭐⭐⭐ 高价值：覆盖全平台公众号文章，时效性最强
    - 搜索关键词：武汉/湖北/黄石/鄂州/黄冈/孝感 教师招聘

## 项目结构

```
wuhan-teacher-job-tracker/
├── crawler/                        # 爬虫脚本
│   ├── main.py                     # 主程序：爬取 + 合并 + 去重 + 过期清理
│   ├── refresh_wechat_links.py     # 公众号链接刷新（临时链接 → 永久链接）
│   ├── crawl_utils.py              # 过滤/去重等公共逻辑
│   ├── crawl_*.py                  # 各数据源爬虫
│   └── requirements.txt            # 爬虫依赖
├── data/
│   └── jobs.json                   # 招聘数据（单一数据源：爬虫写，前端读）
├── frontend/                       # 前端页面
│   ├── index.html
│   ├── style.css
│   └── app.js                      # 从 /api/jobs 读数据并渲染
├── server/                         # 自托管后端（Flask + APScheduler）
│   ├── app.py                      # 托管前端 + /api/jobs + 定时爬取/刷新
│   ├── requirements.txt            # 后端依赖
│   ├── nginx-wuhan-job.conf        # Nginx 反代配置
│   └── setup.sh                    # 一键部署脚本
├── docs/                           # 开发文档
│   ├── README.md                   # 文档索引
│   └── DESIGN.md                   # 自托管设计方案与架构图
└── .github/workflows/              # GitHub Actions（定时已关闭，仅手动备用）
    ├── crawl.yml
    └── refresh-wechat.yml
```

## 快速开始

### 一、服务器部署（推荐）

在 Linux 服务器（Ubuntu 22.04 + systemd + Nginx）上常驻运行：

```bash
# 1) 克隆仓库
git clone https://github.com/ArthurUker/wuhan-teacher-job-tracker.git ~/wuhan-teacher-job-tracker
cd ~/wuhan-teacher-job-tracker

# 2) 一键部署（装依赖 / 建 venv / 装 Playwright / 注册 systemd / 配置 Nginx）
sudo bash server/setup.sh
```

完成后访问 `http://<服务器公网IP>/`（**记得在云安全组放通 80 端口**）。

一键脚本做了：安装系统依赖与浏览器库 → 创建 Python 虚拟环境并安装 `crawler` + `server`
依赖 → 安装 Playwright Chromium → 注册并启动 `wuhan-job` systemd 服务 → 配置 Nginx 反代。

### 二、本地开发运行

```bash
# 安装依赖
pip install -r crawler/requirements.txt
pip install -r server/requirements.txt
python -m playwright install chromium

# 启动后端（默认 0.0.0.0:8000，内置托管前端 + 定时任务）
python server/app.py
```

然后访问 http://localhost:8000 。
如只想手动跑一次爬虫：`cd crawler && python main.py`。

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 前端页面 |
| GET | `/api/jobs` | 返回全部招聘数据（JSON 数组，`no-store` 不缓存） |
| GET | `/api/status` | 健康检查：当前时间与数据条数 |

## 定时计划（北京时间 Asia/Shanghai）

| 任务 | 脚本 | 时刻 |
|---|---|---|
| 主爬虫 | `crawler/main.py` | 每天 **0:00 / 12:00** |
| 刷新公众号链接 | `crawler/refresh_wechat_links.py` | 每天 **0:30 / 6:30 / 12:30 / 18:30** |

均由 `server/app.py` 中的 APScheduler 调度，无需 GitHub Actions。

## 运维常用命令

```bash
# 查看实时日志
sudo journalctl -u wuhan-job -f

# 重启 / 停止 / 启动服务
sudo systemctl restart wuhan-job
sudo systemctl stop wuhan-job
sudo systemctl start wuhan-job

# 更新代码后重启（依赖有变更时重跑 setup.sh）
git pull && sudo systemctl restart wuhan-job

# 手动触发一次爬取
cd ~/wuhan-teacher-job-tracker/crawler && ../venv/bin/python main.py
```

- 数据文件：`data/jobs.json`
- 服务日志：`logs/server.log` 或 `journalctl -u wuhan-job`
- 修改端口：编辑 `server/nginx-wuhan-job.conf` 的 `listen`，然后 `sudo nginx -t && sudo systemctl restart nginx`

## GitHub Actions（备用）

两个工作流（`crawl.yml`、`refresh-wechat.yml`）的定时触发已注释关闭，仅保留
`workflow_dispatch` 手动触发，作为自托管故障时的临时备用数据源。如需恢复定时，
取消对应 `schedule` 段注释即可。

## 注意事项

- 爬虫仅用于学习和个人使用，请遵守目标网站的 robots.txt。
- 如遇反爬措施（如搜狗验证码），可能需要更新爬虫策略。
- 部分政府站点对境外 IP 不可达；使用国内服务器可提升可用性。

## 许可证

MIT License
