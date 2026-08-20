# 🎯 Telegram Test Platformasi — To'liq Loyiha Qo'llanmasi

Ushbu hujjat botni boshqa kompyuterda ochish, ishga tushirish, tahrirlash va rivojlantirish uchun to'liq yo'riqnomadir.

---

## 1. 🔑 Asosiy Ma'lumotlar & Sozlamalar

- **Bot Username:** `@tekshiruv2_bot`
- **Bot Token:** `8780241869:AAHjmdDSqUSCRiCLHAguEDUIhOot6mjSGvY`
- **Bosh Admin (Owner Telegram ID):** `8420258761`
- **Platforma tili:** Python 3.10+ (Aiogram 3.x, SQLAlchemy 2.0 Async, SQLite, OpenPyXL, ReportLab)
- **Ma'lumotlar bazasi:** `storage/test_platform.db` (SQLite async)

---

## 2. 🚀 Boshqa Kompyuterda Ishga Tushirish (O'rnatish):

1. **Arxivni oching** (ZIP faylni papkaga chiqaring).
2. **Terminal yoki CMD ni ochib**, loyiha papkasiga kiring:
   ```bash
   cd telegram_test_platform
   ```
3. **Kutubxonalarni o'rnating:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Botni ishga tushiring:**
   ```bash
   python -m app.main
   ```

---

## 3. 📂 Loyiha Arxitekturasi & Fayllar Tuzilishi:

```
telegram_test_platform/
├── app/
│   ├── main.py                     # Botning asosiy kirish nuqtasi va ishga tushiruvchisi
│   ├── config.py                   # Bot sozlamalari (.env o'quvchi)
│   ├── bot/
│   │   ├── filters/                # Admin va ro'yxatdan o'tganlik filtrlari
│   │   ├── handlers/               # Barcha bot bo'limlari
│   │   │   ├── start.py            # /start, interaktiv progress-barli ro'yxatdan o'tish
│   │   │   ├── admin/              # Admin boshqaruv panellari
│   │   │   │   ├── admin_menu.py   # Asosiy admin menyusi
│   │   │   │   ├── excel_handler.py# Excel import/export va shablonlar
│   │   │   │   ├── test_creator.py # Test yaratish ustasi
│   │   │   │   ├── tests_manage.py # Testlarni tahrirlash/yopish
│   │   │   │   ├── students_manage.py # O'quvchilar ro'yxati/qidiruv/bloklash
│   │   │   │   ├── statistics.py   # Tizim statistikasi
│   │   │   │   ├── broadcast_handler.py # Xabar tarqatish
│   │   │   │   ├── channels_manage.py   # Majburiy a'zolik kanallari
│   │   │   │   ├── groups_manage.py     # Guruhlar boshqaruvi
│   │   │   │   ├── admins_manage.py     # Qo'shimcha adminlar
│   │   │   │   ├── support_manage.py    # Murojaatlar
│   │   │   │   └── settings_manage.py   # Tizim sozlamalari & Zaxira
│   │   │   └── student/            # O'quvchi bo'limlari
│   │   │       ├── main_menu.py    # RPG Profil, sozlamalar
│   │   │       ├── quick_check.py  # Tezkor test tekshirish (TEST-101 ABCD...)
│   │   │       ├── test_solver.py  # Interaktiv test yechish (jonli counter)
│   │   │       ├── ratings.py      # Jonli paginatsiyali reyting va PDF export
│   │   │       ├── results.py      # Natijalar tarixi va sertifikatlar
│   │   │       ├── certificates.py # Sertifikat olish va PDF generatsiya
│   │   │       ├── guide.py        # Qo'llanma
│   │   │       └── support.py      # Adminga xabar yozish
│   │   ├── keyboards/              # Inline va Reply tugmalar
│   │   ├── middlewares/            # Bazaga ulanish, xavfsizlik, xatolik tutuvchi
│   │   └── states/                 # FSM holatlari (Registration, Test, Admin)
│   ├── database/
│   │   ├── session.py              # Async SQLAlchemy sessiyasi
│   │   ├── models/                 # Baza jadvallari (User, Test, Result, Certificate...)
│   │   └── repositories/           # Bazaga so'rov yuboruvchi qatlam
│   └── services/
│       ├── scoring_service.py      # Baholash, foizlar, RPG darajalar
│       ├── profanity_service.py    # Nomaqbul so'zlar filtri (Anti-Profanity)
│       ├── excel_service.py        # Excel shablon, import/export, PDF ro'yxatlar
│       ├── certificate_service.py  # PDF sertifikat yasovchi
│       ├── scheduler_service.py    # Avtomatik muddat tugashini tekshiruvchi fon xizmati
│       └── auth_service.py         # Avtorizatsiya va adminlikni tekshirish
└── storage/
    ├── test_platform.db            # Asosiy SQLite ma'lumotlar bazasi
    ├── exports/                    # PDF va Excel eksport fayllari
    ├── uploads/                    # Yuklangan test fayllari va PDFlar
    └── data/fsm_storage.json       # Doimiy FSM xotirasi
```

---

## 4. 🌟 Loyihada Amalga Oshirilgan Oxirgi Yangiliklar:

1. **🛡 Anti-Profanity (Nomaqbul so'zlar filtri):** O'zbekcha, Ruscha, Inglizcha haqoratli so'zlar va leetspeak (`j a l a b`, `d4lb4y0b`) bilan ro'yxatdan o'tishni to'liq bloklaydi.
2. **📊 Mukammal Excel Boshqaruvi:** Savollar uchun tayyor namunali shablon generatsiyasi (`.xlsx`), Krill-Lotin avtomatik konvertatsiyasi, 5000 tagacha natijalarni bir zumda eksport qilish.
3. **🎮 Gamifikatsiyalashgan Registratsiya:** 4 bosqichli vizual progress bar (`25% -> 50% -> 75% -> 100%`).
4. **⏱ Jonli Test Kartasi:** Rangli vaqt indikatori (`🟢 -> 🟡 -> 🔴`), jonli savol progress bari (`[████░░░░]`).
5. **🏆 Jonli Reyting & Paginatsiya:** 10 tadan sahifalash, `👈 (Siz)` belgisi, yulduzli baholar va to'liq A4 PDF reyting exporti.
6. **💾 Backup Tizimi:** Admin panelidan bazaning to'liq zaxira nusxasini (`.db`) 1 tugma bilan yuklab olish.
7. **🔒 Anti-Cheat & Qat'iy Vaqt Nazorati:** Belgilangan muddatdan keyin yuborilgan javoblar qabul qilinmaydi.

---

## 5. 🤖 Boshqa Kompyuterdan Yangi AI (Chat) bilan ishlaganda:
Ushbu papkani ochib, yangi AI agentiga:
*"Ushbu loyiha telegram_test_platform boti. LOYIHA_QOLLANMASI.md faylini o'qib chiq va shunga asosan davom etamiz"* deb yozsangiz, AI botni 100% tushunib, ishni davom ettiradi!
