from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🤖 Выбор модели"), KeyboardButton(text="📚 Темы ЕГЭ")],
            [KeyboardButton(text="📉 Мой прогресс"), KeyboardButton(text="🔄 Новый диалог")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери раздел или задай вопрос..."
    )
    return keyboard

def model_selector():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Llama 3 (Groq)", callback_data="set_model_groq")],
        [
            InlineKeyboardButton(text="🚀 Gemini Flash", callback_data="set_model_flash"),
            InlineKeyboardButton(text="🧠 Gemini PRO", callback_data="set_model_pro")
        ]
    ])
    return keyboard
