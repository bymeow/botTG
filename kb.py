from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Темы ЕГЭ")], # Большая кнопка сверху
            [KeyboardButton(text="📉 Мой прогресс"), KeyboardButton(text="🔄 Новый диалог")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери раздел или задай вопрос..."
    )
    return keyboard
