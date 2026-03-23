import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, MessageHandler,
    CommandHandler, filters, ContextTypes
)
from groq import Groq

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Клиент Groq
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

# Хранилище истории диалогов
conversation_history = {}

# Системный промпт — личность менеджера
SYSTEM_PROMPT = """Ты — Нурсултан, менеджер барбершопа FADE.

Услуги и цены:
- Стрижка мужская — 4 000 тг
- Стрижка + борода — 6 500 тг
- Тонирование — 8 000 тг
- VIP-пакет (всё) — 12 000 тг

Адрес: ул. Абая 15, 2 этаж, Алматы
Режим: Пн-Вс, 10:00-22:00
Запись: в Telegram или по номеру +7 777 123 45 67

Твоя задача: записать клиента на удобное время.
Всегда спрашивай: имя, желаемую услугу, удобное время.

Твои задачи:
1. Тепло приветствовать клиентов и выяснять их потребности
2. Рассказывать о продуктах/услугах компании
3. Отвечать на возражения профессионально
4. Предлагать подходящие решения
5. Приглашать на консультацию или оформлять заявку

Продукты компании:
- [ВПИШИ СВОИ ПРОДУКТЫ]
- [ВПИШИ ЦЕНЫ]
- [ВПИШИ АКЦИИ]

Правила:
- Всегда общайся дружелюбно и по-русски
- Не придумывай информацию которой нет
- Если вопрос сложный — предложи связаться с менеджером
- Старайся получить контакт клиента (имя, телефон)
- Максимальная длина ответа — 200 слов"""


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []
    await update.message.reply_text(
        "👋 Привет! Я Нурсултан, менеджер по продажам.\n\n"
        "Чем могу помочь? Расскажите, что вас интересует!"
    )


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    # Инициализируем историю если новый пользователь
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    # Добавляем сообщение пользователя в историю
    conversation_history[chat_id].append({
        "role": "user",
        "content": user_text
    })

    # Храним только последние 10 сообщений (память)
    if len(conversation_history[chat_id]) > 10:
        conversation_history[chat_id] = conversation_history[chat_id][-10:]

    # Отправляем запрос в Groq
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *conversation_history[chat_id]
            ],
            max_tokens=400,
            temperature=0.7
        )

        bot_reply = response.choices[0].message.content

        # Добавляем ответ бота в историю
        conversation_history[chat_id].append({
            "role": "assistant",
            "content": bot_reply
        })

        await update.message.reply_text(bot_reply)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text(
            "⚠️ Временная ошибка. Попробуйте через минуту."
        )


# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(
        os.environ["TELEGRAM_TOKEN"]
    ).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    print("Бот запущен!")
    app.run_polling()
