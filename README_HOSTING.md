# 🚀 Telegram Test Platform — Hostingga O‘rnatish Qo‘llanmasi

Ushbu loyiha 24/7 rejimida serverda (hostingda) to‘xtovsiz ishlash uchun 100% tayyorlangan.

---

## 🌟 1-USUL: Oddiy Ubuntu / Debian VPS Serverga O‘rnatish (Tavsiya etiladi)

VPS serveringizga (masalan: *Timeweb, Hetzner, Beget, DigitalOcean, VDSina*) SSH orqali ulaning va quyidagi qadamlarni bajaring:

### 1-Qadam: Loyihani serverga yuklash
Zip faylni serverga tashlang yoki GitHub dan clone qiling:
```bash
cd /root
# Zip faylni oching
unzip telegram_test_platform_HOSTING_READY.zip -d telegram_test_platform
cd telegram_test_platform
```

### 2-Qadam: 1-Buyruq orqali avtomatik o‘rnatish
```bash
chmod +x deploy/deploy_ubuntu.sh
./deploy/deploy_ubuntu.sh
```

Shu bilan bot serveringizda **avtomatik fonda ishga tushadi** va server o‘chib-yonsa ham avtomatik qayta yonadi!

---

### 🛠 Foydali buyruqlar (VPS boshqaruvi):
* **Bot holatini ko‘rish:** `sudo systemctl status telegram_bot`
* **Jonli loglarni kuzatish:** `sudo journalctl -u telegram_bot -f`
* **Botni qayta ishga tushirish:** `sudo systemctl restart telegram_bot`
* **Botni to‘xtatish:** `sudo systemctl stop telegram_bot`

---

## 🐳 2-USUL: Docker orqali ishga tushirish

Agar siz Docker ishlatmoqchi bo‘lsangiz:

```bash
# 1. Image qurish va fonda yoqish
docker compose up -d

# 2. Loglarni ko‘rish
docker compose logs -f bot
```

---

## ⚙️ Sozlamalar (`.env` fayli):
* `BOT_TOKEN` — Telegram botingizning tokeni
* `OWNER_ID` — Sizning Telegram ID raqamingiz
* `DATABASE_URL` — SQLite: `sqlite+aiosqlite:///storage/test_platform.db` (yoki PostgreSQL)

---

🎉 **Bot foydalanuvchilari saqlab qolingan va hostingga yuklashga to‘liq tayyor!**
