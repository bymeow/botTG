from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню (кнопки под полем ввода)
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

# Меню выбора нейросети (кнопки под сообщением)
def model_selector():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            # callback_data должна совпадать с тем, что мы ловим в main.py
            InlineKeyboardButton(text="⚡ Llama 3 (Groq)", callback_data="set_model_groq"),
        ],
        [
            InlineKeyboardButton(text="🚀 Gemini Flash", callback_data="set_model_flash"),
            InlineKeyboardButton(text="🧠 Gemini PRO", callback_data="set_model_pro")
        ]
    ])
    return keyboard
