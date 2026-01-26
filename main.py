from aiohttp import web
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import kb
from groq import Groq
import os
import re
from memory import MemoryManager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация
bot = Bot(token=os.getenv("TG_TOKEN"))
dp = Dispatcher()

class SmartAITutor:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.memory = MemoryManager()
        # Базовый промпт. Мы будем уточнять предмет динамически.
        self.system_prompt = (
            "Ты — опытный репетитор для подготовки к ЕГЭ. "
            "ПИШИ ТОЛЬКО ОБЫЧНЫМ ТЕКСТОМ. ЗАПРЕЩЕНО: жирный шрифт (**), Markdown, HTML теги. "
            "Используй смайлики. Отвечай кратко, по делу и структурированно."
        )

    def clean_text(self, text: str) -> str:
        text = re.sub(r'<[^>]+>', '', text)
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
            return "⚠️ Ошибка связи. Попробуй еще раз!"

    # Метод для смены роли (предмета)
    def change_subject(self, user_id: int, subject_name: str):
        instruction = (
            f"ВНИМАНИЕ: Пользователь сменил предмет. "
            f"Теперь ты репетитор по предмету: {subject_name.upper()}. "
            f"Забудь про информатику, если спрашивали ранее. "
            f"Готовь пользователя к ЕГЭ по предмету {subject_name}."
        )
        # Добавляем скрытую инструкцию в историю диалога
        self.memory.add_message_to_history(str(user_id), "system", instruction)

tutor = SmartAITutor(api_key=os.getenv("GROQ_KEY"))

# --- ХЕНДЛЕРЫ ---

@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    await msg.answer(
        "👋 Привет! Я твой универсальный ИИ-репетитор!\n\n"
        "🎓 Готовлю к ЕГЭ по всем предметам.\n"
        "⬇️ Нажми «Выбрать предмет» в меню ниже, чтобы начать!",
        reply_markup=kb.main_menu()
    )

# 1. Обработка нажатия на кнопку "Выбрать предмет"
@dp.message(lambda m: m.text == "🎓 Выбрать предмет")
async def ask_subject(msg: types.Message):
    await msg.answer("Какой предмет будем учить?", reply_markup=kb.subjects_inline())

# 2. Обработка выбора конкретного предмета (Inline кнопки)
@dp.callback_query(lambda c: c.data.startswith('set_subj_'))
async def set_subject_handler(cq: types.CallbackQuery):
    # Словарь для перевода кода в название
    subjects = {
        "math": "Математика 📐", "info": "Информатика 💻",
        "rus": "Русский язык 🇷🇺", "soc": "Обществознание 📜",
        "phys": "Физика ⚛️", "chem": "Химия 🧪",
        "bio": "Биология 🧬", "hist": "История 🏺",
        "eng": "Английский язык 🇬🇧", "geo": "География 🌍"
    }
    
    code = cq.data.split('_')[2]
    subject_name = subjects.get(code, "Предмет")
    
    # Меняем "мозги" боту
    tutor.change_subject(cq.from_user.id, subject_name)
    
    await cq.answer(f"Выбрано: {subject_name}")
    await cq.message.edit_text(f"✅ Отлично! Теперь я твой репетитор по предмету: **{subject_name}**.\n\nЗадай мне любой вопрос или попроси задачу!")

# Остальные кнопки
@dp.message(lambda m: m.text == "🔄 Новый диалог")
async def reset_history(msg: types.Message):
    data = tutor.memory.load_user_data(msg.from_user.id)
    data["conversation_history"] = []
    tutor.memory.save_user_data(msg.from_user.id, data)
    await msg.answer("🧹 История очищена! Можешь выбрать новый предмет.")

@dp.message(lambda m: m.text == "📉 Мой прогресс")
async def show_progress(msg: types.Message):
    data = tutor.memory.load_user_data(msg.from_user.id)
    count = len(data.get("conversation_history", []))
    await msg.answer(f"📊 Сообщений в этом диалоге: {count}\nТы молодец!")

# Главный чат
@dp.message()
async def chat_handler(msg: types.Message):
    await bot.send_chat_action(msg.chat.id, "typing")
    answer = await tutor.get_ai_response(msg.from_user.id, msg.text)
    # Отправляем ответ и на всякий случай обновляем клавиатуру
    await msg.answer(answer, reply_markup=kb.main_menu())

# --- ЗАПУСК ДЛЯ RENDER ---
async def main():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is Live"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv('PORT', 10000))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    logging.info(f"🚀 Бот запущен на порту {port}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
