import sympy as sp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from openai import OpenAI
import os
from flask import Flask
import threading

# Токен Telegram-бота
TELEGRAM_TOKEN = "7649909820:AAG_ofyeA__Q6iLHWl1WQaFuiS6iaUhxW3Q"

# Настройка OpenAI через AITUNNEL
client = OpenAI(
    api_key="sk-aitunnel-ynPRiPL0SFNxo2Gm1YkgWbjGsxVIdgEy",
    base_url="https://api.aitunnel.ru/v1/",
)

# Словарь для хранения выражений пользователей
user_expressions = {}

# Функция для решения математических задач
def solve_math_problem(problem: str):
    try:
        expr = sp.sympify(problem)
        result = sp.N(expr)

        if result == int(result):
            result = int(result)
        else:
            result = round(result, 10)

        result_str = str(result).rstrip('0').rstrip('.') if '.' in str(result) else str(result)
        return f"Результат: {result_str}"

    except Exception as e:
        return f"Произошла ошибка: {e}"

# Функция для создания главной клавиатуры
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Математические задачи", callback_data='math')],
        [InlineKeyboardButton("🖼 Сгенерировать изображение", callback_data='image')],
        [InlineKeyboardButton("🔊 Сгенерировать речь (TTS)", callback_data='speech')],
        [InlineKeyboardButton("🤖 ИИ помощник", callback_data='other')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Функция для клавиатуры калькулятора
def get_calculator_keyboard():
    keyboard = [
        [InlineKeyboardButton("7", callback_data='7'), InlineKeyboardButton("8", callback_data='8'), InlineKeyboardButton("9", callback_data='9')],
        [InlineKeyboardButton("4", callback_data='4'), InlineKeyboardButton("5", callback_data='5'), InlineKeyboardButton("6", callback_data='6')],
        [InlineKeyboardButton("1", callback_data='1'), InlineKeyboardButton("2", callback_data='2'), InlineKeyboardButton("3", callback_data='3')],
        [InlineKeyboardButton("0", callback_data='0'), InlineKeyboardButton("+", callback_data='+'), InlineKeyboardButton("-", callback_data='-')],
        [InlineKeyboardButton("*", callback_data='*'), InlineKeyboardButton("/", callback_data='/')],
        [InlineKeyboardButton("√", callback_data='sqrt'), InlineKeyboardButton("=", callback_data='solve')],
        [InlineKeyboardButton("Очистить", callback_data='clear')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Обработчик команды /start
async def start_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Я могу помочь с различными задачами. Выберите действие:",
        reply_markup=get_main_keyboard()
    )

# Обработчик кнопок
async def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "math":
        user_expressions[user_id] = {"expression": ""}
        await query.message.edit_text(
            "Составьте выражение с помощью кнопок:",
            reply_markup=get_calculator_keyboard()
        )

    elif query.data == "back_to_main":
        try:
            await query.message.edit_text(
                "Выберите действие:",
                reply_markup=get_main_keyboard()
            )
        except Exception:
            await query.message.reply_text(
                "Выберите действие:",
                reply_markup=get_main_keyboard()
            )
        user_expressions[user_id] = {}

    else:
        # Добавляем введенный символ в текущее выражение пользователя
        if user_id in user_expressions and "expression" in user_expressions[user_id]:
            user_expressions[user_id]["expression"] += query.data
            await query.message.edit_text(
                f"Текущее выражение: {user_expressions[user_id]['expression']}",
                reply_markup=get_calculator_keyboard()
            )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_message = update.message.text
    user_state = user_expressions.get(user_id, "other")

    if user_state == "math":
        await update.message.reply_text("Используйте кнопки калькулятора для ввода выражения.")

# Запуск Flask для хостинга
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# Основная функция
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    main()