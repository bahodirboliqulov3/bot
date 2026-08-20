from typing import Dict, List, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.database.models.test import Test, TestStatus


def get_channel_subscription_keyboard(channels: list) -> InlineKeyboardMarkup:
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(text=f"📢 {ch.title}", url=ch.invite_link)])
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_channel_subs")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_test_item_keyboard(test_id: int, is_saved: bool = False, is_author: bool = False) -> InlineKeyboardMarkup:
    save_text = "🔖 Saqlanganlardan o'chirish" if is_saved else "🔖 Testni saqlash"
    buttons = [
        [InlineKeyboardButton(text="▶️ Testni boshlash", callback_data=f"start_test:{test_id}")],
        [InlineKeyboardButton(text=save_text, callback_data=f"toggle_save:{test_id}")],
    ]
    if is_author:
        buttons.append([
            InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"edit_test:{test_id}"),
            InlineKeyboardButton(text="🗑 O‘chirish", callback_data=f"delete_test:{test_id}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quiz_question_keyboard(
    attempt_id: int,
    current_index: int,
    total_questions: int,
    selected_option: Optional[str] = None,
    allow_backtracking: bool = True
) -> InlineKeyboardMarkup:
    # Options A, B, C, D
    options = ["A", "B", "C", "D"]
    opt_buttons = []
    for opt in options:
        prefix = "🔘"
        if selected_option == opt:
            prefix = "🟢"
        opt_buttons.append(
            InlineKeyboardButton(
                text=f"{prefix} {opt}",
                callback_data=f"ans:{attempt_id}:{current_index}:{opt}"
            )
        )

    nav_row = []
    if allow_backtracking and current_index > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"nav:{attempt_id}:{current_index - 1}"))
    
    nav_row.append(InlineKeyboardButton(text="📋 Savollar", callback_data=f"overview:{attempt_id}"))

    if current_index < total_questions:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"nav:{attempt_id}:{current_index + 1}"))

    bottom_row = [
        InlineKeyboardButton(text="🏁 Testni yakunlash", callback_data=f"finish_confirm:{attempt_id}")
    ]

    keyboard = [
        opt_buttons[:2],
        opt_buttons[2:],
        nav_row,
        bottom_row
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_quiz_overview_keyboard(attempt_id: int, total_questions: int, answered_indices: set[int]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i in range(1, total_questions + 1):
        status_icon = "✅" if i in answered_indices else "▫️"
        row.append(InlineKeyboardButton(text=f"{status_icon} {i}", callback_data=f"nav:{attempt_id}:{i}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text="🏁 Testni yakunlash", callback_data=f"finish_confirm:{attempt_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quiz_finish_confirm_keyboard(attempt_id: int, current_index: int = 1) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yakunlash", callback_data=f"finish_test:{attempt_id}"),
                InlineKeyboardButton(text="↩️ Davom etish", callback_data=f"nav:{attempt_id}:{current_index}")
            ]
        ]
    )


def get_result_actions_keyboard(result_id: int, test_id: int, share_text: str = "") -> InlineKeyboardMarkup:
    import urllib.parse
    if not share_text:
        share_url = f"https://t.me/share/url?url=https://t.me/tekshiruv2_bot&text={urllib.parse.quote('Telegram Test Platformasida o‘z bilimingizni sinab ko‘ring! 🎯')}"
    else:
        share_url = f"https://t.me/share/url?url=https://t.me/tekshiruv2_bot&text={urllib.parse.quote(share_text)}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔎 Xatolarni ko‘rish", callback_data=f"view_mistakes:{result_id}"),
                InlineKeyboardButton(text="📄 PDF natija", callback_data=f"pdf_result:{result_id}")
            ],
            [
                InlineKeyboardButton(text="🎉 Sertifikat olish", callback_data=f"get_cert:{result_id}"),
                InlineKeyboardButton(text="📤 Ulashish", url=share_url)
            ]
        ]
    )


def get_confirmation_keyboard(confirm_action: str, cancel_action: str = "cancel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha / Tasdiqlash", callback_data=confirm_action),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=cancel_action)
            ]
        ]
    )


def get_pagination_keyboard(prefix: str, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"{prefix}:page:{current_page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"{prefix}:page:{current_page + 1}"))
    buttons.append(nav_row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)
