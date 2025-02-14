import sympy as sp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from openai import OpenAI

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
        # Преобразуем строку в выражение sympy
        expr = sp.sympify(problem)

        # Вычисляем результат
        result = sp.N(expr)

        # Если результат — целое число, возвращаем его как целое
        if result == int(result):
            result = int(result)
        else:
            result = round(result, 10)  # Округляем результат до 10 знаков после запятой

        # Убираем лишние нули после запятой
        result_str = str(result)
        if '.' in result_str:
            result_str = result_str.rstrip('0').rstrip('.')  # Убираем нули и точку, если числа нет

        return f"Результат: {result_str}"

    except Exception as e:
        return f"Произошла ошибка: {e}"

# Функция для обработки выбора кнопок
async def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "math":
        # Убираем кнопку корня из основного калькулятора
        keyboard = [[InlineKeyboardButton("7", callback_data='7'), InlineKeyboardButton("8", callback_data='8'), InlineKeyboardButton("9", callback_data='9')],
                    [InlineKeyboardButton("4", callback_data='4'), InlineKeyboardButton("5", callback_data='5'), InlineKeyboardButton("6", callback_data='6')],
                    [InlineKeyboardButton("1", callback_data='1'), InlineKeyboardButton("2", callback_data='2'), InlineKeyboardButton("3", callback_data='3')],
                    [InlineKeyboardButton("0", callback_data='0'), InlineKeyboardButton("+", callback_data='+'), InlineKeyboardButton("-", callback_data='-')],
                    [InlineKeyboardButton("*", callback_data='*'), InlineKeyboardButton("/", callback_data='/')],
                    [InlineKeyboardButton("=", callback_data='solve'), InlineKeyboardButton("Очистить", callback_data='clear')],
                    [InlineKeyboardButton("Вычислить корень", callback_data='sqrt')]]  # Добавляем кнопку для корня
        reply_markup = InlineKeyboardMarkup(keyboard)
        user_expressions[user_id] = ""
        await query.message.reply_text("Составьте выражение с помощью кнопок:", reply_markup=reply_markup)
    elif query.data == "other":
        await query.message.reply_text("Задайте мне любой вопрос, и я постараюсь ответить!")
    elif query.data == "sqrt":
        # Обработка кнопки "Вычислить корень"
        await query.message.reply_text("Пожалуйста, введите число, для которого нужно вычислить корень:")
    else:
        user_expression = user_expressions.get(user_id, "")
        if query.data == "solve":
            answer = solve_math_problem(user_expression)
            await query.message.reply_text(f"Результат: {answer}")
            user_expressions[user_id] = ""
        elif query.data == "clear":
            user_expressions[user_id] = ""
            await query.message.reply_text("Выражение очищено. Начните заново.")
        else:
            user_expressions[user_id] += query.data
        await query.message.edit_text(f"Текущее выражение: {user_expressions[user_id]}", reply_markup=query.message.reply_markup)

# Функция для обработки сообщений
async def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    
    # Проверяем, содержит ли сообщение приветствие
    if user_message.lower() in ["привет", "здравствуй", "добрый день", "добрый вечер", "хай"]:
        keyboard = [[InlineKeyboardButton("Математические задачи", callback_data='math')],
                    [InlineKeyboardButton("Другое", callback_data='other')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Привет! Я могу помочь с любыми вопросами. Выберите, что хотите сделать:", reply_markup=reply_markup)
        return
    
    # Проверяем, является ли сообщение числом для корня
    try:
        number = float(user_message)
        sqrt_result = sp.sqrt(number)
        result = sp.N(sqrt_result)
        
        # Убираем лишние нули после запятой
        result_str = str(result)
        if '.' in result_str:
            result_str = result_str.rstrip('0').rstrip('.')  # Убираем нули и точку, если числа нет

        await update.message.reply_text(f"Корень числа {number} равен: {result_str}")
        return  # Выход из функции, если вычислили корень
    
    except ValueError:
        pass  # Если это не число, то не будем делать ничего

    # Проверяем, содержит ли сообщение математическое выражение
    if any(char in user_message for char in ['+', '-', '*', '/', '^', '(', ')', '=', 'x', 'y', 'z']):
        answer = solve_math_problem(user_message)
        if answer:
            await update.message.reply_text(f"🔢 {answer}")
            return  # Если удалось решить, выходим из функции
    
    # Если не математическое выражение, передаем запрос в OpenAI
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

# Основная функция
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
