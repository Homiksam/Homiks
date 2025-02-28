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

# Функция для создания клавиатуры калькулятора
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

# Функция для создания клавиатуры для изображения
def get_image_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Функция для создания клавиатуры для речи
def get_speech_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Функция для создания клавиатуры ИИ помощника
def get_ai_assistant_keyboard():
    keyboard = [
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
        user_expressions[user_id] = ""
        # Создаем новое сообщение и отправляем клавиатуру калькулятора
        message = await query.message.reply_text(
            "Составьте выражение с помощью кнопок:",
            reply_markup=get_calculator_keyboard()
        )
        # Сохраняем id сообщения, чтобы можно было обновить его
        user_expressions[user_id] = {"expression": "", "message_id": message.message_id}
    
    elif query.data == "image":
        user_expressions[user_id] = "image"
        await query.message.reply_text("🖼 Введите описание изображения:", reply_markup=get_image_keyboard())

    elif query.data == "speech":
        user_expressions[user_id] = "speech"
        await query.message.reply_text("🔊 Введите текст для озвучки:", reply_markup=get_speech_keyboard())

    elif query.data == "other":
        user_expressions[user_id] = "other"
        await query.message.reply_text(
            "❓ Задайте свой вопрос! Я могу помочь вам с любыми вопросами. Просто напишите, и я постараюсь помочь.",
            reply_markup=get_ai_assistant_keyboard()
        )

    elif query.data == "clear":
        user_expressions[user_id] = ""
        await query.message.reply_text("Выражение очищено. Начните заново.", reply_markup=get_calculator_keyboard())

    elif query.data == "solve":
        user_expression = user_expressions.get(user_id, "").get("expression", "")
        if user_expression:
            answer = solve_math_problem(user_expression)
            # Обновляем текст в том же сообщении
            await query.message.edit_text(f"Текущее выражение: {user_expression}\n{answer}", reply_markup=get_calculator_keyboard())
            user_expressions[user_id]["expression"] = ""  # Очищаем выражение после вычисления
        else:
            await query.message.reply_text("Пожалуйста, введите выражение через кнопки калькулятора.", reply_markup=get_calculator_keyboard())
        
    elif query.data == "sqrt":
        # Если в выражении есть число, считаем его квадратный корень
        user_expression = user_expressions.get(user_id, "").get("expression", "")
        if user_expression:
            try:
                # Преобразуем выражение и вычисляем квадратный корень
                num = float(user_expression)
                if num < 0:
                    result = "Ошибка: Не можно вычислить квадратный корень из отрицательного числа."
                else:
                    result = sp.sqrt(num)
                    result = sp.N(result)
                    result_str = str(result)
                    if '.' in result_str:
                        result_str = result_str.rstrip('0').rstrip('.') 

                    result = f"Квадратный корень из {user_expression} = {result_str}"
                await query.message.edit_text(result, reply_markup=get_calculator_keyboard())
                user_expressions[user_id]["expression"] = ""  # Очищаем выражение после вычисления
            except Exception as e:
                await query.message.edit_text(f"Ошибка: {e}", reply_markup=get_calculator_keyboard())
        else:
            await query.message.edit_text("Пожалуйста, введите число для вычисления квадратного корня.", reply_markup=get_calculator_keyboard())

    elif query.data == "back_to_main":
        # Возвращаемся в главное меню
        await query.message.edit_text(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        # Очищаем состояние пользователя
        user_expressions[user_id] = {}

    else:
        # Добавляем введенный символ в текущее выражение пользователя
        user_expressions[user_id]["expression"] += query.data
        # Обновляем текст в том же сообщении
        await query.message.edit_text(f"Текущее выражение: {user_expressions[user_id]['expression']}", reply_markup=get_calculator_keyboard())

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_message = update.message.text
    user_state = user_expressions.get(user_id, "other")

    if user_state == "math":
        # Если сообщение не содержит чисел или операторов, оно не будет обработано
        await update.message.reply_text("Пожалуйста, используйте кнопки для ввода математического выражения.")
    elif user_state == "image":
        try:
            image_res = client.images.generate(
                model="dall-e-3",
                size="1024x1024",
                quality="standard",
                prompt=user_message
            )
            image_url = image_res.data[0].url
            await update.message.reply_photo(photo=image_url, caption="Вот ваше изображение!", reply_markup=get_image_keyboard())
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}", reply_markup=get_image_keyboard())
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
            await update.message.reply_voice(voice=open(speech_file, "rb"), reply_markup=get_speech_keyboard())
            os.remove(speech_file)
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}", reply_markup=get_speech_keyboard())
    elif user_state == "other":
        # Обработка обычных сообщений, если это не математическое выражение
        try:
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": user_message}],
                max_tokens=1000,
                model="gpt-4"
            )
            bot_response = completion.choices[0].message.content
        except Exception as e:
            bot_response = f"Ошибка: {e}"
        
        await update.message.reply_text(bot_response, reply_markup=get_ai_assistant_keyboard())

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
