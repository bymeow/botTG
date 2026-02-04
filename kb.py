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


def get_language_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en"),
            InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang_es")
        ],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
    ])
    return keyboard

def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 Выбрать предмет", callback_data="choose_subject")],
        [InlineKeyboardButton(text="🌐 Язык / Language", callback_data="lang_menu")] # <-- НОВАЯ КНОПКА
    ])
    return keyboard

# Обработка выбора языка
@dp.callback_query(lambda c: c.data.startswith('lang_'))
async def set_language(callback: types.CallbackQuery):
    lang_code = callback.data.split('_')[1]
    
    # Инструкции для ИИ на разных языках
    prompts = {
        "ru": "Перейди на русский язык. Общайся как крутой наставник-бро.",
        "en": "Switch to English. Speak like a cool mentor and friend.",
        "es": "Cambia al español. Habla como un mentor y amigo genial."
    }
    
    # Текст подтверждения
    confirm = {
        "ru": "Принято! Теперь ботаем на русском 🇷🇺",
        "en": "Got it! English mode is on 🇺🇸",
        "es": "¡Vale! Ahora hablamos español 🇪🇸"
    }

    # Записываем команду в память бота (он увидит это как системную установку)
    user_id = callback.from_user.id
    ai_tutor.memory.add_message_to_history(str(user_id), "system", prompts.get(lang_code))
    
    await callback.message.answer(confirm.get(lang_code))
    await callback.answer()
