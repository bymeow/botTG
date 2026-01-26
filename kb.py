from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎓 Выбрать предмет")],  # Новая главная кнопка
            [KeyboardButton(text="📉 Мой прогресс"), KeyboardButton(text="🔄 Новый диалог")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери предмет или задай вопрос..."
    )
    return keyboard

def subjects_inline():
    # Создаем кнопки в 2 колонки для красоты
    buttons = [
        [InlineKeyboardButton(text="📐 Математика", callback_data="set_subj_math"), InlineKeyboardButton(text="💻 Информатика", callback_data="set_subj_info")],
        [InlineKeyboardButton(text="🇷🇺 Русский язык", callback_data="set_subj_rus"), InlineKeyboardButton(text="📜 Обществознание", callback_data="set_subj_soc")],
        [InlineKeyboardButton(text="⚛️ Физика", callback_data="set_subj_phys"), InlineKeyboardButton(text="🧪 Химия", callback_data="set_subj_chem")],
        [InlineKeyboardButton(text="🧬 Биология", callback_data="set_subj_bio"), InlineKeyboardButton(text="🏺 История", callback_data="set_subj_hist")],
        [InlineKeyboardButton(text="🇬🇧 Английский", callback_data="set_subj_eng"), InlineKeyboardButton(text="🌍 География", callback_data="set_subj_geo")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
