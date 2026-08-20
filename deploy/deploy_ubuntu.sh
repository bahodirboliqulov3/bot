#!/usr/bin/env bash
# ==============================================================================
# Telegram Test Platform Bot — Ubuntu VPS 1-Click Auto Installer
# ==============================================================================

set -e

echo "🚀 [1/5] Tizim paketlarini yangilash..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git curl

echo "📦 [2/5] Virtual muhit (venv) yaratish va kutubxonalarni o'rnatish..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "📁 [3/5] Kerakli papkalarni tekshirish..."
mkdir -p storage/certificates storage/exports storage/uploads storage/data

echo "⚙️ [4/5] Systemd avtomatik xizmatini sozlash..."
SERVICE_FILE="/etc/systemd/system/telegram_bot.service"
CURRENT_DIR=$(pwd)

cat << EOF | sudo tee $SERVICE_FILE
[Unit]
Description=Telegram Test Platform Bot
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python -m app.main
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable telegram_bot
sudo systemctl restart telegram_bot

echo "✅ [5/5] Bot muvaffaqiyatli ishga tushirildi!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Holatni tekshirish:  sudo systemctl status telegram_bot"
echo "📜 Loglarni ko'rish:    sudo journalctl -u telegram_bot -f"
echo "🔄 Qayta ishga tushirish: sudo systemctl restart telegram_bot"
echo "⏹ To'xtatish:          sudo systemctl stop telegram_bot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
