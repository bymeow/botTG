
import json
from pathlib import Path
from datetime import datetime

class MemoryManager:
    def __init__(self, storage_dir="bot_memory"):
        """Инициализация: создаем папку для хранения, если её нет."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

    def _get_user_file(self, user_id):
        """Вспомогательная функция для получения пути к файлу юзера."""
        return self.storage_dir / f"user_{user_id}.json"

    def load_user_data(self, user_id):
        """Загрузка данных. Если файла нет или он сломан — создаем новый шаблон."""
        user_file = self._get_user_file(user_id)
        
        if user_file.exists():
            try:
                with open(user_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                # Если файл поврежден, перезаписываем его чистым шаблоном
                pass
        
        return {
            "user_id": str(user_id),
            "name": None,
            "created_at": datetime.now().isoformat(),
            "conversation_history": [],
            "learning_progress": {
                "current_topic": "Не выбрана",
                "completed_topics": [],
                "common_mistakes": []
            }
        }

    def save_user_data(self, user_id, data):
        """Сохранение данных в JSON."""
        user_file = self._get_user_file(user_id)
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_message_to_history(self, user_id, role, content):
        """Добавление сообщения в историю и автоматическое сохранение."""
        data = self.load_user_data(user_id)
        
        # Ограничиваем историю (например, последние 50 сообщений), чтобы файлы не весили тонны
        if len(data["conversation_history"]) > 50:
            data["conversation_history"] = data["conversation_history"][-50:]
            
        data["conversation_history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.save_user_data(user_id, data)

    def get_recent_context(self, user_id, max_messages=10):
        """Получаем последние N сообщений для отправки в ИИ."""
        data = self.load_user_data(user_id)
        history = data.get("conversation_history", [])
        
        # Берем последние сообщения
        recent = history[-max_messages:] if len(history) > max_messages else history
        
        # Возвращаем только то, что понимает API Groq (role и content)
        return [{"role": m["role"], "content": m["content"]} for m in recent]
