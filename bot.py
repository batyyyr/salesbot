import os
import logging
import asyncio
import requests
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from groq import Groq

# --- БЛОК 1: ОЖИВЛЕНИЕ ДЛЯ RENDER (ФИКС ОШИБКИ 503) ---
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Бот работает!"

def run_web():
    # Render дает порт в переменной окружения, либо используем 10000
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# --- БЛОК 2: НАСТРОЙКИ ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL")

client = Groq(api_key=GROQ_API_KEY)
logging.basicConfig(level=logging.INFO)

# --- БЛОК 3: ИНСТРУКЦИИ ДЛЯ ИИ (ПРОМПТ) ---
SYSTEM_PROMPT = """Ты — опытный администратор барбершопа 'Brutal & Co'. 
Твоя задача: вежливо отвечать на вопросы и записывать клиентов.

ЦЕНЫ: Стрижка — 7000 тг, Борода — 4000 тг, Комплекс — 10000 тг.
АДРЕС: Алматы, Абая 52.

ПРАВИЛА ОБЩЕНИЯ:
1. Отвечай кратко (1-3 предложения).
2. Если клиент хочет записаться, ОБЯЗАТЕЛЬНО узнай: Имя, Номер телефона и желаемое Время.
3. Как только клиент сообщил эти данные, подтверди запись и В САМОМ КОНЦЕ сообщения напиши строго:
ЗАЯВКА:
Имя: [Имя]
Тел: [Телефон]
Время: [Время]
Услуга: [Услуга]"""

# Память бота
context_storage = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if chat_id not in context_storage:
        context_storage[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    context_storage[chat_id].append({"role": "user", "content": user_text})

    # Запрос к нейросети Llama
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=context_storage[chat_id],
    )
    
    bot_reply = completion.choices[0].message.content
    context_storage[chat_id].append({"role": "assistant", "content": bot_reply})

    # --- БЛОК 4: ОТПРАВКА В GOOGLE ТАБЛИЦУ ---
    if "ЗАЯВКА:" in bot_reply and MAKE_WEBHOOK_URL:
        payload = {
            "user_id": chat_id,
            "username": update.effective_user.first_name,
            "raw_text": bot_reply
        }
        try:
            requests.post(MAKE_WEBHOOK_URL, json=payload)
        except Exception as e:
            logging.error(f"Ошибка отправки: {e}")

    await update.message.reply_text(bot_reply)

def main():
    # Запускаем "мини-сайт" в фоновом потоке
    Thread(target=run_web).start()

    # Запускаем Telegram бота
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот и веб-сервер запущены!")
    app.run_polling()

if __name__ == '__main__':
    main()
