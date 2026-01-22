from aiohttp import web
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import kb
from groq import Groq
import google.generativeai as genai
import os
import re
from memory import MemoryManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model_flash = genai.GenerativeModel('gemini-1.5-flash')
model_pro = genai.GenerativeModel('gemini-1.5-pro')

bot = Bot(token=os.getenv("TG_TOKEN"))
dp = Dispatcher()

# --- ИИ-тютор ---
class SmartAITutor:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.memory = MemoryManager()
        self.system_prompt = (
            "Ты — опытный репетитор по информатике (ЕГЭ). "
            "ПИШИ ТОЛЬКО ОБЫЧНЫМ ТЕКСТОМ БЕЗ ВЫДЕЛЕНИЙ. "
            "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО: жирный шрифт (**), курсив (*), решетки (#) и любые теги. "
            "ОБЯЗАТЕЛЬНО ИСПОЛЬЗУЙ ЭМОДЗИ: 📚, 💡, ✅, ❌, 🎯. "
            "Отвечай структурированно, разделяя мысли просто новыми строками."
        )

    def clean_response(self, text: str) -> str:
        """Удаляет символы форматирования, если ИИ их все же добавил"""
        text = re.sub(r'<[^>]+>', '', text)  # Удаляем HTML
        text = re.sub(r'#{1,6}\s+', '', text)  # Удаляем решётки
        text = text.replace('**', '').replace('*', '') # Удаляем Markdown жирный/курсив
        return text.strip()

    async def get_ai_response(self, user_id: int, message: str):
        uid = str(user_id)
        self.memory.add_message_to_history(uid, "user", message)
        history = self.memory.get_recent_context(uid)
        messages = [{"role": "system", "content": self.system_prompt}] + history

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.client.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=messages, temperature=0.7
            ))
            ai_text = self.clean_response(response.choices[0].message.content)
            self.memory.add_message_to_history(uid, "assistant", ai_text)
            return ai_text
        except Exception as e:
            logging.error(f"Groq ошибка: {e}")
            return "⚠️ Ошибка Groq. Попробуй ещё раз!"

tutor = SmartAITutor(api_key=os.getenv("GROQ_KEY"))

# --- Вспомогательные функции Gemini ---
async def get_gemini_response(prompt, model_type="flash"):
    try:
        selected_model = model_pro if model_type == "pro" else model_flash
        instruction = (
            "Ты репетитор по информатике. Используй эмодзи (📚, ✅, 💡). "
            "ПИШИ ТОЛЬКО ОБЫЧНЫМ ТЕКСТОМ. ЗАПРЕЩЕН ЖИРНЫЙ ШРИФТ И КУРСИВ. "
            f"Вопрос: {prompt}"
        )
        # Вызов Gemini через поток
        response = await asyncio.to_thread(selected_model.generate_content, instruction)
        
        if not response.text:
            return "⚠️ Gemini прислала пустой ответ."
            
        return tutor.clean_response(response.text)
    except Exception as e:
        logging.error(f"Gemini ошибка: {e}")
        return "⚠️ Ошибка Gemini (лимит 2 зап/мин для Pro). Попробуй позже!"

# --- Хендлеры ---
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    await msg.answer(
        "👋 Привет! Я твой ИИ-репетитор по информатике!\n\n"
        "🎓 Помогу с ЕГЭ | 💡 Объясню просто | 📝 Разберу задачи\n\n"
        "⬇️ Используй кнопки меню",
        reply_markup=kb.main_menu()
    )

@dp.message(lambda m: m.text == "🤖 Выбор модели")
async def choose_model(msg: types.Message):
    data = tutor.memory.load_user_data(msg.from_user.id)
    current = data.get("current_model", "groq")
    models = {"groq": "Groq", "flash": "Flash", "pro": "Pro"}
    await msg.answer(
        f"Сейчас: {models.get(current)}\nВыбери модель:",
        reply_markup=kb.model_selector()
    )

@dp.callback_query(lambda c: c.data.startswith('set_model_'))
async def set_model(cq: types.CallbackQuery):
    model = cq.data.split('_')[2]
    data = tutor.memory.load_user_data(cq.from_user.id)
    data["current_model"] = model
    tutor.memory.save_user_data(cq.from_user.id, data)
    await cq.answer(f"Модель: {model.upper()}")
    await cq.message.edit_text(f"✅ Модель изменена на: {model.upper()}")

@dp.message(lambda m: m.text == "📚 Темы ЕГЭ")
async def show_topics(msg: types.Message):
    await msg.answer(
        "📚 Темы ЕГЭ:\n\n"
        "1. Системы счисления 🔢\n"
        "2. Алгебра логики 🧮\n"
        "3. Алгоритмы 🔄\n"
        "4. Программирование 💻\n"
        "5. Сети 🌐\n\n"
        "💡 Просто напиши вопрос!"
    )

@dp.message(lambda m: m.text == "🔄 Новый диалог")
async def reset_history(msg: types.Message):
    data = tutor.memory.load_user_data(msg.from_user.id)
    data["conversation_history"] = []
    tutor.memory.save_user_data(msg.from_user.id, data)
    await msg.answer("🧹 История очищена! ✨")

@dp.message(lambda m: m.text == "📉 Мой прогресс")
async def show_progress(msg: types.Message):
    data = tutor.memory.load_user_data(msg.from_user.id)
    mistakes = data.get("learning_progress", {}).get("common_mistakes", [])
    text = "📊 Прогресс:\n✅ Ошибок нет" if not mistakes else f"📊 Ошибки:\n{mistakes}"
    await msg.answer(text)

# --- Основной чат (БЕЗ MARKDOWN) ---
@dp.message()
async def chat_handler(msg: types.Message):
    await bot.send_chat_action(msg.chat.id, "typing")
    data = tutor.memory.load_user_data(msg.from_user.id)
    model = data.get("current_model", "groq")

    try:
        if model == "pro":
            answer = await get_gemini_response(msg.text, "pro")
        elif model == "flash":
            answer = await get_gemini_response(msg.text, "flash")
        else:
            answer = await tutor.get_ai_response(msg.from_user.id, msg.text)
        
        # Отправляем как обычный текст без parse_mode
        await msg.answer(answer)
        
    except Exception as e:
        logging.error(f"Ошибка чата: {e}")
        await msg.answer("⚠️ Ошибка. Попробуй сменить модель или начать новый диалог.")

# --- Запуск сервера для Koyeb ---
async def main():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8000))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
