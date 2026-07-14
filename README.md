# 武汉教师招聘信息追踪系统

> 详细设计文档。架构/部署/运维以**自托管**形态为准（自有服务器常驻运行，不依赖 GitHub Actions 额度）。
> 设计细节另见 `docs/DESIGN.md`。

---

## 1. 系统概述

### 1.1 业务定位
自动采集并集中展示**武汉市及湖北省中小学教师招聘信息**，覆盖市/区教育局、人社局、省考试院官网以及微信公众号（搜狗微信搜索），帮助用户第一时间获取招聘动态、报名截止时间与原文链接。

### 1.2 目标用户
- 湖北省（尤其武汉及周边 1 小时生活圈）的中小学教师、应届师范生、备考人员；
- 关注编制/校招/合同制等各类招聘渠道的求职者。

### 1.3 部署形态
| 维度 | 说明 |
|---|---|
| 形态 | 自托管单机服务（非 SaaS、非多租户） |
| 运行时 | 单个常驻进程：Flask + APScheduler，由 systemd 保活 |
| 接入 | Nginx 反向代理（80 端口）→ 本机 `127.0.0.1:8000` |
| 数据 | 本地文件 `data/jobs.json`（单一数据源） |
| 调度 | 进程内 APScheduler 按计划后台跑爬虫，无需外部 CI |
| GitHub | 仅作代码仓库；Actions 定时已关闭，仅保留手动备用 |

---

## 2. 技术栈总览

| 层 | 技术 | 用途 |
|---|---|---|
| 爬虫 | Python 3.10、requests、BeautifulSoup4、lxml | 抓取与解析各官网 |
| 反爬/动态页 | Playwright（Chromium） | 搜狗微信等需渲染/跳转的页面 |
| 后端 | Flask、APScheduler、waitress、tzdata | HTTP 服务、定时调度、生产级 WSGI |
| 前端 | 原生 HTML + CSS + JavaScript（无框架） | 展示、筛选、分页 |
| 反向代理 | Nginx（可选 Caddy） | 80 端口接入、静态反代 |
| 进程管理 | systemd | 服务保活、开机自启 |
| 数据存储 | JSON 文件（`data/jobs.json`） | 招聘数据（非关系型数据库） |

---

## 3. 系统架构图

### 3.1 部署拓扑
```
                         ┌──────────────── 服务器 (Ubuntu 22.04) ────────────────┐
                         │                                                      │
  浏览器 (http://IP/)    │   80           127.0.0.1:8000                       │
     │                   │  ┌────────┐     ┌─────────────────────────────────┐  │
     ├──────────────────▶│─▶│ Nginx  │────▶│ Flask + waitress (server/app.py)│  │
     │  GET /            │  └────────┘     │  • 托管 frontend/               │  │
     │  GET /api/jobs    │                 │  • GET /api/jobs → jobs.json    │  │
     │                   │                 │  • APScheduler (后台定时)        │  │
     │                   │                 └───────┬───────────────┬─────────┘  │
     │                   │                         │               │            │
     │                   │                         ▼               ▼            │
     │                   │                  data/jobs.json   subprocess(venv)   │
     │                   │                  (单一数据源)    crawler/main.py    │
     │                   │                                   crawler/refresh_*.py │
     │                   │                                                       │
                         └───────────────────────────────────────────────────────┘
```

### 3.2 分层说明
- **前端层**：浏览器加载 `frontend/index.html`，通过 `fetch('/api/jobs')` 拉取数据并本地渲染。
- **反向代理层**：Nginx 终结 80 端口 HTTP，反代到后端 8000 端口。
- **应用层**：Flask 同时承担"静态托管 + API + 调度器"三角色（单进程）。
- **数据层**：`data/jobs.json` 由爬虫写、由 API 读，是唯一的真相源。
- **采集层**：APScheduler 到点以子进程方式调用 `crawler/main.py` / `refresh_wechat_links.py`。

---

## 4. 数据模型设计

> ⚠️ 本系统**不使用关系型数据库**，数据落地为单个 JSON 文件 `data/jobs.json`（JSON 数组）。
> 因此没有传统意义上的 ER 图、表/外键/索引；本节给出**数据对象 Schema** 与去重策略。

### 4.1 存储结构
```
data/jobs.json  →  Array<Job>
```
- 编码：UTF-8，缩进 2 空格。
- 去重键：`(title, source)` —— 同名同源视为同一条，新抓取覆盖旧值（如链接刷新）。

### 4.2 Job 对象字段定义

| 字段 | 类型 | 必含 | 说明 | 示例 |
|---|---|---|---|---|
| `title` | string | 是 | 招聘标题 | `"2026年武汉市东西湖区教师招聘公告"` |
| `url` | string | 是 | 原文链接（官网原文或微信永久/临时链接） | `"https://..."` |
| `source` | string | 是 | 数据来源名称 | `"武汉市教育局"` / `"微信公众号"` |
| `date` | string | 是 | 日期，`YYYY-MM-DD` 或 `"未知日期"` | `"2026-03-12"` / `"未知日期"` |
| `type` | string | 否* | 招聘类别标签 | `"编制"` / `"非编制"` / `"公众号文章"` |
| `title_date` | string | 否 | 从标题中提取的日期 | `"2026-03-12"` |
| `publish_time` | string | 否 | 公众号发布时间 | `"2026-03-10"` |
| `deadline` | string | 否 | 报名/截止日期 | `"2026-03-20"` |
| `urgent` | bool | 否 | 是否临近截止（前端标红） | `true` |
| `account_name` | string | 否 | 公众号名称（仅微信来源） | `"武汉教师招聘"` |
| `summary` | string | 否 | 摘要（微信来源） | `"..."` |

> *`type` 对官网来源由 `extract_teacher_tag(title)` 推导（如含"编制"则标记）；微信来源固定为 `"公众号文章"`。

### 4.3 生命周期与清理
- **合并**：每次爬虫运行后，新数据与 `jobs.json` 现有数据按 `(title, source)` 合并。
- **过期清理**（`main.py`）：非编制保留近 6 个月、编制保留近 12 个月、绝对上限 24 个月；`date` 为"未知日期"时从标题年份回填。
- **低频源兜底**：若某来源清理后为空，保留其最新 1 条，避免界面长期空白。

### 4.4 关于"索引/外键"
- 全文一次性读入前端内存后做筛选/分页，**服务端无查询引擎、无索引**。
- 关系：仅 `(title, source)` 逻辑主键用于去重；无外键（单文件、无关联表）。

---

## 5. API 接口文档

基础地址：`http://<服务器IP>/`（由 Nginx 反代到 Flask:8000）。
**认证方式：无（公开只读）**，见第 7 节。

| # | 方法 | 路径 | 说明 |
|---|---|---|---|
| 1 | GET | `/` | 前端页面（静态 `index.html`） |
| 2 | GET | `/api/jobs` | 获取全部招聘数据 |
| 3 | GET | `/api/status` | 健康检查 |

### 5.1 `GET /api/jobs`
- 请求：无参数（URL 可带 `?t=<时间戳>` 防浏览器缓存，后端忽略）。
- 响应：`200 OK`，`Content-Type: application/json`，`Cache-Control: no-store`
```json
[
  {
    "title": "2026年武汉市教师招聘公告",
    "url": "https://jyj.wuhan.gov.cn/xxx",
    "source": "武汉市教育局",
    "date": "2026-03-12",
    "type": "编制",
    "title_date": "",
    "publish_time": "未知日期",
    "deadline": "",
    "urgent": false,
    "account_name": "未知公众号"
  }
]
```
- 错误：`500`，当 `jobs.json` 不存在或 JSON 损坏时返回 `{"error": "..."}`。

### 5.2 `GET /api/status`
- 响应：`200 OK`
```json
{ "ok": true, "time": "2026-07-14T17:40:00", "jobs_count": 213 }
```

---

## 6. 前端模块设计

> 原生 JS 单页应用，**无前端路由、无状态管理库**（数据量小，全部在内存中处理）。

### 6.1 页面结构（单页）
- 顶部：标题 + 副标题
- 控制区：刷新数据按钮
- 来源筛选卡片（`sourceCards`）
- 统计条：总条数 + 最后更新时间
- 每页/视图控制：每页条数、卡片/列表视图切换
- 职位列表（`jobList`）
- 分页导航（`paginationNav`）

### 6.2 状态（模块级变量，`frontend/app.js`）
| 变量 | 含义 |
|---|---|
| `allJobs` | 全量数据 |
| `filteredJobs` | 当前筛选结果 |
| `activeSource` | 选中的来源（""=全部） |
| `currentPage` / `perPage` | 分页状态 |
| `currentView` | `"card"` / `"list"` |

### 6.3 关键函数划分
| 函数 | 职责 |
|---|---|
| `loadJobs()` | 拉取 `/api/jobs` 并渲染 |
| `renderSourceCards()` | 渲染来源筛选卡片 |
| `filterJobs()` | 按来源 + 排除高校招聘过滤 |
| `isUniversityRecruitment()` | 标题规则：排除"大学/学院/高校"作为雇主的招聘 |
| `displayJobs()` / `displayCurrentPage()` | 渲染职位卡片/列表 |
| `renderPagination()` / `goToPage()` / `prevPage()` / `nextPage()` | 分页 |
| `switchView()` / `changePerPage()` | 视图与每页条数切换 |
| `copyTitle()` | 复制标题到剪贴板（微信搜索用） |

### 6.4 组件划分（逻辑组件）
- **来源卡片**：展示各来源及其数量，点击切换 `activeSource`。
- **职位卡片/列表项**：标题、来源、日期、类型、截止（临近标红）、公众号过期提示。
- **分页器**：页码窗口 + 上一页/下一页。
- **视图开关**：卡片 ↔ 列表。

---

## 7. 认证与权限设计

### 7.1 当前状态（重要）
**系统当前无认证、无用户体系**。设计为**公开只读展示**：
- 任何人可访问页面与 `/api/jobs`；
- 无登录、无角色、无 JWT、无会话；
- 写入仅由本机调度器（服务端进程）完成，不接受客户端写请求。

### 7.2 风险与建议
若将来需限制访问（如仅自己可见），推荐在**反向代理层**或**应用层**加认证，而非改造前端：
- 轻量：Nginx `auth_basic`（密码文件）；
- 标准：JWT Bearer + 中间件（见下方草案，**未实现**）。

### 7.3 推荐 RBAC 角色矩阵（未来扩展，未实现）

| 角色 | 读数据 | 触发爬取 | 管理配置 |
|---|---|---|---|
| 访客（默认） | ✅ | ❌ | ❌ |
| 管理员 | ✅ | ✅ | ✅ |

### 7.4 推荐 JWT 结构（草案，未实现）
```
Header : { "alg": "HS256", "typ": "JWT" }
Payload: { "sub": "<user_id>", "role": "admin|guest", "iat": ..., "exp": ... }
Signature: HMAC-SHA256(base64(header)+"."+base64(payload), SECRET)
```
- 中间件链（草案）：`请求 → 解析 Authorization → 校验签名/过期 → 角色校验 → 路由处理`。
- 当前未实现，新增前需引入密钥管理（环境变量 `JWT_SECRET`）与登录接口。

---

## 8. 部署架构

### 8.1 单实例拓扑
单台 Linux 服务器（Ubuntu 22.04）运行一个 `wuhan-job` 服务实例。
**多实例**：当前为单实例设计（文件型数据源不支持并发写）。若需多实例/高可用，须先将存储迁移到数据库（见第 10 节技术债务）。

### 8.2 环境变量清单
当前后端**无强制环境变量**（端口、时区在代码中固定）。可选：
| 变量 | 默认值 | 说明 |
|---|---|---|
| `TZ` | 由系统决定 | 建议设为 `Asia/Shanghai`（调度已硬编码该时区） |
| `PORT` | `8000` | 如需改监听端口，改 `server/app.py` 的 `serve(...)` 与 Nginx 反代 |
| `FLASK_ENV` | 不设置 | 生产由 waitress 提供，勿用 `flask run` 上生产 |

### 8.3 systemd 单元（`/etc/systemd/system/wuhan-job.service`）
由 `server/setup.sh` 生成：
```ini
[Unit]
Description=Wuhan Teacher Job Tracker (Flask + APScheduler)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/wuhan-teacher-job-tracker
ExecStart=/home/ubuntu/wuhan-teacher-job-tracker/venv/bin/python server/app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 8.4 Nginx 反代（`server/nginx-wuhan-job.conf`）
```nginx
server {
    listen 80;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 8.5 Caddy 替代方案（可选，未默认启用）
若偏好 Caddy 的自动 HTTPS，可用：
```caddyfile
:80 {
    reverse_proxy 127.0.0.1:8000
}
```
（启用 443/HTTPS 时改为你的域名并放开 443 安全组。）

### 8.6 一键部署
```bash
git clone https://github.com/ArthurUker/wuhan-teacher-job-tracker.git ~/wuhan-teacher-job-tracker
cd ~/wuhan-teacher-job-tracker
sudo bash server/setup.sh
```
`setup.sh` 依次：装系统依赖/浏览器库 → 建 venv 并装 `crawler`+`server` 依赖 → `playwright install chromium` → 修正目录属主为 `ubuntu` → 注册并启动 systemd → 配置并启动 Nginx。

---

## 9. 安全设计

### 9.1 认证与授权
- 当前：无认证，公开只读（见 7.1）。写入仅限本机调度器。

### 9.2 限流（建议）
- Nginx 反代层加 `limit_req`（示例）：
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
location /api/ { limit_req zone=api burst=20 nodelay; }
```
- 当前未默认开启；如使用面扩大建议启用。

### 9.3 密码策略
- N/A（无账户体系）。若接入 JWT/登录，应在登录接口实施最小长度、失败锁定、HTTPS 传输。

### 9.4 审计日志
- 应用日志：`logs/server.log`（APScheduler 调度与爬虫子进程输出）。
- 系统日志：`journalctl -u wuhan-job`（含 stdout/stderr）。
- 爬虫执行记录：每次运行的起止、returncode、stdout/stderr 尾部均写入上述日志。
- 无独立审计表；如需操作审计，建议后续接入结构化日志/集中收集。

### 9.5 其他
- 爬虫遵守目标站 `robots.txt`，仅个人学习用途。
- 反向代理建议仅暴露 80/443，SSH 22 限制来源 IP。

---

## 10. 已知技术债务与待办

| # | 项 | 说明 / 建议 |
|---|---|---|
| 1 | 非原子写 | 爬虫直接 `json.dump` 覆盖 `jobs.json`，读取端偶发读到半成品。建议改"写临时文件 + `rename`"原子替换。 |
| 2 | 无数据库 | 全部数据在前端内存筛选，无法服务端检索/聚合。多实例或大数据量时应迁移到 SQLite/Postgres。 |
| 3 | 无认证 | 公开只读，无访问控制（见 7）。 |
| 4 | 单实例 | 文件型存储不支持并发写，无法水平扩展。 |
| 5 | 调度错峰 | 服务重启期间的计划任务不会补跑，仅等下一周期。 |
| 6 | 过滤误判 | 历史上出现过事业单位综合招聘/公示漏过过滤；`crawl_utils.py` 规则需持续维护。 |
| 7 | 微信链接时效 | 搜狗临时链接会失效，`refresh_wechat_links.py` 兜底但依赖搜狗可达。 |
| 8 | 部分站点可达性 | 境外 runner 曾无法访问黄冈/孝感等站；国内服务器应改善（待验证）。 |
| 9 | Actions 残留 | `.github/workflows` 保留为手动备用，定时已注释关闭，需与自托管状态保持同步。 |
| 10 | 备份缺失 | `jobs.json` 无自动备份；建议定时 `git commit/push` 或异地拷贝。 |

**待办（建议）**
- [ ] 原子写 `jobs.json`
- [ ] 加 Nginx `limit_req` 限流
- [ ] 可选：接入 JWT + 基础 RBAC
- [ ] 可选：定时备份 `data/jobs.json` 到 GitHub/对象存储
- [ ] 监控：进程存活 + 数据条数异常告警

---

## 11. 开发环境搭建指南

### 11.1 前置要求
- Python 3.10+
- `pip` / `venv`
- 操作系统库（Playwright 浏览器依赖，Ubuntu 示例）：
```bash
sudo apt-get install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
  libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
  libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0
```

### 11.2 安装与运行
```bash
git clone https://github.com/ArthurUker/wuhan-teacher-job-tracker.git
cd wuhan-teacher-job-tracker

python3 -m venv venv
source venv/bin/activate
pip install -r crawler/requirements.txt
pip install -r server/requirements.txt
python -m playwright install chromium

# 启动后端（托管前端 + 定时任务），访问 http://localhost:8000
python server/app.py

# 或仅手动跑一次爬虫
cd crawler && python main.py
```

### 11.3 目录速览
见 `docs/DESIGN.md` 与本文第 3、4 节。

---

## 12. 运维手册

### 12.1 常用命令
```bash
sudo systemctl status wuhan-job     # 状态
sudo systemctl restart wuhan-job    # 重启（更新代码后）
sudo systemctl stop wuhan-job       # 停止
sudo journalctl -u wuhan-job -f     # 实时日志
```

### 12.2 日志查看
| 日志 | 位置 | 内容 |
|---|---|---|
| 应用日志 | `logs/server.log` | 调度、爬虫输出 |
| 系统日志 | `journalctl -u wuhan-job` | 进程 stdout/stderr |
| Nginx | `/var/log/nginx/*.log` | 接入/反代日志 |

### 12.3 备份与恢复
**备份**（建议加入 cron）：
```bash
cp data/jobs.json /backup/jobs-$(date +%F).json
# 或：git commit -m "backup" data/jobs.json && git push
```
**恢复**：将备份文件放回 `data/jobs.json` 并 `sudo systemctl restart wuhan-job`。

### 12.4 故障排查

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 页面空白/加载失败 | 后端未起或 80 未放通 | `systemctl status wuhan-job`；查安全组 80 |
| `/api/jobs` 返回 500 | `jobs.json` 损坏/不存在 | 检查文件 JSON 合法性；重跑爬虫生成 |
| 数据长时间不更新 | 调度未触发/爬虫报错 | `journalctl -u wuhan-job` 查 APScheduler 与子进程错误 |
| 端口冲突 | 8000 被占用 | 改 `app.py` 端口与 Nginx 反代 |
| Playwright 报错缺库 | 浏览器依赖不全 | `python -m playwright install-deps chromium` |
| Nginx 502 | 后端未监听 8000 | 确认 `wuhan-job` 在运行 |

### 12.5 更新流程
```bash
git pull
# 若依赖/Playwright 有变更：
sudo bash server/setup.sh
sudo systemctl restart wuhan-job
```

---

## 许可证
MIT License
