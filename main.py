from aiohttp import web
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import kb  # Импортируем наш файл с кнопками
from groq import Groq
import google.generativeai as genai
import os
import styles
from memory import MemoryManager
import re

# --- Настройки и инициализация ---
logging.basicConfig(level=logging.INFO)

# Инициализация Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model_flash = genai.GenerativeModel('gemini-1.5-flash')
model_pro = genai.GenerativeModel('gemini-1.5-pro')

TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()


# --- Класс  ИИ-тютора (с возвращенными эмодзи) ---
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
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'#{1,6}\s+', '', text)
        return text

    async def get_ai_response(self, user_id: int, message: str):
        uid = str(user_id)
        self.memory.add_message_to_history(uid, "user", message)
        history = self.memory.get_recent_context(uid)
        messages = [{"role": "system", "content": self.system_prompt}] + history

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7
        ))
        
        ai_text = self.clean_response(response.choices[0].message.content)
        self.memory.add_message_to_history(uid, "assistant", ai_text)
        return ai_text

tutor = SmartAITutor(api_key=GROQ_API_KEY)

# --- Вспомогательные функции ---
async def get_gemini_response(prompt, model_type="flash"):
    selected_model = model_pro if model_type == "pro" else model_flash
    response = await asyncio.to_thread(selected_model.generate_content, prompt)
    return response.text

# --- Хендлеры команд и меню ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    welcome_text = (
        "👋 <b>Привет! Я твой ИИ-репетитор по информатике!</b>\n\n"
        "📚 Готов помочь с подготовкой к ЕГЭ\n⬇️ <i>Используй кнопки ниже:</i>"
    )
    await message.answer(welcome_text, reply_markup=kb.main_menu(), parse_mode="HTML")

@dp.message(lambda message: message.text == "🤖 Выбор модели")
async def choose_model(message: types.Message):
    user_id = message.from_user.id
    data = tutor.memory.load_user_data(user_id)
    current_model = data.get("current_model", "groq")
    await message.answer(
        f"Сейчас активна модель: <b>{current_model.upper()}</b>\nВыбери мозги:",
        reply_markup=kb.model_selector(),
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data.startswith('set_model_'))
async def process_model_selection(callback_query: types.CallbackQuery):
    model_name = callback_query.data.split('_')[2]
    user_id = callback_query.from_user.id
    data = tutor.memory.load_user_data(user_id)
    data["current_model"] = model_name
    tutor.memory.save_user_data(user_id, data)
    await callback_query.answer(f"Модель изменена на {model_name.upper()}!")
    await callback_query.message.edit_text(f"✅ Теперь я использую: <b>{model_name.upper()}</b>", parse_mode="HTML")

@dp.message(lambda message: message.text == "📚 Темы ЕГЭ")
async def show_topics(message: types.Message):
    topics_text = "<b>Ключевые темы ЕГЭ:</b>\n1. Логика\n2. Алгоритмы\n3. Python\n4. Сети"
    await message.answer(topics_text, parse_mode="HTML")

@dp.message(lambda message: message.text == "🔄 Новый диалог")
async def reset_history(message: types.Message):
    user_id = message.from_user.id
    data = tutor.memory.load_user_data(user_id)
    data["conversation_history"] = []
    tutor.memory.save_user_data(user_id, data)
    await message.answer("🧼 <b>История очищена!</b>", parse_mode="HTML")

@dp.message(lambda message: message.text == "📉 Мой прогресс")
async def show_progress(message: types.Message):
    user_id = message.from_user.id
    data = tutor.memory.load_user_data(user_id)
    mistakes = data.get("learning_progress", {}).get("common_mistakes", [])
    response = "Твой прогресс чист!" if not mistakes else f"Твои ошибки: {', '.join(mistakes)}"
    await message.answer(f"<b>{response}</b>", parse_mode="HTML")

# --- Основной обработчик чата ---
@dp.message()
async def chat_handler(message: types.Message):
    await bot.send_chat_action(message.chat.id, "typing")
    user_id = message.from_user.id
    data = tutor.memory.load_user_data(user_id)
    current_model = data.get("current_model", "groq")
    raw_answer = ""

    try:
        if current_model == "pro":
            raw_answer = await get_gemini_response(message.text, model_type="pro")
        elif current_model == "flash":
            raw_answer = await get_gemini_response(message.text, model_type="flash")
        else:
            raw_answer = await tutor.get_ai_response(user_id, message.text)
            
        pretty_answer = styles.format_bot_response(raw_answer)
        await message.answer(pretty_answer, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        try:
            # Пытаемся отправить текст без форматирования, если Markdown подвел
            await message.answer(raw_answer if raw_answer else "⚠️ Ошибка связи с ИИ.")
        except:
            await message.answer("⚠️ Произошла ошибка. Попробуй позже.")

# --- Запуск сервера для Koyeb ---
async def main():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    
    logging.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
