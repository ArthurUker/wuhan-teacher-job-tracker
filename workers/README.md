# Cloudflare Worker 部署指南

## 一键触发爬虫

前端「刷新数据」按钮可以通过 Cloudflare Worker 代理触发 GitHub Actions 运行爬虫。

## 部署步骤

### 1. 创建 GitHub Personal Access Token

1. 打开 https://github.com/settings/tokens
2. 点击 **Generate new token (classic)**
3. 勾选权限：`repo` (完整)、`workflow`
4. 生成并**复制 Token**

### 2. 部署 Cloudflare Worker

1. 登录 https://dash.cloudflare.com → **Workers & Pages** → **Create**
2. 选择 **Create Worker**，名称随意（如 `crawl-trigger`）
3. 删除默认代码，粘贴 `workers/trigger-crawl.js` 的全部内容
4. 点击 **Deploy**

### 3. 配置环境变量

1. 在 Worker 页面点击 **Settings** → **Variables and Secrets**
2. 添加两个 Secret：

| 名称 | 值 | 说明 |
|------|-----|------|
| `GITHUB_PAT` | 你刚创建的 GitHub PAT | 必填 |
| `GITHUB_REPO` | `ArthurUker/wuhan-teacher-job-tracker` | 默认值，可省略 |

3. 点击 **Save and Deploy** 重新部署

### 4. 配置前端

打开 `frontend/app.js`，找到第 4 行：

```js
const TRIGGER_WORKER_URL = '';
```

改为你的 Worker URL，例如：

```js
const TRIGGER_WORKER_URL = 'https://crawl-trigger.your-name.workers.dev';
```

提交推送后即可使用。

## 工作原理

```
用户点击「刷新数据」
    ↓
前端 POST 到 Cloudflare Worker
    ↓
Worker 用 GITHUB_PAT 调用 GitHub API workflow_dispatch
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

- GitHub PAT 存储在 Cloudflare Worker 的 Secrets 中，不会暴露到前端
- 前端只调用你的 Worker URL，不接触任何密钥
- 建议给 PAT 设置最小必要权限（repo + workflow 即可）
