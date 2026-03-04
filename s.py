import os
from dotenv import load_dotenv
import telebot
from openai import OpenAI

load_dotenv()

TG_TOKEN = os.getenv("TG_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(TG_TOKEN)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# 🧠 Память пользователей
user_memory = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content": "Ты полезный, дружелюбный Telegram-бот. Отвечай понятно и по делу."
}

MAX_HISTORY = 10  # сколько последних сообщений хранить


@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    
    # очищаем память при старте
    user_memory[user_id] = [SYSTEM_PROMPT]

    bot.reply_to(
        message,
        "Привет! 👋\n\n"
        "Я — ИИ-Telegram-бот Mikcha 🤖\n"
        "Я могу помочь с домашней работой или просто ответить на твой вопрос)\n\n"
        "Напиши мне что-нибудь 😊"
    )


@bot.message_handler(commands=['reset'])
def start_message(message):
    user_id = message.from_user.id
    user_memory[user_id] = [SYSTEM_PROMPT]

    bot.send_message(
        message.chat.id,
        "🔄 Диалог перезапущен.\n"
        "Контекст очищен.\n\n"
        "Чем могу помочь?"
    )



@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_text = message.text

    try:
        # если пользователь новый
        if user_id not in user_memory:
            user_memory[user_id] = [SYSTEM_PROMPT]

        # добавляем сообщение пользователя
        user_memory[user_id].append({
            "role": "user",
            "content": user_text
        })

        # ограничиваем длину истории
        user_memory[user_id] = (
            [SYSTEM_PROMPT] +
            user_memory[user_id][-MAX_HISTORY:]
        )

        response = client.chat.completions.create(
            model="google/gemma-2-9b-it",
            messages=user_memory[user_id]
        )

        if not response or not response.choices:
            bot.reply_to(message, "Ошибка: пустой ответ от модели.")
            return

        answer = response.choices[0].message.content

        # добавляем ответ модели в память
        user_memory[user_id].append({
            "role": "assistant",
            "content": answer
        })

        bot.reply_to(message, answer)

    except Exception as e:
        bot.reply_to(message, f"Системная ошибка: {e}")


print("Бот запущен...")
bot.infinity_polling()