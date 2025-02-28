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

        result_str = str(result)
        if '.' in result_str:
            result_str = result_str.rstrip('0').rstrip('.') 

        return f"Результат: {result_str}"

    except Exception as e:
        return f"Произошла ошибка: {e}"

# Функция для создания клавиатуры с кнопками
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Математические задачи", callback_data='math')],
        [InlineKeyboardButton("🖼 Сгенерировать изображение", callback_data='image')],
        [InlineKeyboardButton("🔊 Сгенерировать речь (TTS)", callback_data='speech')],
        [InlineKeyboardButton("🤖 ИИ помощник", callback_data='other')]  # Переименовано в ИИ помощник
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
        keyboard = [[InlineKeyboardButton("7", callback_data='7'), InlineKeyboardButton("8", callback_data='8'), InlineKeyboardButton("9", callback_data='9')],
                    [InlineKeyboardButton("4", callback_data='4'), InlineKeyboardButton("5", callback_data='5'), InlineKeyboardButton("6", callback_data='6')],
                    [InlineKeyboardButton("1", callback_data='1'), InlineKeyboardButton("2", callback_data='2'), InlineKeyboardButton("3", callback_data='3')],
                    [InlineKeyboardButton("0", callback_data='0'), InlineKeyboardButton("+", callback_data='+'), InlineKeyboardButton("-", callback_data='-')],
                    [InlineKeyboardButton("*", callback_data='*'), InlineKeyboardButton("/", callback_data='/')],
                    [InlineKeyboardButton("=", callback_data='solve'), InlineKeyboardButton("Очистить", callback_data='clear')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        user_expressions[user_id] = ""
        await query.message.reply_text("Составьте выражение с помощью кнопок:", reply_markup=reply_markup)
    
    elif query.data == "image":
        user_expressions[user_id] = "image"
        await query.message.reply_text("🖼 Введите описание изображения:")

    elif query.data == "speech":
        user_expressions[user_id] = "speech"
        await query.message.reply_text("🔊 Введите текст для озвучки:")

    elif query.data == "other":
        user_expressions[user_id] = "other"
        await query.message.reply_text(
            "❓ Задайте свой вопрос! Я могу помочь вам с любыми вопросами. Просто напишите, и я постараюсь помочь.",
            reply_markup=get_main_keyboard()
        )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_message = update.message.text
    user_state = user_expressions.get(user_id, "other")

    if user_state == "math":
        user_expression = user_expressions[user_id]
        if user_message in ['clear']:
            user_expressions[user_id] = ""
            await update.message.reply_text("Выражение очищено. Начните заново.")
        elif user_message == '=':
            answer = solve_math_problem(user_expression)
            await update.message.reply_text(answer)
            user_expressions[user_id] = ""
        else:
            user_expressions[user_id] += user_message
            await update.message.reply_text(f"Текущее выражение: {user_expressions[user_id]}")

    elif user_state == "image":
        try:
            image_res = client.images.generate(
                model="dall-e-3",
                size="1024x1024",
                quality="standard",
                prompt=user_message
            )
            image_url = image_res.data[0].url
            await update.message.reply_photo(photo=image_url, caption="Вот ваше изображение!")
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}")

    elif user_state == "speech":
        try:
            response = client.audio.speech.create(
                model="tts-1",
                input=user_message,
                voice="alloy"
            )
            speech_file = "speech.mp3"
            with open(speech_file, "wb") as file:
                file.write(response.content)
            await update.message.reply_voice(voice=open(speech_file, "rb"))
            os.remove(speech_file)
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}")

    elif user_state == "other":
        try:
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": user_message}],
                max_tokens=1000,
                model="gpt-4"
            )
            bot_response = completion.choices[0].message.content
        except Exception as e:
            bot_response = f"Ошибка: {e}"
        
        await update.message.reply_text(bot_response)

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
