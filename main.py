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

# Настройка Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model_flash = genai.GenerativeModel('gemini-1.5-flash')
model_pro = genai.GenerativeModel('gemini-1.5-pro')

bot = Bot(token=os.getenv("TG_TOKEN"))
dp = Dispatcher()

# --- Класс тютора БЕЗ форматирования ---
class SmartAITutor:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.memory = MemoryManager()
        # Прямо запрещаем любой жирный текст в инструкции
        self.system_prompt = (
            "Ты — опытный репетитор по информатике (ЕГЭ). "
            "ПИШИ ТОЛЬКО ОБЫЧНЫМ ТЕКСТОМ. "
            "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать: **, __, <b>, <i>, #. "
            "ИСПОЛЬЗУЙ ЭМОДЗИ для оформления: 📚, 💡, ✅, ❌, 🎯. "
            "Разделяй мысли просто переносом строки."
        )

    def clean_all(self, text: str) -> str:
        """Полная очистка от любого мусора"""
        text = re.sub(r'<[^>]+>', '', text)  # Удаляет <b>, </b> и т.д.
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
                model="llama-3.3-70b-versatile", messages=messages, temperature=0.7
            ))
            ai_text = self.clean_all(response.choices[0].message.content)
            self.memory.add_message_to_history(uid, "assistant", ai_text)
            return ai_text
        except Exception as e:
            logging.error(f"Groq error: {e}")
            return "⚠️ Ошибка связи. Попробуй еще раз."

tutor = SmartAITutor(api_key=os.getenv("GROQ_KEY"))

# --- Исправленная функция Gemini ---
async def get_gemini_response(prompt, model_type="flash"):
    try:
        selected_model = model_pro if model_type == "pro" else model_flash
        instruction = (
            "Ты репетитор по информатике. Используй смайлики. "
            "НЕ ИСПОЛЬЗУЙ жирный шрифт или HTML. Пиши просто текст. "
            f"Вопрос: {prompt}"
        )
        response = await asyncio.to_thread(selected_model.generate_content, instruction)
        return tutor.clean_all(response.text)
    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return "⚠️ Ошибка Gemini. Попробуй через минуту."

# --- Хендлеры (Убрали parse_mode везде) ---
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    await msg.answer(
        "👋 Привет! Я твой ИИ-репетитор по информатике!\n\n"
        "🎓 Помогу с ЕГЭ | 💡 Объясню просто\n\n"
        "⬇️ Используй кнопки ниже",
        reply_markup=kb.main_menu()
    )

@dp.message(lambda m: m.text == "🤖 Выбор модели")
async def choose_model(msg: types.Message):
    await msg.answer("Выбери модель для обучения:", reply_markup=kb.model_selector())

@dp.callback_query(lambda c: c.data.startswith('set_model_'))
async def set_model(cq: types.CallbackQuery):
    model = cq.data.split('_')[2]
    data = tutor.memory.load_user_data(cq.from_user.id)
    data["current_model"] = model
    tutor.memory.save_user_data(cq.from_user.id, data)
    await cq.answer(f"Выбрано: {model.upper()}")
    await cq.message.edit_text(f"✅ Теперь я использую модель: {model.upper()}")

@dp.message(lambda m: m.text == "🔄 Новый диалог")
async def reset_history(msg: types.Message):
    data = tutor.memory.load_user_data(msg.from_user.id)
    data["conversation_history"] = []
    tutor.memory.save_user_data(msg.from_user.id, data)
    await msg.answer("🧹 История диалога очищена!")

# --- ГЛАВНЫЙ ЧАТ ---
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
        
        # САМОЕ ВАЖНОЕ: Отправляем без parse_mode
        await msg.answer(answer)
        
    except Exception as e:
        logging.error(f"Chat error: {e}")
        await msg.answer("⚠️ Произошла ошибка. Попробуй сменить модель.")

async def main():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8000))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
