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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Инициализация Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model_flash = genai.GenerativeModel('gemini-1.5-flash')
model_pro = genai.GenerativeModel('gemini-1.5-pro')

TOKEN = os.getenv("TG_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()


# --- Класс ИИ-тютора ---
class SmartAITutor:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.memory = MemoryManager()
        self.system_prompt = (
            "Ты — опытный репетитор по информатике для подготовки к ЕГЭ 💻\n\n"
            "📋 ПРАВИЛА ФОРМАТИРОВАНИЯ:\n"
            "✅ Используй ТОЛЬКО Markdown: *курсив*, **жирный**, `код`\n"
            "❌ ЗАПРЕЩЕНО: HTML-теги, символы решётки (#), любые другие теги\n\n"
            "🎯 СТИЛЬ ОБЩЕНИЯ:\n"
            "- Отвечай структурировано, используй списки с дефисами (-) или цифрами\n"
            "- Активно используй эмодзи для визуальной понятности:\n"
            "  📚 теория | 💡 подсказки | ✅ правильно | ❌ ошибка\n"
            "  ❓ вопросы | 🎯 важное | 📝 примеры | 🔢 формулы\n"
            "  ⚠️ частые ошибки | 🚀 продвинутое | 💪 практика\n"
            "- Не давай готовое решение сразу — задавай наводящие вопросы\n"
            "- Помогай разобраться в логике решения пошагово\n"
            "- Объясняй простым языком, приводи аналогии\n"
            "- Мотивируй и поддерживай ученика 🌟"
        )

    def clean_response(self, text: str) -> str:
        """Удаляет все запрещённые символы из ответа ИИ"""
        # Удаляем HTML-теги
        text = re.sub(r'<[^>]+>', '', text)
        # Удаляем решётки заголовков (# ## ###)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'#{1,6}\s+', '', text)
        return text.strip()

    async def get_ai_response(self, user_id: int, message: str):
        """Получает ответ от Groq API с учётом истории"""
        uid = str(user_id)
        self.memory.add_message_to_history(uid, "user", message)
        history = self.memory.get_recent_context(uid)
        messages = [{"role": "system", "content": self.system_prompt}] + history

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None, 
                lambda: self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2048
                )
            )
            
            ai_text = self.clean_response(response.choices[0].message.content)
            self.memory.add_message_to_history(uid, "assistant", ai_text)
            return ai_text
        except Exception as e:
            logging.error(f"Ошибка Groq API: {e}")
            return "⚠️ Произошла ошибка при обращении к ИИ. Попробуй ещё раз!"


tutor = SmartAITutor(api_key=GROQ_API_KEY)


# --- Вспомогательные функции ---
async def get_gemini_response(prompt, model_type="flash"):
    """Получает ответ от Gemini API"""
    try:
        selected_model = model_pro if model_type == "pro" else model_flash
        response = await asyncio.to_thread(selected_model.generate_content, prompt)
        return response.text
    except Exception as e:
        logging.error(f"Ошибка Gemini API: {e}")
        return "⚠️ Произошла ошибка при обращении к Gemini. Попробуй ещё раз!"


# --- Хендлеры команд и меню ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    """Приветственное сообщение"""
    welcome_text = (
        "👋 **Привет! Я твой ИИ-репетитор по информатике!**\n\n"
        "🎓 Помогу подготовиться к ЕГЭ по информатике\n"
        "💡 Объясню сложные темы простым языком\n"
        "📝 Разберу задачи пошагово\n"
        "🚀 Подготовлю к экзамену на высокий балл\n\n"
        "⬇️ *Используй кнопки меню для навигации*"
    )
    await message.answer(welcome_text, reply_markup=kb.main_menu(), parse_mode="Markdown")


@dp.message(lambda message: message.text == "🤖 Выбор модели")
async def choose_model(message: types.Message):
    """Меню выбора ИИ-модели"""
    user_id = message.from_user.id
    data = tutor.memory.load_user_data(user_id)
    current_model = data.get("current_model", "groq")
    
    model_info = {
        "groq": "🚀 Groq (быстрая и умная)",
        "flash": "⚡ Gemini Flash (сбалансированная)",
        "pro": "🎯 Gemini Pro (максимальная точность)"
    }
    
    await message.answer(
        f"🤖 **Выбор ИИ-модели**\n\n"
        f"Сейчас активна: **{model_info.get(current_model, current_model)}**\n\n"
        f"Выбери модель для ответов:",
        reply_markup=kb.model_selector(),
        parse_mode="Markdown"
    )


@dp.callback_query(lambda c: c.data.startswith('set_model_'))
async def process_model_selection(callback_query: types.CallbackQuery):
    """Обработка выбора модели"""
    model_name = callback_query.data.split('_')[2]
    user_id = callback_query.from_user.id
    
    data = tutor.memory.load_user_data(user_id)
    data["current_model"] = model_name
    tutor.memory.save_user_data(user_id, data)
    
    model_emoji = {"groq": "🚀", "flash": "⚡", "pro": "🎯"}
    emoji = model_emoji.get(model_name, "🤖")
    
    await callback_query.answer(f"Модель изменена на {model_name.upper()}! {emoji}")
    await callback_query.message.edit_text(
        f"✅ **Модель успешно изменена!**\n\n"
        f"{emoji} Теперь я использую: **{model_name.upper()}**",
        parse_mode="Markdown"
    )


@dp.message(lambda message: message.text == "📚 Темы ЕГЭ")
async def show_topics(message: types.Message):
    """Показывает темы ЕГЭ по информатике"""
    topics_text = (
        "📚 **Ключевые темы ЕГЭ по информатике:**\n\n"
        "**1️⃣ Системы счисления** 🔢\n"
        "   - Перевод между системами\n"
        "   - Арифметические операции\n\n"
        "**2️⃣ Алгебра логики** 🧮\n"
        "   - Таблицы истинности\n"
        "   - Логические выражения\n\n"
        "**3️⃣ Алгоритмы** 🔄\n"
        "   - Блок-схемы\n"
        "   - Трассировка программ\n\n"
        "**4️⃣ Программирование** 💻\n"
        "   - Python/Pascal\n"
        "   - Рекурсия и циклы\n\n"
        "**5️⃣ Информация и кодирование** 📊\n"
        "   - Кодирование информации\n"
        "   - Объём данных\n\n"
        "**6️⃣ Базы данных и Excel** 📈\n"
        "   - SQL-запросы\n"
        "   - Электронные таблицы\n\n"
        "**7️⃣ Компьютерные сети** 🌐\n"
        "   - IP-адресация\n"
        "   - Маски подсети\n\n"
        "💡 *Напиши номер темы или задай вопрос!*"
    )
    await message.answer(topics_text, parse_mode="Markdown")


@dp.message(lambda message: message.text == "🔄 Новый диалог")
async def reset_history(message: types.Message):
    """Очищает историю диалога"""
    user_id = message.from_user.id
    data = tutor.memory.load_user_data(user_id)
    data["conversation_history"] = []
    tutor.memory.save_user_data(user_id, data)
    
    await message.answer(
        "🧹 **История диалога очищена!**\n\n"
        "✨ Начнём с чистого листа!\n"
        "❓ Чем могу помочь?",
        parse_mode="Markdown"
    )


@dp.message(lambda message: message.text == "📉 Мой прогресс")
async def show_progress(message: types.Message):
    """Показывает прогресс пользователя"""
    user_id = message.from_user.id
    data = tutor.memory.load_user_data(user_id)
    
    mistakes = data.get("learning_progress", {}).get("common_mistakes", [])
    message_count = len(data.get("conversation_history", []))
    
    if not mistakes:
        response = (
            "📊 **Твой прогресс:**\n\n"
            f"💬 Сообщений: **{message_count}**\n"
            "✅ Ошибок не зафиксировано\n\n"
            "🌟 Отлично! Продолжай в том же духе! 💪"
        )
    else:
        mistakes_list = "\n".join([f"   • {m}" for m in mistakes[:5]])
        response = (
            "📊 **Твой прогресс:**\n\n"
            f"💬 Сообщений: **{message_count}**\n"
            f"⚠️ Частые ошибки:\n{mistakes_list}\n\n"
            "💡 Давай разберём эти темы подробнее!"
        )
    
    await message.answer(response, parse_mode="Markdown")


# --- Основной обработчик чата ---
@dp.message()
async def chat_handler(message: types.Message):
    """Обрабатывает все текстовые сообщения"""
    await bot.send_chat_action(message.chat.id, "typing")
    
    user_id = message.from_user.id
    data = tutor.memory.load_user_data(user_id)
    current_model = data.get("current_model", "groq")
    raw_answer = ""

    try:
        # Выбираем модель и получаем ответ
        if current_model == "pro":
            raw_answer = await get_gemini_response(message.text, model_type="pro")
        elif current_model == "flash":
            raw_answer = await get_gemini_response(message.text, model_type="flash")
        else:
            raw_answer = await tutor.get_ai_response(user_id, message.text)
        
        # Форматируем и отправляем ответ
        if raw_answer:
            pretty_answer = styles.format_bot_response(raw_answer)
            await message.answer(pretty_answer, parse_mode="Markdown")
        else:
            await message.answer("⚠️ Получен пустой ответ. Попробуй переформулировать вопрос.")
            
    except Exception as e:
        logging.error(f"Ошибка в chat_handler: {e}")
        
        # Пытаемся отправить без форматирования
        try:
            if raw_answer:
                await message.answer(raw_answer)
            else:
                await message.answer(
                    "⚠️ **Произошла ошибка**\n\n"
                    "Попробуй:\n"
                    "• Переформулировать вопрос\n"
                    "• Выбрать другую модель (🤖 Выбор модели)\n"
                    "• Очистить историю (🔄 Новый диалог)"
                )
        except Exception as e2:
            logging.error(f"Критическая ошибка при отправке сообщения: {e2}")
            await message.answer("❌ Критическая ошибка. Попробуй команду /start")


# --- Запуск сервера для Koyeb ---
async def main():
    """Запускает веб-сервер и бота"""
    # Создаём веб-приложение для health check
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running! 🤖"))
    app.router.add_get('/health', lambda r: web.Response(text="OK"))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8000)))
    await site.start()
    
    logging.info("🚀 Бот запущен и готов к работе!")
    logging.info(f"🌐 Веб-сервер запущен на порту {os.getenv('PORT', 8000)}")
    
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
