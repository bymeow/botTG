import re
import html

def format_bot_response(text: str) -> str:
    # 1. Экранируем спецсимволы, чтобы не ломать HTML
    text = html.escape(text)

    # 2. Жирный шрифт: заменяем **текст** на <b>текст</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = text.replace("*", "") # Убираем одиночные звезды

    # 3. Заголовки и отступы (ИСПРАВЛЕННАЯ ЧАСТЬ)
    lines = [line.strip() for line in text.split('\n')]
    if lines:
        # Первая строка - заголовок
        header = lines[0]
        if not header.startswith("<b>"):
            header = f"<b>{header}</b>"
        
        # Собираем остальной текст
        body_list = [line for line in lines[1:] if line]
        
        if body_list:
            # Соединяем с двойными отступами
            text = f"{header}\n\n" + "\n\n".join(body_list)
        else:
            text = header

    # 4. Курсив для важных слов
    for phrase in ["Важно:", "Запомни:", "Обрати внимание:"]:
        text = text.replace(phrase, f"<i>{phrase}</i>")

    # 5. Спойлер для ответов
    for trigger in ["Ответ:", "РЕШЕНИЕ:"]:
        if trigger in text:
            parts = text.split(trigger, 1)
            if len(parts) > 1 and parts[1].strip():
                text = f"{parts[0]}\n\n<b>{trigger}</b> <tg-spoiler>{parts[1].strip()}</tg-spoiler>"
            break

    return text
