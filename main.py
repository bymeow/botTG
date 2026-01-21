from aiohttp import web
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from groq import Groq
import os
import styles
from memory import MemoryManager

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# --- Класс твоего ИИ-тютора ---
class SmartAITutor:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.memory = MemoryManager()
        self.system_prompt = (
            "Ты — опытный репетитор по информатике (ЕГЭ). "
            "Отвечай структурировано. Используй заголовки и списки. "
            "Не давай решение сразу, задавай наводящие вопросы."
        )

    async def get_ai_response(self, user_id: int, message: str):
        uid = str(user_id)
        # 1. Сохраняем вопрос ученика
        self.memory.add_message_to_history(uid, "user", message)
        
        # 2. Загружаем контекст
        history = self.memory.get_recent_context(uid)
        messages = [{"role": "system", "content": self.system_prompt}] + history

        # 3. Делаем запрос к ИИ
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7
        ))
        
        ai_text = response.choices[0].message.content
        
        # 4. Сохраняем ответ бота
        self.memory.add_message_to_history(uid, "assistant", ai_text)
        return ai_text

# --- Инициализация (Глобальные переменные) ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_KEY")

# Создаем объекты один раз
bot = Bot(token=TOKEN)
dp = Dispatcher()
tutor = SmartAITutor(api_key=GROQ_API_KEY) 

# --- Хендлеры ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет! Я готов к работе. Напиши любой вопрос по информатике.")

@dp.message()
async def chat_handler(message: types.Message):
    # Показываем статус "печатает..."
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Получаем ответ от ИИ через объект tutor, который мы создали выше
        raw_answer = await tutor.get_ai_response(message.from_user.id, message.text)
        
        # Форматируем текст через твой модуль styles
        pretty_answer = styles.format_bot_response(raw_answer)
        
        # Отправляем ответ пользователю
        await message.answer(pretty_answer, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        # Если ошибка, сообщаем пользователю
        await message.answer(f"⚠️ Произошла ошибка: {e}. Попробуй позже.")

# --- Мини-сервер для Koyeb ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    # 1. Сначала запускаем веб-сервер, чтобы Koyeb сразу увидел порт 8000
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    
    print("🤖 БОТ ЗАПУЩЕН и сервер на порту 8000 работает!")
    
    # 2. Только ПОСЛЕ запуска сервера начинаем слушать Телеграм
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
       

