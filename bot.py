import os, logging, requests
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from groq import Groq

# 1. МИНИ-СЕРВЕР (ФИКС 502/503)
flask_app = Flask('')
@flask_app.route('/')
def home(): return "Бот в строю!"
def run_web():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# 2. НАСТРОЙКИ
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_KEY = os.environ.get("GROQ_API_KEY")
MAKE_URL = os.environ.get("MAKE_WEBHOOK_URL")
client = Groq(api_key=GROQ_KEY)

# Умный промпт, который заставляет ИИ выделять данные
SYSTEM_PROMPT = """Ты админ барбершопа в Алматы. Запиши клиента. 
Когда узнаешь Имя, Телефон и Время, в самом конце сообщения добавь строго одну строку:
ДАННЫЕ: Имя | Телефон | Время"""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": update.message.text}]
        )
        reply = completion.choices[0].message.content
        
        # Если ИИ выдал строку ДАННЫЕ, отправляем в Make
        if "ДАННЫЕ:" in reply and MAKE_URL:
            # Вырезаем только строку с данными
            data_line = reply.split("ДАННЫЕ:")[1].strip()
            parts = data_line.split("|")
            
            payload = {
                "name": parts[0].strip() if len(parts) > 0 else "Не указано",
                "phone": parts[1].strip() if len(parts) > 1 else "Не указано",
                "time": parts[2].strip() if len(parts) > 2 else "Не указано"
            }
            requests.post(MAKE_URL, json=payload)

        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"Ошибка: {e}")

def main():
    Thread(target=run_web).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
