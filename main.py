import sympy as sp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from openai import OpenAI
import threading
from flask import Flask

# Токен Telegram-бота
TELEGRAM_TOKEN = "7649909820:AAG_ofyeA__Q6iLHWl1WQaFuiS6iaUhxW3Q"

# Настройка OpenAI через AITUNNEL
client = OpenAI(
    api_key="sk-aitunnel-ynPRiPL0SFNxo2Gm1YkgWbjGsxVIdgEy",  # Подставьте ваш API-ключ
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
        return f"Ошибка: {e}"

# Функция для генерации речи
async def generate_speech(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    context.user_data['awaiting_tts'] = True
    await update.message.reply_text("Введите текст, который хотите преобразовать в речь:")

# Обработчик команды /start
async def start_command(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📊 Математические задачи", callback_data='math'),
         InlineKeyboardButton("🖼 Сгенерировать изображение", callback_data='image')],
        [InlineKeyboardButton("🔊 Сгенерировать речь (TTS)", callback_data='tts'),
         InlineKeyboardButton("❓ Другое", callback_data='other')],
        [InlineKeyboardButton("🔄 Перезапустить бота", callback_data='restart')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("✅ Бот запущен! Выберите действие:", reply_markup=reply_markup)

# Обработчик нажатий на кнопки
async def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "math":
        keyboard = [
            [InlineKeyboardButton("7", callback_data='7'), InlineKeyboardButton("8", callback_data='8'), InlineKeyboardButton("9", callback_data='9')],
            [InlineKeyboardButton("4", callback_data='4'), InlineKeyboardButton("5", callback_data='5'), InlineKeyboardButton("6", callback_data='6')],
            [InlineKeyboardButton("1", callback_data='1'), InlineKeyboardButton("2", callback_data='2'), InlineKeyboardButton("3", callback_data='3')],
            [InlineKeyboardButton("0", callback_data='0'), InlineKeyboardButton("+", callback_data='+'), InlineKeyboardButton("-", callback_data='-')],
            [InlineKeyboardButton("*", callback_data='*'), InlineKeyboardButton("/", callback_data='/')],
            [InlineKeyboardButton("🟢 = (Рассчитать)", callback_data='solve')],
            [InlineKeyboardButton("Очистить", callback_data='clear'), InlineKeyboardButton("↩️ Назад", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        user_expressions[user_id] = ""
        await query.message.reply_text("Составьте выражение с помощью кнопок:", reply_markup=reply_markup)

    elif query.data == "image":
        await query.message.reply_text("Введите описание изображения, которое хотите сгенерировать:")

    elif query.data == "tts":
        await generate_speech(query.message, context)

    elif query.data == "other":
        await query.message.reply_text("Задайте мне любой вопрос, и я постараюсь ответить!")

    elif query.data == "solve":
        answer = solve_math_problem(user_expressions.get(user_id, ""))
        await query.message.reply_text(f"Результат: {answer}")
        user_expressions[user_id] = ""

    elif query.data == "clear":
        user_expressions[user_id] = ""
        await query.message.reply_text("Выражение очищено. Начните заново.")

    elif query.data == "back":
        await start_command(query.message, context)

    elif query.data == "restart":
        await start_command(query.message, context)

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text

    if context.user_data.get('awaiting_tts'):
        context.user_data['awaiting_tts'] = False
        response = client.audio.speech.create(
            model="tts-1",
            input=user_message,
            voice="alloy"
        )
        with open("speech.mp3", "wb") as file:
            file.write(response.content)
        await update.message.reply_audio(audio=open("speech.mp3", "rb"))
        return

    try:
        number = float(user_message)
        sqrt_result = sp.sqrt(number)
        result_str = str(sp.N(sqrt_result)).rstrip('0').rstrip('.') if '.' in str(sp.N(sqrt_result)) else str(sp.N(sqrt_result))
        await update.message.reply_text(f"Корень числа {number} равен: {result_str}")
        return
    except ValueError:
        pass

    if any(char in user_message for char in ['+', '-', '*', '/', '^', '(', ')', '=']):
        answer = solve_math_problem(user_message)
        await update.message.reply_text(f"🔢 {answer}")
        return

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