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
        # В промпте просим использовать жирный шрифт (**текст**) вместо заголовков (#), 
        # чтобы старый Маркдаун их понимал красиво.
        self.system_prompt = (
    "Ты — опытный репетитор по информатике (ЕГЭ). "
    "ОТВЕЧАЙ СТРОГО БЕЗ ИСПОЛЬЗОВАНИЯ СИМВОЛОВ # (решеток). "
    "Для заголовков используй только жирный шрифт (выделяй текст так: **Заголовок**). "
    "Используй списки и эмодзи 📚, 💡, ✅ для наглядности."
)
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
        
        # 4. Сохраняем ответ
        self.memory.add_message_to_history(uid, "assistant", ai_text)
        return ai_text

# --- Инициализация ---
TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()
tutor = SmartAITutor(api_key=GROQ_API_KEY) 

# --- Хендлеры ---

@dp.message()
async def chat_handler(message: types.Message):
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        raw_answer = await tutor.get_ai_response(message.from_user.id, message.text)
        pretty_answer = styles.format_bot_response(raw_answer)
        
        # СТАВИМ HTML. Твой текст уже содержит <b>, поэтому это всё исправит!
        await message.answer(pretty_answer, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        # Если HTML сломается, отправим просто текст.
        await message.answer(pretty_answer)
        # --- ФИКС ---
        # Используем обычный "Markdown" (без V2). 
        # Он самый надежный: смайлики работают, жирный текст работает.
        await message.answer(pretty_answer, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"❌ Ошибка разметки: {e}")
        # Если вдруг Маркдаун все равно сломается (редко), 
        # отправляем чистый текст, чтобы ты точно получил ответ!
        await message.answer(pretty_answer)

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
    
    print("🤖 Бот запущен! Сервер работает на порту 8000")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
