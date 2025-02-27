import sympy as sp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from openai import OpenAI
from flask import Flask
import threading

# Токен Telegram-бота
TELEGRAM_TOKEN = "7649909820:AAG_ofyeA__Q6iLHWl1WQaFuiS6iaUhxW3Q"

# Настройка OpenAI через AITUNNEL
client = OpenAI(
    api_key="sk-aitunnel-ynPRiPL0SFNxo2Gm1YkgWbjGsxVIdgEy",  # Ключ из нашего сервиса
    base_url="https://api.aitunnel.ru/v1/",
)

# Словарь для хранения выражений пользователей
user_expressions = {}

# Функция для решения математических задач
def solve_math_problem(problem: str):
    try:
        expr = sp.sympify(problem)
        result = sp.N(expr)
        result_str = str(int(result)) if result == int(result) else str(result).rstrip('0').rstrip('.')
        return f"Результат: {result_str}"
    except Exception as e:
        return f"Произошла ошибка: {e}"

# Обработчик команды /start
async def start_command(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Математические задачи", callback_data='math')],
        [InlineKeyboardButton("Сгенерировать изображение", callback_data='image')],
        [InlineKeyboardButton("Сгенерировать речь (TTS)", callback_data='speech')],
        [InlineKeyboardButton("Другое", callback_data='other')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Я бот, который может решать задачи, отвечать на вопросы, генерировать изображения и синтезировать речь.\n\nВыберите действие:",
        reply_markup=reply_markup
    )

# Обработчик кнопок
async def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == "math":
        await query.message.reply_text("Введите математическое выражение.")

    elif query.data == "image":
        await query.message.reply_text("Введите описание изображения, которое хотите сгенерировать.")

    elif query.data == "speech":
        await query.message.reply_text("Введите текст, который хотите преобразовать в голосовое сообщение.")

    elif query.data == "other":
        await query.message.reply_text("Задайте мне любой вопрос, и я постараюсь ответить!")

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text

    # Проверка на математические выражения
    if any(char in user_message for char in ['+', '-', '*', '/', '^', '(', ')', '=', 'x', 'y', 'z']):
        answer = solve_math_problem(user_message)
        await update.message.reply_text(f"🔢 {answer}")
        return

    # Генерация речи (TTS), если пользователь запросил
    if user_message.lower().startswith("скажи ") or len(user_message) < 100:
        try:
            response = client.audio.speech.create(
                model="tts-1",
                input=user_message,
                voice="alloy"
            )
            with open("speech.mp3", "wb") as file:
                file.write(response.content)
            await update.message.reply_voice(voice=open("speech.mp3", "rb"))
        except Exception as e:
            await update.message.reply_text(f"Ошибка при генерации речи: {e}")
        return

    # Генерация изображения, если введен длинный текст (предполагаем, что это описание)
    if len(user_message) > 10:
        try:
            image_res = client.images.generate(
                model="dall-e-3",
                size="1024x1024",
                quality="standard",
                prompt=user_message
            )
            image_url = image_res.data[0].url
            await update.message.reply_photo(photo=image_url, caption="Вот ваше изображение!")
            return
        except Exception as e:
            await update.message.reply_text(f"Ошибка при генерации изображения: {e}")
            return

    # Генерация текстового ответа от ИИ
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": user_message}],
            max_tokens=1000,
            model="gpt-4"
        )
        bot_response = completion.choices[0].message.content
    except Exception as e:
        bot_response = f"Произошла ошибка: {e}"

    await update.message.reply_text(bot_response)

# Запуск бота
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

# Запуск Flask для хостинга
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    main()