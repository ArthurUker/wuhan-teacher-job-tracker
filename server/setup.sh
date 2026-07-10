#!/usr/bin/env bash
#
# 自托管一键部署脚本（Ubuntu 22.04 + systemd + Nginx）
# 用法（在服务器上，建议用 root 或 sudo 执行）：
#   sudo bash server/setup.sh
#
# 脚本会：安装依赖 → 建 venv → 装 Playwright → 注册 systemd 服务 → 配置 Nginx。
# 部署完成后访问 http://<服务器IP>/  （确保腾讯云安全组已放通 80 端口）。
#
set -euo pipefail

# 项目根目录：取本脚本所在目录的上一级
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="wuhan-job"
VENV_DIR="$PROJECT_DIR/venv"
PY="$VENV_DIR/bin/python"

echo "==> 项目目录: $PROJECT_DIR"

# 1. 系统依赖
echo "==> 安装系统依赖 (python3-venv, nginx, 浏览器库)..."
apt-get update -y
apt-get install -y python3-venv python3-pip nginx \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0

# 2. Python 虚拟环境
echo "==> 创建虚拟环境: $VENV_DIR"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r "$PROJECT_DIR/crawler/requirements.txt"
"$PY" -m pip install -r "$PROJECT_DIR/server/requirements.txt"

# 3. Playwright 浏览器
echo "==> 安装 Playwright Chromium..."
"$PY" -m playwright install chromium
"$PY" -m playwright install-deps chromium 2>/dev/null || \
    echo "（install-deps 失败可忽略，若运行时报缺库请手动 apt 安装对应依赖）"

# 3.5 修正目录属主：systemd 服务以 ubuntu 运行，需可写日志/数据
echo "==> 修正项目目录属主为 ubuntu..."
chown -R ubuntu:ubuntu "$PROJECT_DIR"

# 4. systemd 服务
echo "==> 写入 systemd 单元: /etc/systemd/system/${SERVICE_NAME}.service"
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Wuhan Teacher Job Tracker (Flask + APScheduler)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PY} ${PROJECT_DIR}/server/app.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
echo "==> 服务状态："
systemctl status "$SERVICE_NAME" --no-pager || true

# 5. Nginx
echo "==> 配置 Nginx..."
cp "$SCRIPT_DIR/nginx-wuhan-job.conf" /etc/nginx/sites-available/${SERVICE_NAME}.conf
if [ -L /etc/nginx/sites-enabled/default ]; then
    rm -f /etc/nginx/sites-enabled/default
fi
ln -sf /etc/nginx/sites-available/${SERVICE_NAME}.conf /etc/nginx/sites-enabled/${SERVICE_NAME}.conf
nginx -t
systemctl enable nginx
systemctl restart nginx

echo ""
echo "============================================================"
echo " 部署完成！"
echo " 访问: http://<你的服务器IP>/   （默认 80 端口）"
echo " 查看日志: sudo journalctl -u ${SERVICE_NAME} -f"
echo " 数据文件: ${PROJECT_DIR}/data/jobs.json"
echo " 计划(北京时间): 爬取 0/12点, 刷新 0:30/6:30/12:30/18:30"
echo ""
echo " ⚠ 请在腾讯云安全组放通 80 端口；若放通 8080 等其它端口，"
echo "   请修改 server/nginx-wuhan-job.conf 的 listen 端口后执行:"
echo "   sudo nginx -t && sudo systemctl restart nginx"
echo "============================================================"
