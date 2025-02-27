import sympy as sp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from openai import OpenAI
from flask import Flask
import threading
import os

# Токен Telegram-бота
TELEGRAM_TOKEN = "7649909820:AAG_ofyeA__Q6iLHWl1WQaFuiS6iaUhxW3Q"

# Настройка OpenAI через AITUNNEL
client = OpenAI(
    api_key="sk-aitunnel-ynPRiPL0SFNxo2Gm1YkgWbjGsxVIdgEy",
    base_url="https://api.aitunnel.ru/v1/",
)

# Словари для хранения состояний и выражений пользователей
user_states = {}       # для хранения режима: "math", "image", "speech", "other", "menu"
user_expressions = {}  # для хранения текущего математического выражения

#############################################
# Функция решения математических задач
def solve_math_problem(problem: str):
    try:
        expr = sp.sympify(problem)
        result = sp.N(expr)
        if result == int(result):
            result = int(result)
        else:
            result = round(result, 10)
        result_str = str(result)
        if '.' in result_str:
            result_str = result_str.rstrip('0').rstrip('.')
        return f"Результат: {result_str}"
    except Exception as e:
        return f"Произошла ошибка: {e}"

#############################################
# Главное меню с постоянной клавиатурой
def get_main_menu():
    keyboard = [
        [KeyboardButton("📊 Математические задачи"), KeyboardButton("🖼 Сгенерировать изображение")],
        [KeyboardButton("🔊 Сгенерировать речь (TTS)"), KeyboardButton("❓ Другое")],
        [KeyboardButton("🔄 Перезапустить бота")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

#############################################
# Первое приветственное сообщение при заходе
async def welcome_message(update: Update, context: CallbackContext):
    keyboard = [[KeyboardButton("🔄 Запустить бота")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "👋 Привет! Нажмите кнопку ниже, чтобы запустить бота.",
        reply_markup=reply_markup
    )
    # Сбрасываем состояние пользователя
    user_states[update.message.from_user.id] = "menu"

#############################################
# Обработчик команды /start (если вдруг введут)
async def start_command(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_states[user_id] = "menu"
    await update.message.reply_text(
        "✅ Бот запущен! Выберите действие:",
        reply_markup=get_main_menu()
    )

#############################################
# Обработчик inline-кнопок (например, для калькулятора)
async def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Если нажали кнопку "math" — запускаем калькулятор
    if query.data == "math":
        user_states[user_id] = "math"
        # Inline-клавиатура для математического выражения
        keyboard = [
    [InlineKeyboardButton("7", callback_data='7'), InlineKeyboardButton("8", callback_data='8'), InlineKeyboardButton("9", callback_data='9')],
    [InlineKeyboardButton("4", callback_data='4'), InlineKeyboardButton("5", callback_data='5'), InlineKeyboardButton("6", callback_data='6')],
    [InlineKeyboardButton("1", callback_data='1'), InlineKeyboardButton("2", callback_data='2'), InlineKeyboardButton("3", callback_data='3')],
    [InlineKeyboardButton("0", callback_data='0'), InlineKeyboardButton("+", callback_data='+'), InlineKeyboardButton("-", callback_data='-')],
    [InlineKeyboardButton("*", callback_data='*'), InlineKeyboardButton("/", callback_data='/')],
    [InlineKeyboardButton("🟩 = 🟩", callback_data='solve')],  # Выделенная кнопка "="
    [InlineKeyboardButton("Очистить", callback_data='clear'), InlineKeyboardButton("Вычислить корень", callback_data='sqrt')],
    [InlineKeyboardButton("🔙 Назад", callback_data='back')]
]
        reply_markup = InlineKeyboardMarkup(keyboard)
        user_expressions[user_id] = ""
        await query.message.reply_text("🔢 Составьте выражение с помощью кнопок:", reply_markup=reply_markup)
    
    elif query.data == "other":
        user_states[user_id] = "other"
        # При выборе "Другое" выводим инструкцию с кнопкой "Назад"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("❓ Задайте мне любой вопрос, и я постараюсь ответить!", reply_markup=reply_markup)
    
    elif query.data == "sqrt":
        await query.message.reply_text("Пожалуйста, введите число, для которого нужно вычислить корень:")
    
    elif query.data == "back":
        # Возврат к главному меню
        user_states[user_id] = "menu"
        await query.message.reply_text("Вы вернулись в главное меню.", reply_markup=get_main_menu())
    
    else:
        # Обработка ввода для математического выражения
        current_expr = user_expressions.get(user_id, "")
        if query.data == "solve":
            answer = solve_math_problem(current_expr)
            await query.message.reply_text(f"🔢 {answer}")
            user_expressions[user_id] = ""
        elif query.data == "clear":
            user_expressions[user_id] = ""
            await query.message.reply_text("Выражение очищено. Начните заново.")
        else:
            user_expressions[user_id] = current_expr + query.data
        # Обновляем сообщение с текущим выражением
        await query.message.edit_text(f"Текущее выражение: {user_expressions[user_id]}", reply_markup=query.message.reply_markup)

#############################################
# Обработчик текстовых сообщений (для других режимов)
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_message = update.message.text

    # Если пользователь нажал кнопку "🔄 Запустить бота" или "🔄 Перезапустить бота"
    if user_message == "🔄 Запустить бота" or user_message == "🔄 Перезапустить бота":
        user_states[user_id] = "menu"
        await update.message.reply_text("✅ Бот запущен!", reply_markup=get_main_menu())
        return

    # Если пользователь только что запустил бота, отправляем главное меню
    if user_states.get(user_id, "menu") == "menu":
        # Здесь можно обрабатывать текст как запрос в режим "other"
        try:
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": user_message}],
                max_tokens=1000,
                model="gpt-4"
            )
            bot_response = completion.choices[0].message.content
        except Exception as e:
            bot_response = f"Произошла ошибка: {e}"
        await update.message.reply_text(bot_response, reply_markup=get_main_menu())
        return

    # Режимы, заданные через главное меню:
    current_state = user_states.get(user_id, "other")
    
    if current_state == "math":
        # Если пользователь ввёл текст вместо нажатия inline-кнопок — пробуем решить как выражение
        answer = solve_math_problem(user_message)
        await update.message.reply_text(f"🔢 {answer}", reply_markup=get_main_menu())
    
    elif current_state == "image":
        try:
            image_res = client.images.generate(
                model="dall-e-3",
                size="1024x1024",
                quality="standard",
                prompt=user_message
            )
            image_url = image_res.data[0].url
            await update.message.reply_photo(photo=image_url, caption="Вот ваше изображение!", reply_markup=get_main_menu())
        except Exception as e:
            await update.message.reply_text(f"Ошибка при генерации изображения: {e}", reply_markup=get_main_menu())
    
    elif current_state == "speech":
        try:
            response = client.audio.speech.create(
                model="tts-1",
                input=user_message,
                voice="alloy"
            )
            speech_file = "speech.mp3"
            with open(speech_file, "wb") as file:
                file.write(response.content)
            await update.message.reply_voice(voice=open(speech_file, "rb"), reply_markup=get_main_menu())
            os.remove(speech_file)
        except Exception as e:
            await update.message.reply_text(f"Ошибка при генерации речи: {e}", reply_markup=get_main_menu())
    
    elif current_state == "other":
        try:
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": user_message}],
                max_tokens=1000,
                model="gpt-4"
            )
            bot_response = completion.choices[0].message.content
        except Exception as e:
            bot_response = f"Произошла ошибка: {e}"
        await update.message.reply_text(bot_response, reply_markup=get_main_menu())

#############################################
# Основная функция для запуска бота
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    # При новом входе (NEW_CHAT_MEMBERS) отправляем приветственное сообщение
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_message))
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

#############################################
# Flask для хостинга
app = Flask(__name__)
@app.route('/')
def home():
    return "Бот работает!"
def run_flask():
    app.run(host="0.0.0.0", port=10000)

#############################################
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    main()