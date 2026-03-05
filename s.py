import os
import time
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
import telebot
from openai import OpenAI
from dotenv import load_dotenv

# ==============================
# 🔐 Переменные окружения
# ==============================

load_dotenv()  # Локально работает, на Render не мешает

TG_TOKEN = os.getenv("TG_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TG_TOKEN:
    raise ValueError("TG_TOKEN не найден в переменных окружения")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY не найден в переменных окружения")

# ==============================
# 🤖 Инициализация
# ==============================

bot = telebot.TeleBot(TG_TOKEN)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# ==============================
# 🧠 Память пользователей
# ==============================

user_memory = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content": "Ты полезный, дружелюбный Telegram-бот. Отвечай кратко и понятно."
}

MAX_HISTORY = 7


# ==============================
# ✍️ Анимация печати
# ==============================

def typing_animation(chat_id, stop_event):
    while not stop_event.is_set():
        bot.send_chat_action(chat_id, "typing")
        time.sleep(4)


# ==============================
# ⌨️ Эффект постепенной отправки
# ==============================

def send_with_typing_effect(chat_id, text, reply_to_id):
    message = bot.send_message(
        chat_id,
        "✍️ ...",
        reply_to_message_id=reply_to_id
    )

    chunk_size = 15
    current_text = ""

    for i in range(0, len(text), chunk_size):
        current_text += text[i:i+chunk_size]
        try:
            bot.edit_message_text(
                current_text,
                chat_id,
                message.message_id
            )
        except:
            pass
        time.sleep(0.05)


# ==============================
# 🔄 Команда /start
# ==============================

@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    user_memory[user_id] = [SYSTEM_PROMPT]

    bot.send_message(
        message.chat.id,
        "🔄 Диалог перезапущен.\n"
        "Память очищена 🧠\n\n"
        "Напиши мне что-нибудь 😊"
    )


# ==============================
# 💬 Обработка сообщений
# ==============================

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_text = message.text

    stop_event = threading.Event()
    typing_thread = threading.Thread(
        target=typing_animation,
        args=(message.chat.id, stop_event)
    )
    typing_thread.start()

    try:
        if user_id not in user_memory:
            user_memory[user_id] = [SYSTEM_PROMPT]

        # 🕒 Московское время (без pytz)
        now = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M")

        user_memory[user_id].append({
            "role": "system",
            "content": f"Текущая дата и время: {now}"
        })

        user_memory[user_id].append({
            "role": "user",
            "content": user_text
        })

        user_memory[user_id] = (
            [SYSTEM_PROMPT] +
            user_memory[user_id][-MAX_HISTORY:]
        )

        response = client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=user_memory[user_id],
            max_tokens=300
        )

        answer = response.choices[0].message.content

        user_memory[user_id].append({
            "role": "assistant",
            "content": answer
        })

        stop_event.set()
        typing_thread.join()

        send_with_typing_effect(
            message.chat.id,
            answer,
            message.message_id
        )

    except Exception as e:
        stop_event.set()
        typing_thread.join()

        print(f"Ошибка: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ Временная ошибка сервера. Попробуй ещё раз.",
            reply_to_message_id=message.message_id
        )


# ==============================
# ♻️ Автоперезапуск
# ==============================

def run_bot():
    while True:
        try:
            print("Бот запущен...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Бот упал: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run_bot()
