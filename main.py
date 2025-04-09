import os
import sympy as sp
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from openai import OpenAI
import threading

# Telegram Token
TELEGRAM_TOKEN = "7649909820:AAG_ofyeA__Q6iLHWl1WQaFuiS6iaUhxW3Q"

# OpenAI через AITUNNEL
client = OpenAI(
    api_key="sk-aitunnel-ynPRiPL0SFNxo2Gm1YkgWbjGsxVIdgEy",
    base_url="https://api.aitunnel.ru/v1/",
)

# Состояния пользователей
user_states = {}

# Клавиатура главного меню
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Калькулятор", callback_data="math")],
        [InlineKeyboardButton("🖼 Генерация изображения", callback_data="image")],
        [InlineKeyboardButton("🔊 Озвучить текст", callback_data="speech")],
        [InlineKeyboardButton("🤖 ИИ помощник", callback_data="other")],
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура с кнопкой "Назад"
def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])

# Клавиатура с кнопкой "Главное меню"
def get_main_menu_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]])

# Калькулятор
def get_calculator_keyboard():
    keyboard = [
        [InlineKeyboardButton("7", callback_data='7'), InlineKeyboardButton("8", callback_data='8'), InlineKeyboardButton("9", callback_data='9')],
        [InlineKeyboardButton("4", callback_data='4'), InlineKeyboardButton("5", callback_data='5'), InlineKeyboardButton("6", callback_data='6')],
        [InlineKeyboardButton("1", callback_data='1'), InlineKeyboardButton("2", callback_data='2'), InlineKeyboardButton("3", callback_data='3')],
        [InlineKeyboardButton("0", callback_data='0'), InlineKeyboardButton("+", callback_data='+'), InlineKeyboardButton("-", callback_data='-')],
        [InlineKeyboardButton("*", callback_data='*'), InlineKeyboardButton("/", callback_data='/'), InlineKeyboardButton("√", callback_data='sqrt')],
        [InlineKeyboardButton("=", callback_data='solve'), InlineKeyboardButton("Очистить", callback_data='clear')],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Отправляем сообщение с кнопкой "Главное меню"
    await update.message.reply_text("Привет! Что будем делать?", reply_markup=get_main_menu_button())

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "back_to_main":
        user_states[user_id] = None
        await query.message.reply_text("Вы вернулись в главное меню:", reply_markup=get_main_keyboard())

    elif data == "math":
        user_states[user_id] = {"mode": "math", "expression": ""}
        await query.message.reply_text("Собери выражение с помощью кнопок:", reply_markup=get_calculator_keyboard())

    elif data in "0123456789+-*/":
        if user_states.get(user_id, {}).get("mode") == "math":
            user_states[user_id]["expression"] += data
            await query.message.edit_text(f"Выражение: {user_states[user_id]['expression']}", reply_markup=get_calculator_keyboard())

    elif data == "clear":
        if user_states.get(user_id, {}).get("mode") == "math":
            user_states[user_id]["expression"] = ""
            await query.message.edit_text("Выражение очищено.", reply_markup=get_calculator_keyboard())

    elif data == "solve":
        expr = user_states.get(user_id, {}).get("expression", "")
        try:
            result = sp.N(sp.sympify(expr))
            if result == int(result):
                result = int(result)
            await query.message.edit_text(f"{expr} = {result}", reply_markup=get_calculator_keyboard())
            user_states[user_id]["expression"] = ""
        except Exception as e:
            await query.message.edit_text(f"Ошибка: {e}", reply_markup=get_calculator_keyboard())

    elif data == "sqrt":
        expr = user_states.get(user_id, {}).get("expression", "")
        try:
            if expr:
                value = float(expr)
                if value < 0:
                    raise ValueError("Нельзя извлечь корень из отрицательного числа.")
                result = sp.N(sp.sqrt(value))
                await query.message.edit_text(f"√{expr} = {result}", reply_markup=get_calculator_keyboard())
                user_states[user_id]["expression"] = ""
            else:
                await query.message.edit_text("Введите число для извлечения корня.", reply_markup=get_calculator_keyboard())
        except Exception as e:
            await query.message.edit_text(f"Ошибка: {e}", reply_markup=get_calculator_keyboard())

    elif data == "image":
        user_states[user_id] = {"mode": "image"}
        await query.message.reply_text("Отправьте описание изображения:", reply_markup=back_keyboard())

    elif data == "speech":
        user_states[user_id] = {"mode": "speech"}
        await query.message.reply_text("Отправьте текст для озвучки:", reply_markup=back_keyboard())

    elif data == "other":
        user_states[user_id] = {"mode": "other"}
        await query.message.reply_text("Задайте свой вопрос ИИ:", reply_markup=back_keyboard())

# Обработка текстов
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_input = update.message.text
    mode = user_states.get(user_id, {}).get("mode")

    if mode == "image":
        try:
            img = client.images.generate(model="dall-e-3", prompt=user_input, size="1024x1024", quality="standard")
            await update.message.reply_photo(photo=img.data[0].url, caption="Вот ваше изображение!", reply_markup=get_main_menu_button())
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}", reply_markup=get_main_menu_button())

    elif mode == "speech":
        try:
            response = client.audio.speech.create(
                model="tts-1",
                input=user_input,
                voice="alloy"
            )
            file_path = "speech.mp3"
            with open(file_path, "wb") as f:
                f.write(response.content)
            await update.message.reply_voice(voice=open(file_path, "rb"), reply_markup=get_main_menu_button())
            os.remove(file_path)
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}", reply_markup=get_main_menu_button())

    elif mode == "other":
        try:
            chat = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": user_input}],
                max_tokens=1000
            )
            await update.message.reply_text(chat.choices[0].message.content, reply_markup=get_main_menu_button())
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}", reply_markup=get_main_menu_button())

    else:
        await update.message.reply_text("Пожалуйста, выберите действие из меню:", reply_markup=get_main_menu_button())

# Flask-сервер
app = Flask(__name__)

@app.route("/")
def home():
    return "Бот запущен!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# Запуск бота
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    threading.Thread(target=run_flask).start()
    application.run_polling()

if __name__ == "__main__":
    main()

