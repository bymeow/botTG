from aiohttp import web
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import kb
from groq import Groq
import os
import re
from memory import MemoryManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация бота и Groq
bot = Bot(token=os.getenv("TG_TOKEN"))
dp = Dispatcher()

class SmartAITutor:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.memory = MemoryManager()
        # Жесткая установка: только текст и смайлики
        self.system_prompt = (
            "Ты — опытный репетитор по информатике (ЕГЭ). "
            "ПИШИ ТОЛЬКО ОБЫЧНЫМ ТЕКСТОМ БЕЗ ВЫДЕЛЕНИЙ. "
            "ЗАПРЕЩЕНО: **жирный**, *курсив*, # решетки и любые HTML-теги. "
            "ОБЯЗАТЕЛЬНО используй смайлики: 📚, 💡, ✅, ❌, 🎯. "
            "Разделяй мысли просто новыми строками."
        )

    def clean_text(self, text: str) -> str:
        """Удаляет любой мусор, если ИИ ослушался"""
        text = re.sub(r'<[^>]+>', '', text)  # Убираем HTML
        text = text.replace('**', '').replace('*', '').replace('`', '')
        text = re.sub(r'#{1,6}\s+', '', text)
        return text.strip()

    async def get_ai_response(self, user_id: int, message: str):
        uid = str(user_id)
        self.memory.add_message_to_history(uid, "user", message)
        history = self.memory.get_recent_context(uid)
        messages = [{"role": "system", "content": self.system_prompt}] + history

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=messages, 
                temperature=0.7
            ))
            ai_text = self.clean_text(response.choices[0].message.content)
            self.memory.add_message_to_history(uid, "assistant", ai_text)
            return ai_text
        except Exception as e:
            logging.error(f"Groq Error: {e}")
            return "⚠️ Ошибка связи с сервером. Попробуй еще раз!"

tutor = SmartAITutor(api_key=os.getenv("GROQ_KEY"))

# --- Хендлеры ---
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    await msg.answer(
        "👋 Привет! Я твой ИИ-репетитор по информатике!\n\n"
        "📚 Помогу с ЕГЭ | 💡 Объясню просто\n\n"
        "⬇️ Используй кнопки меню",
        reply_markup=kb.main_menu()
    )

@dp.message(lambda m: m.text == "🔄 Новый диалог")
async def reset_history(msg: types.Message):
    data = tutor.memory.load_user_data(msg.from_user.id)
    data["conversation_history"] = []
    tutor.memory.save_user_data(msg.from_user.id, data)
    await msg.answer("🧹 История диалога очищена!")

@dp.message(lambda m: m.text == "📚 Темы ЕГЭ")
async def show_topics(msg: types.Message):
    await msg.answer(
        "📚 Темы ЕГЭ по информатике:\n\n"
        "1. Системы счисления 🔢\n"
        "2. Логика 🧮\n"
        "3. Алгоритмы 🔄\n"
        "4. Программирование 💻\n"
        "5. Сети 🌐\n\n"
        "Задай вопрос по любой из тем!"
    )

@dp.message(lambda m: m.text == "🤖 Выбор модели")
async def choose_model(msg: types.Message):
    await msg.answer("В текущей версии доступ
