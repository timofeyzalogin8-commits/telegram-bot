import time
import telebot
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
# ==============================
# 🔐 Переменные окружения
# ==============================

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

MAX_HISTORY = 10


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

    try:
        if user_id not in user_memory:
            user_memory[user_id] = [SYSTEM_PROMPT]

        # Добавляем сообщение пользователя
        user_memory[user_id].append({
            "role": "user",
            "content": user_text
        })

        # Ограничиваем историю
        user_memory[user_id] = (
            [SYSTEM_PROMPT] +
            user_memory[user_id][-MAX_HISTORY:]
        )

        response = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=user_memory[user_id],
        )

        answer = response.choices[0].message.content

        # Сохраняем ответ
        user_memory[user_id].append({
            "role": "assistant",
            "content": answer
        })

        bot.send_message(message.chat.id, answer)

    except Exception as e:
        print(f"Ошибка при обработке сообщения: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ Временная ошибка сервера. Попробуй ещё раз."
        )


# ==============================
# ♻️ Автоперезапуск при падении
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
