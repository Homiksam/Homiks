import sympy as sp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from openai import OpenAI
from flask import Flask
import threading
import os

# Токен Telegram-бота
TELEGRAM_TOKEN = "7649909820:AAG_ofyeA__Q6iLHWl1WQaFuiS6iaUhxW3Q"

# Настройка OpenAI через AITUNNEL
client = OpenAI(
    api_key="sk-aitunnel-ynPRiPL0SFNxo2Gm1YkgWbjGsxVIdgEy",  # Ключ из нашего сервиса
    base_url="https://api.aitunnel.ru/v1/",
)

# Словарь для хранения состояний пользователей
user_states = {}

# Главное меню
async def show_main_menu(update: Update):
    keyboard = [
        [InlineKeyboardButton("📊 Математические задачи", callback_data='math')],
        [InlineKeyboardButton("🖼 Сгенерировать изображение", callback_data='image')],
        [InlineKeyboardButton("🔊 Сгенерировать речь (TTS)", callback_data='speech')],
        [InlineKeyboardButton("❓ Другое", callback_data='other')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Я бот, который может:\n\n✅ Решать математические задачи\n✅ Генерировать изображения\n✅ Преобразовывать текст в речь\n✅ Отвечать на вопросы\n\nВыберите действие:",
        reply_markup=reply_markup
    )

# Функция для обработки кнопки "Назад"
async def back_to_main(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_states[query.from_user.id] = "menu"
    await show_main_menu(query)

# Обработчик команды /start
async def start_command(update: Update, context: CallbackContext):
    await show_main_menu(update)

# Функция для решения математических задач
def solve_math_problem(problem: str):
    try:
        expr = sp.sympify(problem)
        result = sp.N(expr)
        result_str = str(int(result)) if result == int(result) else str(result).rstrip('0').rstrip('.')
        return f"Результат: {result_str}"
    except Exception as e:
        return f"Произошла ошибка: {e}"

# Обработчик кнопок
async def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    back_button = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]

    if query.data == "math":
        user_states[user_id] = "math"
        reply_markup = InlineKeyboardMarkup(back_button)
        await query.message.reply_text(
            "🔢 *Вы выбрали режим математических задач.*\n\nВведите выражение, например: `2+2*3` или `sqrt(16)`.",
            reply_markup=reply_markup
        )

    elif query.data == "image":
        user_states[user_id] = "image"
        reply_markup = InlineKeyboardMarkup(back_button)
        await query.message.reply_text(
            "🖼 *Вы выбрали генерацию изображения.*\n\nВведите описание картинки, например: `космический корабль, летающий над Марсом`.",
            reply_markup=reply_markup
        )

    elif query.data == "speech":
        user_states[user_id] = "speech"
        reply_markup = InlineKeyboardMarkup(back_button)
        await query.message.reply_text(
            "🔊 *Вы выбрали генерацию речи (TTS).*\n\nВведите текст, который хотите преобразовать в голосовое сообщение.",
            reply_markup=reply_markup
        )

    elif query.data == "other":
        user_states[user_id] = "other"
        reply_markup = InlineKeyboardMarkup(back_button)
        await query.message.reply_text(
            "❓ *Вы выбрали общение с ИИ.*\n\nЗадайте мне любой вопрос, и я постараюсь ответить!",
            reply_markup=reply_markup
        )

    elif query.data == "back":
        await back_to_main(query, context)

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_message = update.message.text

    # Проверяем, в каком режиме находится пользователь
    user_state = user_states.get(user_id, "other")

    if user_state == "math":
        answer = solve_math_problem(user_message)
        await update.message.reply_text(f"🔢 {answer}")
        return

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
            await update.message.reply_text(f"Ошибка при генерации изображения: {e}")
        return

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
            os.remove(speech_file)  # Удаляем файл после отправки
        except Exception as e:
            await update.message.reply_text(f"Ошибка при генерации речи: {e}")
        return

    else:
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