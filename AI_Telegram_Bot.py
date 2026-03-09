import os
import telebot
from openai import OpenAI
from ddgs import DDGS
from datetime import datetime
from dotenv import load_dotenv
import threading
import time

load_dotenv()

TG_TOKEN = os.getenv("TG_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TG_TOKEN:
    raise ValueError("TG_TOKEN не найден в переменных окружения")

bot = telebot.TeleBot(TG_TOKEN)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

memory = {}


def search_web(query):
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=3):
                results.append(r["body"])
    except:
        pass
    return "\n".join(results)



def need_web_search(question):

    response = client.chat.completions.create(
        model="deepseek/deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": "Ответь только YES или NO. Нужно ли искать информацию в интернете чтобы ответить на вопрос?"
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )

    answer = response.choices[0].message.content.strip().upper()
    return "YES" in answer


def send_slow(chat_id, text):

    msg = bot.send_message(chat_id, "✍️")

    words = text.split()
    output = ""

    for w in words:
        output += w + " "

        try:
            bot.edit_message_text(output, chat_id, msg.message_id)
        except:
            pass

        time.sleep(0.05)


@bot.message_handler(commands=['start'])
def start_message(message):

    memory[message.chat.id] = []

    bot.reply_to(
        message,
        "Привет 👋\n\n"
        "Я ИИ-бот Mikcha🤖\n"
        "Я умею:\n"
        "• отвечать на вопросы и помогать с домашним заданием\n"
        "• искать информацию в интернете\n"
        "• помнить диалог\n\n"
        "Команды:\n"
        "/reset — очистить память"
    )


@bot.message_handler(commands=['reset'])
def clear_memory(message):

    memory[message.chat.id] = []

    bot.reply_to(message, "Память очищена 🧠")



@bot.message_handler(func=lambda message: True)
def handle_message(message):

    try:

        bot.send_chat_action(message.chat.id, "typing")

        user_id = message.chat.id

        if user_id not in memory:
            memory[user_id] = []

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        if len(message.text.split()) > 2 and need_web_search(message.text):
            web_info = search_web(message.text)
        else:
            web_info = ""

        memory[user_id].append({
            "role": "user",
            "content": message.text
        })

        messages = [
            {
                "role": "system",
                "content": f"""
Ты умный помощник.
Текущая дата и время: {now}

Отвечай на русском.
Если есть информация из интернета — используй её.
"""
            }
        ]

        messages += memory[user_id][-6:]

        messages.append({
            "role": "user",
            "content": f"""
Вопрос пользователя:
{message.text}

Информация из интернета:
{web_info}
"""
        })

        response = client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=messages
        )

        answer = response.choices[0].message.content

        memory[user_id].append({
            "role": "assistant",
            "content": answer
        })

        threading.Thread(
            target=send_slow,
            args=(message.chat.id, answer)
        ).start()

    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")



print("Бот запущен...")
while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(5)