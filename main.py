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

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация бота и Groq
# Убедись, что в Koyeb добавлены TG_TOKEN и GROQ_KEY
bot = Bot(token=os.getenv("TG_TOKEN"))
dp = Dispatcher()

class SmartAITutor:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.memory = MemoryManager()
        # Инструкция: только текст и смайлики, НИКАКОГО жирного шрифта
        self.system_prompt = (
            "Ты — опытный репетитор по информатике (ЕГЭ). "
            "ПИШИ ТОЛЬКО ОБЫЧНЫМ ТЕКСТОМ БЕЗ ВЫДЕЛЕНИЙ. "
            "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО: жирный шрифт (**), курсив (*), решетки (#) и любые теги <b>. "
            "ОБЯЗАТЕЛЬНО используй смайлики: 📚, 💡, ✅, ❌, 🎯, 🔢, 💻. "
            "Отвечай структурированно, просто разделяя мысли новыми строками."
        )

    def clean_text(self, text: str) -> str:
        """Удаляет любой мусор и форматирование"""
        text = re.sub(r'<[^>]+>', '', text)  # Убираем HTML-теги
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
        "⬇️ Используй кнопки меню ниже",
        reply_markup=kb.main_menu()
    )

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

@dp.message(lambda m: m.text == "🔄 Новый диалог")
async def reset_history(msg: types.Message):
    data = tutor.memory.load_user_data(msg.from_user.id)
    data["conversation_history"] = []
    tutor.memory.save_user_data(msg.from_user.id, data)
    await msg.answer("🧹 История диалога очищена! Давай начнем заново.")

@dp.message(lambda m: m.text == "📉 Мой прогресс")
async def show_progress(msg: types.Message):
    data = tutor.memory.load_user_data(msg.from_user.id)
    count = len(data.get("conversation_history", []))
    await msg.answer(f"📊 Твой прогресс:\n💬 Сообщений в памяти: {count}\n✅ Ты молодец, продолжаем!")

# --- Главный чат (ОТПРАВКА БЕЗ ПАРС-МОДА) ---

@dp.message()
async def chat_handler(msg: types.Message):
    await bot.send_chat_action(msg.chat.id, "typing")
    
    # Получаем ответ от ИИ
    answer = await tutor.get_ai_response(msg.from_user.id, msg.text)
    
    # ОТПРАВЛЯЕМ ОТВЕТ И ОБЯЗАТЕЛЬНО ДОБАВЛЯЕМ reply_markup
    # Теперь кнопки будут вылезать у каждого, кто напишет боту
    await msg.answer(answer, reply_markup=kb.main_menu())

# --- Настройка сервера для Koyeb ---

async def main():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is Live 🤖"))
    runner = web.AppRunner(app)
    await runner.setup()
    # Koyeb сам подставит нужный PORT
    port = int(os.getenv('PORT', 8000))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    
    logging.info(f"🚀 Бот запущен на порту {port}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
