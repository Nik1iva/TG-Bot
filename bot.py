import logging
import sqlite3
import datetime
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==================== Конфигурация ====================
TOKEN = "8707196063:AAHOV5dzAc5_WRs3re_gsm6kXzIhNhAYZEk"  # Замените на токен вашего бота
ADMIN_ID = 741673133  # Замените на ваш Telegram ID (для админ-функций)

# ==================== Логирование ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== База данных ====================
DB_NAME = "restaurant_bot.db"

def init_db():
    """Создаёт таблицы, если они ещё не существуют."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # Пользователи
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            phone TEXT,
            registered_at TEXT
        )
    """)
    # Меню
    cur.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL
        )
    """)
    # Бронирования
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            table_number INTEGER NOT NULL,
            booking_datetime TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

# ==================== Вспомогательные функции БД ====================
def get_user(telegram_id: int) -> Optional[tuple]:
    """Возвращает данные пользователя по Telegram ID или None."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, username, phone, registered_at FROM users WHERE id = ?", (telegram_id,))
    user = cur.fetchone()
    conn.close()
    return user

def register_user(telegram_id: int, username: str, phone: str) -> None:
    """Регистрирует нового пользователя."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cur.execute(
        "INSERT INTO users (id, username, phone, registered_at) VALUES (?, ?, ?, ?)",
        (telegram_id, username, phone, now)
    )
    conn.commit()
    conn.close()

def get_menu() -> list:
    """Возвращает список всех блюд из меню."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name, description, price FROM menu ORDER BY id")
    items = cur.fetchall()
    conn.close()
    return items

def add_menu_item(name: str, description: str, price: float) -> None:
    """Добавляет блюдо в меню."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO menu (name, description, price) VALUES (?, ?, ?)",
        (name, description, price)
    )
    conn.commit()
    conn.close()

def get_free_tables(datetime_str: str) -> list:
    """Возвращает список свободных столов (1-10) на указанное время."""
    occupied = set()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT table_number FROM bookings WHERE booking_datetime = ?", (datetime_str,))
    rows = cur.fetchall()
    conn.close()
    for row in rows:
        occupied.add(row[0])
    free = [t for t in range(1, 11) if t not in occupied]
    return free

def create_booking(user_id: int, table_number: int, datetime_str: str) -> None:
    """Создаёт бронирование."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cur.execute(
        "INSERT INTO bookings (user_id, table_number, booking_datetime, created_at) VALUES (?, ?, ?, ?)",
        (user_id, table_number, datetime_str, now)
    )
    conn.commit()
    conn.close()

def get_user_bookings(user_id: int) -> list:
    """Возвращает все брони пользователя."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, table_number, booking_datetime FROM bookings WHERE user_id = ? ORDER BY booking_datetime",
        (user_id,)
    )
    bookings = cur.fetchall()
    conn.close()
    return bookings

def cancel_booking(booking_id: int) -> bool:
    """Отменяет бронь по ID. Возвращает True, если успешно."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# ==================== Клавиатуры ====================
def main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура после авторизации."""
    buttons = [
        ["📋 Меню"],
        ["📅 Забронировать стол"],
        ["📖 Мои брони"],
        ["❌ Отменить бронь"]
    ]
    # Если пользователь админ, добавляем кнопку управления меню
    # Но мы добавим отдельную команду /additem, чтобы не загромождать клавиатуру.
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def contact_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой для отправки контакта."""
    button = KeyboardButton("📱 Отправить номер телефона", request_contact=True)
    return ReplyKeyboardMarkup([[button]], resize_keyboard=True)

# ==================== Обработчики ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start. Проверяет авторизацию."""
    user = update.effective_user
    telegram_id = user.id
    username = user.username or "Без имени"

    db_user = get_user(telegram_id)
    if db_user:
        # Пользователь уже зарегистрирован
        await update.message.reply_text(
            f"С возвращением, {username}!\nВыберите действие:",
            reply_markup=main_keyboard()
        )
        context.user_data["authorized"] = True
    else:
        # Просим отправить контакт для регистрации
        await update.message.reply_text(
            "Добро пожаловать! Для регистрации нажмите кнопку ниже и отправьте свой номер телефона.",
            reply_markup=contact_keyboard()
        )
        context.user_data["authorized"] = False

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает полученный контакт и регистрирует пользователя."""
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("Пожалуйста, используйте кнопку для отправки контакта.")
        return

    telegram_id = update.effective_user.id
    username = update.effective_user.username or "Без имени"
    phone = contact.phone_number

    # Проверяем, не зарегистрирован ли уже
    if get_user(telegram_id):
        await update.message.reply_text("Вы уже зарегистрированы.", reply_markup=main_keyboard())
        context.user_data["authorized"] = True
        return

    register_user(telegram_id, username, phone)
    await update.message.reply_text(
        f"Регистрация успешна!\nДобро пожаловать, {username}.",
        reply_markup=main_keyboard()
    )
    context.user_data["authorized"] = True

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню."""
    if not context.user_data.get("authorized"):
        await update.message.reply_text("Пожалуйста, сначала авторизуйтесь через /start.")
        return

    items = get_menu()
    if not items:
        await update.message.reply_text("Меню пусто. Загляните позже.")
        return

    text = "🍽 *Наше меню:*\n\n"
    for item in items:
        item_id, name, desc, price = item
        text += f"*{name}*"
        if desc:
            text += f" — {desc}"
        text += f" — {price:.2f} руб.\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def booking_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начинает процесс бронирования."""
    if not context.user_data.get("authorized"):
        await update.message.reply_text("Сначала авторизуйтесь.")
        return

    # Спросим дату и время
    await update.message.reply_text(
        "Введите желаемую дату и время в формате:\n`YYYY-MM-DD HH:MM`\n\n"
        "Например: 2026-09-03 19:30",
        parse_mode="Markdown"
    )
    # Переключаем состояние ожидания ввода даты
    context.user_data["waiting_for_booking_datetime"] = True

async def booking_datetime_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ввод даты и времени, показывает свободные столы."""
    if not context.user_data.get("waiting_for_booking_datetime"):
        return

    text = update.message.text.strip()
    try:
        # Проверяем формат
        dt = datetime.datetime.strptime(text, "%Y-%m-%d %H:%M")
        # Проверяем, что время в будущем
        if dt < datetime.datetime.now():
            await update.message.reply_text("Дата и время должны быть в будущем. Попробуйте снова.")
            return
        datetime_str = dt.isoformat()
    except ValueError:
        await update.message.reply_text(
            "Неверный формат. Введите дату и время в формате `YYYY-MM-DD HH:MM`.",
            parse_mode="Markdown"
        )
        return

    # Сохраняем выбранное время
    context.user_data["booking_datetime"] = datetime_str

    # Ищем свободные столы
    free_tables = get_free_tables(datetime_str)
    if not free_tables:
        await update.message.reply_text(
            "К сожалению, на это время все столы заняты. Попробуйте другую дату или время."
        )
        # Можно предложить начать заново
        context.user_data["waiting_for_booking_datetime"] = False
        return

    # Создаём инлайн-клавиатуру со свободными столами
    keyboard = []
    row = []
    for table in free_tables:
        row.append(InlineKeyboardButton(f"Стол {table}", callback_data=f"book_table_{table}"))
        if len(row) == 5:  # по 5 в ряд
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data="cancel_booking")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Свободные столы на {dt.strftime('%d.%m.%Y %H:%M')}:\nВыберите стол:",
        reply_markup=reply_markup
    )
    context.user_data["waiting_for_booking_datetime"] = False

async def booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает выбор стола для бронирования."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "cancel_booking":
        await query.edit_message_text("Бронирование отменено.")
        return

    if data.startswith("book_table_"):
        table_number = int(data.split("_")[2])
        user_id = update.effective_user.id
        datetime_str = context.user_data.get("booking_datetime")
        if not datetime_str:
            await query.edit_message_text("Ошибка: время не выбрано. Начните заново.")
            return

        # Проверяем, что стол всё ещё свободен (на случай, если кто-то успел забронировать)
        free = get_free_tables(datetime_str)
        if table_number not in free:
            await query.edit_message_text(
                "Этот стол уже занят на выбранное время. Попробуйте выбрать другой."
            )
            return

        # Создаём бронь
        create_booking(user_id, table_number, datetime_str)
        dt = datetime.datetime.fromisoformat(datetime_str)
        await query.edit_message_text(
            f"✅ Стол {table_number} успешно забронирован на {dt.strftime('%d.%m.%Y %H:%M')}!"
        )
        # Очищаем временные данные
        context.user_data.pop("booking_datetime", None)

async def my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает брони текущего пользователя."""
    if not context.user_data.get("authorized"):
        await update.message.reply_text("Авторизуйтесь через /start.")
        return

    user_id = update.effective_user.id
    bookings = get_user_bookings(user_id)
    if not bookings:
        await update.message.reply_text("У вас пока нет броней.")
        return

    text = "📖 *Ваши брони:*\n\n"
    for b_id, table, dt_str in bookings:
        dt = datetime.datetime.fromisoformat(dt_str)
        text += f"• Стол {table} на {dt.strftime('%d.%m.%Y %H:%M')} (ID: {b_id})\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def cancel_booking_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начинает процесс отмены брони."""
    if not context.user_data.get("authorized"):
        await update.message.reply_text("Авторизуйтесь через /start.")
        return

    user_id = update.effective_user.id
    bookings = get_user_bookings(user_id)
    if not bookings:
        await update.message.reply_text("У вас нет броней для отмены.")
        return

    # Создаём инлайн-клавиатуру со списком броней
    keyboard = []
    for b_id, table, dt_str in bookings:
        dt = datetime.datetime.fromisoformat(dt_str)
        label = f"Стол {table} - {dt.strftime('%d.%m %H:%M')}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"cancel_{b_id}")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_operation")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Выберите бронь для отмены:",
        reply_markup=reply_markup
    )

async def cancel_booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает выбор брони для отмены."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "cancel_operation":
        await query.edit_message_text("Отмена операции.")
        return

    if data.startswith("cancel_"):
        booking_id = int(data.split("_")[1])
        success = cancel_booking(booking_id)
        if success:
            await query.edit_message_text("✅ Бронь успешно отменена.")
        else:
            await query.edit_message_text("❌ Не удалось отменить бронь (возможно, она уже была отменена).")

async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для администратора: добавить блюдо в меню."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У вас нет прав для этой команды.")
        return

    # Ожидаем ввод в формате: название; описание; цена
    await update.message.reply_text(
        "Введите новое блюдо в формате:\n`Название; Описание; Цена`\n\n"
        "Например: `Стейк; Сочный стейк с гарниром; 1500`",
        parse_mode="Markdown"
    )
    context.user_data["waiting_for_add_item"] = True

async def add_item_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ввод нового блюда."""
    if not context.user_data.get("waiting_for_add_item"):
        return

    text = update.message.text.strip()
    parts = text.split(";")
    if len(parts) != 3:
        await update.message.reply_text(
            "Неверный формат. Нужно: `Название; Описание; Цена`.\nПопробуйте снова."
        )
        return

    name = parts[0].strip()
    description = parts[1].strip()
    try:
        price = float(parts[2].strip().replace(",", "."))
    except ValueError:
        await update.message.reply_text("Цена должна быть числом. Попробуйте снова.")
        return

    add_menu_item(name, description, price)
    await update.message.reply_text(f"✅ Блюдо «{name}» добавлено в меню!")
    context.user_data["waiting_for_add_item"] = False

# ==================== Главная функция ====================
def main() -> None:
    """Запуск бота."""
    init_db()

    # Создаём приложение
    application = Application.builder().token(TOKEN).build()

    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("additem", add_item))  # админская команда

    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex("^📋 Меню$"), menu_handler
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex("^📅 Забронировать стол$"), booking_start
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex("^📖 Мои брони$"), my_bookings
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex("^❌ Отменить бронь$"), cancel_booking_start
    ))
    # Обработчик ввода даты для бронирования (после нажатия кнопки "Забронировать стол")
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, booking_datetime_input
    ))
    # Обработчик ввода нового блюда для админа
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, add_item_input
    ))

    # Обработчики callback-запросов (инлайн-кнопки)
    application.add_handler(CallbackQueryHandler(booking_callback, pattern="^book_table_|^cancel_booking$"))
    application.add_handler(CallbackQueryHandler(cancel_booking_callback, pattern="^cancel_|^cancel_operation$"))

    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()