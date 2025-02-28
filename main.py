import sympy as sp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext, ChatMemberHandler
from telegram.constants import ChatMemberStatus
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

# Словарь для хранения состояний пользователей
user_states = {}

# Функция для создания клавиатуры с кнопками
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Математические задачи", callback_data='math')],
        [InlineKeyboardButton("🖼 Сгенерировать изображение", callback_data='image')],
        [InlineKeyboardButton("🔊 Сгенерировать речь (TTS)", callback_data='speech')],
        [InlineKeyboardButton("❓ Другое", callback_data='other')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Функция для решения математических задач
def solve_math_problem(problem: str):
    try:
        expr = sp.sympify(problem)
        result = sp.N(expr)
        return f"Результат: {result}" if result != int(result) else f"Результат: {int(result)}"
    except Exception as e:
        return f"Ошибка: {e}"

# Обработчик команды /start
async def start_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Выберите действие:",
        reply_markup=get_main_keyboard()
    )

# Обработчик входа пользователя в чат
async def chat_member_update(update: Update, context: CallbackContext):
    new_status = update.chat_member.new_chat_member.status
    if new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
        await context.bot.send_message(
            chat_id=update.chat_member.chat.id,
            text="Привет! Выберите действие:",
            reply_markup=get_main_keyboard()
        )

# Обработчик кнопок
async def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if query.data == "math":
        user_states[user_id] = "math"
        message = "🔢 Введите математическое выражение:"
    elif query.data == "image":
        user_states[user_id] = "image"
        message = "🖼 Введите описание изображения:"
    elif query.data == "speech":
        user_states[user_id] = "speech"
        message = "🔊 Введите текст для озвучки:"
    elif query.data == "other":
        user_states[user_id] = "other"
        message = "❓ Задайте свой вопрос:"
    
    await query.message.edit_text(text=message, reply_markup=get_main_keyboard())

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_message = update.message.text
    user_state = user_states.get(user_id, "other")
    
    if user_state == "math":
        answer = solve_math_problem(user_message)
        await update.message.reply_text(answer, reply_markup=get_main_keyboard())
    elif user_state == "image":
        try:
            image_res = client.images.generate(
                model="dall-e-3",
                size="1024x1024",
                quality="standard",
                prompt=user_message
            )
            image_url = image_res.data[0].url
            await update.message.reply_photo(photo=image_url, caption="Вот ваше изображение!", reply_markup=get_main_keyboard())
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}", reply_markup=get_main_keyboard())
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
    else:
        try:
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": user_message}],
                max_tokens=1000,
                model="gpt-4"
            )
            bot_response = completion.choices[0].message.content
        except Exception as e:
            bot_response = f"Ошибка: {e}"
        
        await update.message.reply_text(bot_response, reply_markup=get_main_keyboard())

# Запуск бота
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER))
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
