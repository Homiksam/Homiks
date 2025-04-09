import sympy as sp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from openai import OpenAI
import os
from flask import Flask
import threading

TELEGRAM_TOKEN = "7649909820:AAG_ofyeA__Q6iLHWl1WQaFuiS6iaUhxW3Q"
client = OpenAI(
    api_key="sk-aitunnel-ynPRiPL0SFNxo2Gm1YkgWbjGsxVIdgEy",
    base_url="https://api.aitunnel.ru/v1/",
)

user_expressions = {}

# Универсальная кнопка "Назад"
def back_button():
    return [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]

# Главная клавиатура
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Математические задачи", callback_data='math')],
        [InlineKeyboardButton("🖼 Сгенерировать изображение", callback_data='image')],
        [InlineKeyboardButton("🔊 Сгенерировать речь (TTS)", callback_data='speech')],
        [InlineKeyboardButton("🤖 ИИ помощник", callback_data='other')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Калькулятор
def get_calculator_keyboard():
    keyboard = [
        [InlineKeyboardButton("7", callback_data='7'), InlineKeyboardButton("8", callback_data='8'), InlineKeyboardButton("9", callback_data='9')],
        [InlineKeyboardButton("4", callback_data='4'), InlineKeyboardButton("5", callback_data='5'), InlineKeyboardButton("6", callback_data='6')],
        [InlineKeyboardButton("1", callback_data='1'), InlineKeyboardButton("2", callback_data='2'), InlineKeyboardButton("3", callback_data='3')],
        [InlineKeyboardButton("0", callback_data='0'), InlineKeyboardButton("+", callback_data='+'), InlineKeyboardButton("-", callback_data='-')],
        [InlineKeyboardButton("*", callback_data='*'), InlineKeyboardButton("/", callback_data='/'), InlineKeyboardButton("√", callback_data='sqrt')],
        [InlineKeyboardButton("=", callback_data='solve'), InlineKeyboardButton("Очистить", callback_data='clear')],
        back_button()
    ]
    return InlineKeyboardMarkup(keyboard)

def get_simple_keyboard():
    return InlineKeyboardMarkup([back_button()])

# Решение примера
def solve_math_problem(problem: str):
    try:
        expr = sp.sympify(problem)
        result = sp.N(expr)
        result = int(result) if result == int(result) else round(result, 10)
        return f"Результат: {str(result).rstrip('0').rstrip('.') if '.' in str(result) else result}"
    except Exception as e:
        return f"Произошла ошибка: {e}"

# /start
async def start_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Я могу помочь с различными задачами. Выберите действие:",
        reply_markup=get_main_keyboard()
    )

# Обработка кнопок
async def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    def edit(text, reply_markup):
        try:
            return context.bot.edit_message_text(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                text=text,
                reply_markup=reply_markup
            )
        except Exception as e:
            return query.message.reply_text(f"Ошибка: {e}")

    data = query.data

    if data == "math":
        user_expressions[user_id] = {"expression": "", "message_id": query.message.message_id}
        await edit("Составьте выражение с помощью кнопок:", get_calculator_keyboard())

    elif data == "image":
        user_expressions[user_id] = "image"
        await edit("🖼 Введите описание изображения:", get_simple_keyboard())

    elif data == "speech":
        user_expressions[user_id] = "speech"
        await edit("🔊 Введите текст для озвучки:", get_simple_keyboard())

    elif data == "other":
        user_expressions[user_id] = "other"
        await edit("❓ Задайте вопрос, и я постараюсь помочь:", get_simple_keyboard())

    elif data == "clear":
        if user_id not in user_expressions or not isinstance(user_expressions[user_id], dict):
            user_expressions[user_id] = {"expression": "", "message_id": query.message.message_id}
        else:
            user_expressions[user_id]["expression"] = ""
        await edit("Текущее выражение: ", get_calculator_keyboard())

    elif data == "solve":
        expr = user_expressions.get(user_id, {}).get("expression", "")
        if expr:
            result = solve_math_problem(expr)
            user_expressions[user_id]["expression"] = ""
            await edit(f"Текущее выражение: {expr}\n{result}", get_calculator_keyboard())
        else:
            await edit("Введите выражение с помощью кнопок.", get_calculator_keyboard())

    elif data == "sqrt":
        expr = user_expressions.get(user_id, {}).get("expression", "")
        if expr:
            try:
                num = float(expr)
                if num < 0:
                    result = "Ошибка: нельзя извлечь корень из отрицательного числа."
                else:
                    result = str(sp.N(sp.sqrt(num))).rstrip('0').rstrip('.')
                    result = f"√{expr} = {result}"
                user_expressions[user_id]["expression"] = ""
                await edit(result, get_calculator_keyboard())
            except Exception as e:
                await edit(f"Ошибка: {e}", get_calculator_keyboard())
        else:
            await edit("Введите число для извлечения корня.", get_calculator_keyboard())

    elif data == "back_to_main":
        user_expressions[user_id] = {}
        await edit("Выберите действие:", get_main_keyboard())

    else:
        # Добавление символов в выражение
        if user_id not in user_expressions or not isinstance(user_expressions[user_id], dict):
            user_expressions[user_id] = {"expression": data, "message_id": query.message.message_id}
        else:
            user_expressions[user_id]["expression"] += data
        await edit(f"Текущее выражение: {user_expressions[user_id]['expression']}", get_calculator_keyboard())

# Обработка сообщений
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_message = update.message.text
    state = user_expressions.get(user_id, "other")

    if state == "image":
        try:
            image_res = client.images.generate(
                model="dall-e-3",
                size="1024x1024",
                quality="standard",
                prompt=user_message
            )
            image_url = image_res.data[0].url
            await update.message.reply_photo(photo=image_url, caption="Вот ваше изображение!", reply_markup=get_simple_keyboard())
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}", reply_markup=get_simple_keyboard())

    elif state == "speech":
        try:
            response = client.audio.speech.create(
                model="tts-1",
                input=user_message,
                voice="alloy"
            )
            speech_file = "speech.mp3"
            with open(speech_file, "wb") as f:
                f.write(response.content)
            await update.message.reply_voice(voice=open(speech_file, "rb"), reply_markup=get_simple_keyboard())
            os.remove(speech_file)
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}", reply_markup=get_simple_keyboard())

    elif state == "other":
        try:
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": user_message}],
                max_tokens=1000,
                model="gpt-4"
            )
            bot_response = completion.choices[0].message.content
        except Exception as e:
            bot_response = f"Ошибка: {e}"
        await update.message.reply_text(bot_response, reply_markup=get_simple_keyboard())

    else:
        await update.message.reply_text("Пожалуйста, используйте кнопки калькулятора.")

# Flask для хостинга
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# Запуск бота
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    main()
