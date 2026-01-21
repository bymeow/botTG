from aiohttp import web
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from groq import Groq
import os
import styles
from memory import MemoryManager
import re

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# --- Класс твоего ИИ-тютора ---
class SmartAITutor:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.memory = MemoryManager()
        self.system_prompt = (
            "Ты — опытный репетитор по информатике (ЕГЭ). "
            "ВАЖНО: НИКОГДА не используй символы решётки (#, ##, ###) для заголовков. "
            "НИКОГДА не используй HTML-теги (<b>, </b>, <i>, </i> и любые другие). "
            "Для выделения текста используй ТОЛЬКО звёздочки: *текст* для курсива, **текст** для жирного. "
            "Отвечай структурировано, используй списки с дефисами (-) или цифрами. "
            "Активно используй эмодзи для наглядности: 📚 теория, 💡 подсказки, "
            "✅ правильно, ❌ ошибка, ❓ вопросы, 🎯 важное, 📝 примеры, 🔢 формулы, ⚠️ частые ошибки. "
            "Не давай решение сразу, задавай наводящие вопросы."
        )

    def clean_response(self, text: str) -> str:
        """Удаляет все запрещённые символы из ответа ИИ"""
        # Удаляем все HTML-теги
        text = re.sub(r'<[^>]+>', '', text)
        
        # Удаляем решётки в начале строк (заголовки Markdown)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Удаляем решётки в середине текста (на всякий случай)
        text = re.sub(r'#{1,6}\s+', '', text)
        
        return text

    async def get_ai_response(self, user_id: int, message: str):
        uid = str(user_id)
        # 1. Сохраняем вопрос
        self.memory.add_message_to_history(uid, "user", message)
        
        # 2. Загружаем контекст
        history = self.memory.get_recent_context(uid)
        messages = [{"role": "system", "content": self.system_prompt}] + history

        # 3. Делаем запрос
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7
        ))
        
        ai_text = response.choices[0].message.content
        
        # 4. Очищаем ответ от запрещённых символов
        ai_text = self.clean_response(ai_text)
        
        # 5. Сохраняем очищенный ответ
        self.memory.add_message_to_history(uid, "assistant", ai_text)
        return ai_text

# --- Инициализация ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()
tutor = SmartAITutor(api_key=GROQ_API_KEY) 

# --- Хендлеры ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    welcome_text = (
        "👋 Привет! Я твой ИИ-репетитор по информатике!\n\n"
        "📚 Готов помочь с подготовкой к ЕГЭ\n"
        "💡 Задавай любые вопросы по темам\n"
        "🎯 Разберём сложные задачи вместе!"
    )
    await message.answer(welcome_text)

@dp.message()
async def chat_handler(message: types.Message):
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Получаем очищенный ответ от ИИ
        raw_answer = await tutor.get_ai_response(message.from_user.id, message.text)
        
        # Форматируем через styles (если там есть дополнительная обработка)
        pretty_answer = styles.format_bot_response(raw_answer)
        
        # Дополнительная очистка на всякий случай
        pretty_answer = tutor.clean_response(pretty_answer)
        
        # Отправляем с обычным Markdown (самый надёжный)
        await message.answer(pretty_answer, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        # Если Markdown сломается, отправляем без форматирования
        try:
            await message.answer(raw_answer)
        except:
            await message.answer("⚠️ Произошла ошибка. Попробуй переформулировать вопрос.")

# --- Сервер для Koyeb ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    
    print("Бот запущен! Сервер работает на порту 8000")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
