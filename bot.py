import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# --- ЗАМЕНИТЕ ЭТУ СТРОКУ НА ВАШ ТОКЕН ---

import os
TOKEN = os.getenv("8707196063:AAHOV5dzAc5_WRs3re_gsm6kXzIhNhAYZEk")

# Функция для команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой первый бот. Напиши мне что-нибудь.")

# Функция для команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я умею повторять за тобой. Просто напиши мне любое сообщение.")

# Функция для обработки текстовых сообщений (эхо)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text(f"Ты сказал: {user_text}")

# Главная функция
def main():
    # Создаём объект Application и передаём ему токен
    app = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Регистрируем обработчик текстовых сообщений (для всех, кроме команд)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запускаем бота (polling — опрос серверов Telegram)
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()