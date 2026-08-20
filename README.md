# 🚀 Telegram Test Platformasi (Production-Ready)

O‘quvchilar va o‘qituvchilar/adminlar uchun mo‘ljallangan, professional, yuqori darajada barqaror, tezkor va xavfsiz Telegram Test Platformasi.

---

## 📌 Asosiy Imkoniyatlar

### 👨🎓 O‘quvchi Imkoniyatlari:
- 📢 **Majburiy kanallarga a'zo bo'lish tizimi:** To'liq obuna bo'lmaguncha botdan foydalanib bo'lmaydi.
- 📝 **Interaktiv Test Yechish:** Anti-cheat (savollar va variantlarni random aralashtirish), taymer, oldinga/orqaga xavfsiz navigatsiya.
- ✅ **Tezkor Javoblarni Tekshirish:** `1-A 2-B 3-C` formatidagi matnli javoblar yoki test kodi orqali tekshirish.
- 🎯 **Batafsil Natijalar:** To'g'ri/xato javoblar soni, foiz, sarflangan vaqt, xatolar tahlili va PDF natija hisoboti.
- 🏆 **Reyting Tizimi:** Umumiy respublika reytingi va maxsus guruhlar reytingi.
- 🎉 **Avtomatik PDF Sertifikat:** O'tish balini to'plagan o'quvchiga unikal raqamli (`CERT-2026-XXXXXX`) professional PDF sertifikat generatsiyasi.
- ✍️ **Mustaqil Test Yaratish:** O'quvchilar ham mustaqil test tuzib, kodi orqali boshqalarga ulashishi mumkin.
- 🔖 **Saqlangan testlar va Yutuqlar (Achievements):** Shaxsiy statistika va nishonlar.
- 👨💼 **Admin bilan bog'lanish:** Savol va murojaat yuborish (support tickets).

### 👨💼 Admin Paneli Imkoniyatlari:
- 📝 **To'liq Test Boshqaruvi:** Statuslar (`draft`, `scheduled`, `active`, `finished`, `archived`), testni nusxalash (clone), o'chirish.
- ⏰ **Test Jadvali va Paroli:** Boshlanish va tugash vaqtini belgilash, xususiy test paroli qo'yish.
- ➕ **Bosqichma-bosqich Savol Qo'shish:** Matn, rasm, A/B/C/D variantlar va har bir savolga individual ballar.
- 📥 **Excel Import:** `.xlsx` fayl orqali yuzlab savollarni bir vaqtda qatorlar bo'yicha chuqur validatsiya bilan yuklash.
- 📤 **Excel Eksport:** Barcha o'quvchilar natijalarini to'liq formatlangan `.xlsx` faylda yuklab olish.
- 👥 **O'quvchilar va Guruhlar:** Qidiruv (ism, username, ID, tel), bloklash/ochish, guruhlar tuzish va guruhga test yuborish.
- 📢 **Xavfsiz Xabar Tarqatish (Broadcast):** Barcha o'quvchilarga, guruhlarga yoki ma'lum test ishtirokchilariga tezkor batching bilan xabar yuborish.
- 👑 **Adminlar Boshqaruvi:** Telegram ID orqali yangi admin qo'shish/o'chirish (`OWNER_ID` himoyalangan).
- 📈 **Kengaytirilgan Statistika:** Faol foydalanuvchilar, eng ko'p ishlangan testlar va eng qiyin savollar tahlili.

---

## 🛠 Texnologik Stack

- **Python:** 3.12+
- **Bot Framework:** `aiogram 3.x`
- **Database ORM:** `SQLAlchemy 2.0` (AsyncIO) + `asyncpg` / `aiosqlite`
- **FSM & Kesh:** `Redis` (RedisStorage) / MemoryStorage fallback
- **Hujjatlar & Fayllar:** `openpyxl` (Excel), `ReportLab` & `Pillow` (PDF sertifikatlar)
- **Konteynerizatsiya:** Docker & docker-compose

---

## 📂 Loyiha Tuzilishi

```text
telegram_test_platform/
├── app/
│   ├── config/              # Konfiguratsiya va Settings (.env)
│   ├── database/
│   │   ├── models/          # User, Test, Question, Result, Group, Certificate, etc.
│   │   ├── repositories/    # Asinxron ma'lumotlar bazasi so'rovlari
│   │   └── session.py       # Engine va AsyncSession boshqaruvi
│   ├── services/            # Biznes mantiq (Auth, Scoring, Test, Excel, PDF, Broadcast)
│   ├── bot/
│   │   ├── filters/         # IsAdminFilter, IsRegisteredFilter
│   │   ├── middlewares/     # DB, Auth/Block, Required Channel, Throttling, Error
│   │   ├── states/          # FSM holatlari (Registration, Test Creation, Excel, Support)
│   │   ├── keyboards/       # Reply va Inline tugmalar
│   │   └── handlers/        # O'quvchi va Admin barcha handlerlari
│   └── main.py              # Botni ishga tushirish nuqtasi
├── tests/                   # Pytest to'liq test to'plami
├── storage/                 # Sertifikatlar, eksport va yuklamalar jildi
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ O'rnatish va Sozlash

### 1. Repositoryni yuklab olish va virtual muhit yaratish:
```bash
git clone <repository_url>
cd telegram_test_platform
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 2. Bog'liqliklarni o'rnatish:
```bash
pip install -r requirements.txt
```

### 3. `.env` faylini sozlash:
`.env.example` faylidan `.env` nusxasini yarating:
```bash
cp .env.example .env
```

`.env` faylini ochib, kerakli o'zgaruvchilarni kiriting:
```ini
# Bot ma'lumotlari (@BotFather dan olingan token)
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ

# Asosiy Admin Telegram ID si (@userinfobot dan olingan ID)
OWNER_ID=123456789

# Ma'lumotlar bazasi
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test_platform_db

# Redis FSM / Kesh
REDIS_URL=redis://localhost:6379/0

# Sozlamalar
DEBUG=False
PAGE_SIZE=10
TIMEZONE=Asia/Tashkent
```

---

## 🚀 Ishga Tushirish

### Usul 1: Docker va Docker Compose orqali (Tavsiya etiladi - Production)
Barcha xizmatlar (PostgreSQL, Redis va Bot) bir buyruq bilan ishga tushadi:
```bash
docker-compose up --build -d
```

Loglarni ko'rish:
```bash
docker-compose logs -f bot
```

To'xtatish:
```bash
docker-compose down
```

---

### Usul 2: Mahalliy (Local Development)
PostgreSQL va Redis ishga tushganidan so'ng:
```bash
python -m app.main
```

---

## 📥 Excel orqali Savollarni Yuklash Formati

Admin panelida `📥 Excel import` tanlanganda `.xlsx` fayl quyidagi ustunlar tartibida bo'lishi lozim:

| question | option_a | option_b | option_c | option_d | correct_answer | points |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| O'zbekiston poytaxti qaysi? | Samarqand | Toshkent | Buxoro | Xiva | B | 2.0 |
| 2x + 5 = 15 bo'lsa, x = ? | 3 | 5 | 7 | 10 | B | 1.5 |

- `correct_answer` faqat **A**, **B**, **C** yoki **D** bo'lishi kerak.
- Agar qatorda xatolik bo'lsa, bot qator raqami va aniq xatolik sababini ko'rsatadi.

---

## 🧪 Testlarni Ishga Tushirish

Barcha unit va integratsion testlarni tekshirish:
```bash
pytest tests/ -v
```

---

## 🛡 Xavfsizlik va Anti-Cheat Xususiyatlari

- **Shuffled Questions & Options:** Har bir urinish (attempt) uchun savollar va javob variantlari alohida random tartibda taqdim etiladi.
- **Duplicate Protection:** Bir vaqtning o'zida ikkita urinish boshlash yoki yakunlangan testga qayta javob berish to'liq cheklangan.
- **Throttling Middleware:** Anti-spam va tugmalarni haddan tashqari tez bosishdan himoya.
- **Owner Protection:** Boshlang'ich boshqaruvchi (`OWNER_ID`) dasturiy darajada boshqa adminlar tomonidan o'chirilmaydi yoki bloklanmaydi.
- **Error Shielding:** Foydalanuvchilarga hech qachon texnik xatoliklar (traceback) ko'rsatilmaydi.
