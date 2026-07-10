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
   - ⭐⭐⭐ 中等价值：有WAF防护，需测试

### 省级数据源

10. **湖北省教育考试院** - http://www.hbea.edu.cn/html/jszp/index.html

### 微信公众号（搜狗微信搜索）

11. **搜狗微信搜索** - https://weixin.sogou.com/
    - ⭐⭐⭐⭐⭐ 高价值：覆盖全平台公众号文章，时效性最强
    - 搜索关键词：武汉/湖北/黄石/鄂州/黄冈/孝感 教师招聘

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
├── crawler/                        # 爬虫脚本
│   ├── main.py                    # 主程序
│   ├── crawl_wuhan_education.py   # 武汉市教育局
│   ├── crawl_wuhan_hr.py          # 武汉市人社局
│   ├── crawl_hubei_exam.py        # 湖北省教育考试院
│   ├── crawl_optics_valley.py     # 武汉东湖新技术开发区
│   ├── crawl_hanyang.py           # 汉阳区人民政府
│   ├── crawl_caidian.py           # 蔡甸区人民政府
│   ├── crawl_ezhou.py             # 鄂州市教育局
│   ├── crawl_huangshi.py          # 黄石市教育局
│   ├── crawl_huanggang.py         # 黄冈市教育局
│   ├── crawl_xiaogan.py           # 孝感市教育局
│   └── merge_data.py              # 数据合并工具
│   └── requirements.txt           # Python 依赖
├── data/                          # 数据文件
│   └── jobs.json                 # 爬取的招聘信息
├── frontend/                      # 前端页面
│   ├── index.html                # 主页面
│   ├── style.css                 # 样式
│   └── app.js                    # JavaScript 逻辑
└── .github/
    └── workflows/                 # GitHub Actions 配置（已改为手动备用）
        └── crawl.yml
└── server/                       # 自托管后端（Flask + APScheduler）
    ├── app.py
    ├── requirements.txt
    ├── nginx-wuhan-job.conf
    └── setup.sh
```

## 部署到 GitHub Pages（可选/历史方案）

> 本项目已支持**自托管**（见下），GitHub Pages 仅作为静态预览的备选。
> 注意：自托管后前端改从 `/api/jobs` 读取数据，GitHub Pages 上无后端，故 Pages 版本不再实时可用。

1. Fork 或克隆此仓库
2. 在仓库设置中启用 GitHub Pages
3. 选择 `main` 分支作为源
4. 访问提供的 GitHub Pages 链接

## 自托管部署（推荐，不受 GitHub 额度限制）

在自己的服务器（Linux + systemd + Nginx）上常驻运行：后端用 Flask 托管前端 +
APScheduler 按计划后台跑爬虫，实现"一直运行、持续更新"。

### 目录新增

```
server/
├── app.py                 # Flask 后端：托管前端 + /api/jobs + 定时爬取/刷新
├── requirements.txt       # 后端依赖（flask / apscheduler / waitress / tzdata）
├── nginx-wuhan-job.conf   # Nginx 反代配置
└── setup.sh               # 一键部署脚本（装依赖/venv/Playwright/systemd/Nginx）
```

### 在服务器上部署

```bash
# 1) 以 ubuntu 用户克隆仓库
git clone <你的仓库地址> ~/wuhan-teacher-job-tracker
cd ~/wuhan-teacher-job-tracker

# 2) 用 root/sudo 运行一键脚本（安装依赖、建 venv、注册 systemd 与 Nginx）
sudo bash server/setup.sh
```

完成后访问 `http://<服务器公网IP>/`（**记得在云安全组放通 80 端口**）。
查看运行日志：`sudo journalctl -u wuhan-job -f`。

### 定时计划（北京时间 Asia/Shanghai）

- 主爬虫 `crawler/main.py`：每天 **0:00 / 12:00**
- 刷新公众号链接 `crawler/refresh_wechat_links.py`：每天 **0:30 / 6:30 / 12:30 / 18:30**

均由 `server/app.py` 中的 APScheduler 调度，无需 GitHub Actions。

### 维护

- 重启服务：`sudo systemctl restart wuhan-job`
- 更新代码：`git pull` 后 `sudo systemctl restart wuhan-job`（依赖变更时重跑 `setup.sh`）
- 停止 GitHub Actions 定时：两个 workflow 的 `schedule` 已注释关闭，仅保留手动触发作为备用

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
