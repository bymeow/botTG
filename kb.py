from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    # Создаем кнопки
    btn_model = KeyboardButton(text="🤖 Выбор модели")
    btn_topics = KeyboardButton(text="📚 Темы ЕГЭ")
    btn_progress = KeyboardButton(text="📉 Мой прогресс")
    btn_reset = KeyboardButton(text="🔄 Новый диалог")

    # Собираем клавиатуру (2 кнопки в ряду)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [btn_model, btn_topics],
            [btn_progress, btn_reset]
        ],
        resize_keyboard=True # Чтобы кнопки были маленькими и аккуратными
    )
    return keyboard

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

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
