# Cloudflare Worker 部署指南

## 一键触发爬虫

前端「刷新数据」按钮通过 Cloudflare Worker 代理触发 GitHub Actions 运行爬虫。

本 Worker 采用 **Git 集成自动部署**，`workers/` 目录下代码变更 push 到 `main` 分支后会自动重新部署，无需手动同步。

## 部署步骤（首次配置，仅需一次）

### 1. 创建 GitHub Personal Access Token

1. 打开 https://github.com/settings/tokens
2. 点击 **Generate new token (classic)**
3. 勾选权限：`repo`（完整）、`workflow`
4. 生成并复制 Token

### 2. 创建 Git 集成 Worker

1. 登录 https://dash.cloudflare.com → **Workers & Pages** → **Create**
2. 选择 **Import a repository**（注意不是 "Create Worker" 手动模式）
3. 授权并选择仓库：`ArthurUker/wuhan-teacher-job-tracker`，分支 `main`
4. 构建配置：
   - **Root directory**：`workers`
   - **Build command**：留空
   - **Deploy command**：`npx wrangler deploy`（默认值）
5. 点击部署，等待首次构建完成

### 3. 配置环境变量与密钥

部署完成后，进入该 Worker → **Settings → Variables and Secrets**：

| 名称 | 类型 | 值 | 说明 |
|------|------|-----|------|
| `GITHUB_PAT` | **Secret** | 你创建的 GitHub PAT | 必填 |
| `GITHUB_REPO` | Variable | `ArthurUker/wuhan-teacher-job-tracker` | 可省略，代码有默认值 |
| `AUTH_TOKEN` | **Secret** | 自定义强密码/随机字符串 | 强烈建议配置，用于接口鉴权 |

保存后会自动触发一次重新部署。

### 4. 配置前端

打开 `frontend/app.js`，配置 Worker URL 与鉴权 Token：

```js
const TRIGGER_WORKER_URL = 'https://wuhan-crawl-trigger.your-subdomain.workers.dev';
const AUTH_TOKEN = '与 Cloudflare AUTH_TOKEN 一致的值';
```

并在触发请求时携带 Header：

```js
fetch(TRIGGER_WORKER_URL, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${AUTH_TOKEN}`,
  },
});
```

提交推送后即可使用。

## 日常更新流程（后续维护）

今后如需修改 `trigger-crawl.js` 的逻辑：

1. 在 VS Code 中直接修改 `workers/trigger-crawl.js`
2. `git commit && git push`
3. Cloudflare 自动检测变更并重新部署，**无需手动登录 Dashboard 操作**

## 工作原理

```
用户点击「刷新数据」
    ↓
前端携带 Authorization Header，POST 到 Cloudflare Worker
    ↓
Worker 校验 Token → 用 GITHUB_PAT 调用 GitHub API workflow_dispatch
    ↓
GitHub Actions 开始运行爬虫（约 2-5 分钟）
    ↓
前端每 15 秒轮询 jobs.json 检测数据变化
    ↓
检测到新数据后自动刷新页面显示结果
```

## 费用

Cloudflare Workers 免费计划每天有 **10 万次请求**，完全够用。

## 安全说明

- `GITHUB_PAT` 与 `AUTH_TOKEN` 均存储在 Cloudflare Secrets 中，Dashboard 不会明文展示
- 前端 `AUTH_TOKEN` 会随 JS 源码暴露给访问者，仅能防止自动化扫描式滥用，无法防止"查看源码"的针对性攻击；如需更高安全性，建议后续引入验证码或频率限制
- 建议给 PAT 设置最小必要权限（`repo` + `workflow` 即可，不要勾选额外权限）
- **部署后务必验证**：不带 Token 请求应返回 401，确认鉴权确实生效

## 故障排查

### 部署失败：root directory not found

**原因**：Cloudflare 无法识别 `workers/` 目录下的项目结构

**解决**：确保 `workers/wrangler.toml` 文件存在且格式正确

### 调用失败：返回 401 Unauthorized

**原因**：未配置 `AUTH_TOKEN` 或 Token 不匹配

**解决**：
1. 检查 Cloudflare Dashboard 是否配置了 `AUTH_TOKEN` Secret
2. 检查 `frontend/app.js` 中的 `AUTH_TOKEN` 是否与 Cloudflare 配置一致
3. 如果不需要鉴权，可以从 `trigger-crawl.js` 中移除鉴权逻辑

### 触发失败：crawl.yml not found

**原因**：GitHub API 未找到 `.github/workflows/crawl.yml`

**解决**：
1. 检查仓库中是否存在该文件
2. 检查 `GITHUB_PAT` 是否有 `repo` 权限
3. 检查 `GITHUB_REPO` 是否填写正确

