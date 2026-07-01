# 武汉教师招聘信息追踪系统

🎓 实时监控武汉市及湖北省教师招聘信息，帮助教师及时了解招聘动态。

## 功能特点

- ✅ 自动爬取武汉市教育局官网招聘信息
- ✅ 自动爬取湖北省教育考试院招聘信息
- ✅ 每日自动更新数据（通过 GitHub Actions）
- ✅ 提供友好的 Web 界面查看招聘信息
- ✅ 支持搜索和筛选功能
- ✅ 免费部署在 GitHub Pages

## 数据来源

1. **武汉市教育局官网** - https://jyj.wuhan.gov.cn/zwdt/tsgg/
2. **湖北省教育考试院** - http://www.hbea.edu.cn/html/jszp/index.html

## 使用方法

### 1. 在线访问

访问 GitHub Pages 部署的网站（部署后提供链接）

### 2. 本地运行

#### 运行爬虫

```bash
cd crawler
pip install -r requirements.txt
python main.py
```

#### 查看前端

在 `frontend` 目录启动一个简单的 HTTP 服务器：

```bash
cd frontend
python -m http.server 8000
```

然后访问 http://localhost:8000

### 3. 自动更新

项目已配置 GitHub Actions，每天自动运行爬虫并更新数据。

如需手动触发，在 GitHub 仓库的 Actions 页面点击 "Run workflow"。

## 项目结构

```
wuhan-teacher-job-tracker/
├── crawler/              # 爬虫脚本
│   ├── main.py          # 主程序
│   ├── crawl_wuhan_education.py  # 武汉市教育局爬虫
│   ├── crawl_hubei_exam.py       # 湖北省教育考试院爬虫
│   └── requirements.txt          # Python 依赖
├── data/                # 数据文件
│   └── jobs.json       # 爬取的招聘信息
├── frontend/            # 前端页面
│   ├── index.html      # 主页面
│   ├── style.css       # 样式
│   └── app.js          # JavaScript 逻辑
└── .github/
    └── workflows/       # GitHub Actions 配置
        └── crawl.yml
```

## 部署到 GitHub Pages

1. Fork 或克隆此仓库
2. 在仓库设置中启用 GitHub Pages
3. 选择 `main` 分支作为源
4. 访问提供的 GitHub Pages 链接

## 技术栈

- **后端**: Python + requests + BeautifulSoup
- **前端**: HTML + CSS + JavaScript
- **部署**: GitHub Pages + GitHub Actions

## 注意事项

- 爬虫仅用于学习和个人使用，请遵守目标网站的 robots.txt
- 如遇反爬措施，可能需要更新爬虫策略
- 数据更新频率受 GitHub Actions 限制（每天一次）

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
