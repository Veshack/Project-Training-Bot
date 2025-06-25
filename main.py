import logging
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

import matplotlib.pyplot as plt
from io import BytesIO

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен от BotFather
TOKEN = '7758120985:AAHOid2LvrvC2-u4kZdhnifQTLMcybn_e0o'

# Базовые группы мышц
MUSCLE_GROUPS = {
    "back": "Спина",
    "chest": "Грудь",
    "legs": "Ноги",
    "arms": "Руки",
    "shoulders": "Плечи",
    "abs": "Пресс"
}

# Стандартные упражнения для групп мышц
DEFAULT_EXERCISES = {
    "back": ["Подтягивания", "Тяга штанги", "Тяга гантели"],
    "chest": ["Жим штанги", "Жим гантелей", "Разводка гантелей"],
    "legs": ["Приседания", "Становая тяга", "Выпады"],
    "arms": ["Жим штанги узким хватом", "Подъем гантелей на бицепс", "Французский жим"],
    "shoulders": ["Жим Арнольда", "Махи гантелями", "Подъем передних дельт"],
    "abs": ["Скручивания", "Планка", "Обратные скручивания"]
}

# Хранилище пользовательских данных (временное)
user_data_storage = {}  # user_id -> {history: [...], current_workout: {...}, mode: ... }

# Клавиатура главного меню
def main_menu_keyboard():
    keyboard = [
        [KeyboardButton("🏋️‍♂️ Начать тренировку")],
        [KeyboardButton("📜 История тренировок")],
        [KeyboardButton("📊 Статистика прогресса")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Вспомогательная функция для получения ID пользователя
def get_user_data(user_id):
    if user_id not in user_data_storage:
        user_data_storage[user_id] = {"history": [], "current_workout": None, "mode": None}
    return user_data_storage[user_id]

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в тренировочный бот! 🏋️\nВыберите действие:",
        reply_markup=main_menu_keyboard()
    )

# Функция для сбора статистики по упражнениям
def get_exercise_stats(user_data):
    stats = {}
    for workout in user_data["history"]:
        for ex in workout["exercises"]:
            name = ex["name"]
            if name not in stats:
                stats[name] = []
            stats[name].append({
                "date": workout["date"],
                "sets": ex["sets"],
                "reps": ex["reps"],
                "weight": ex["weight"]
            })
    return stats

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)

    if text == "🏋️‍♂️ Начать тренировку":
        keyboard = [[KeyboardButton(group)] for group in MUSCLE_GROUPS.values()]
        keyboard.append([KeyboardButton("🏁 Завершить тренировку")])
        keyboard.append([KeyboardButton("❌ Отменить")])
        await update.message.reply_text(
            "Выберите группу мышц:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    elif text == "❌ Отменить":
        await update.message.reply_text("Тренировка отменена.", reply_markup=main_menu_keyboard())
        user_data["current_workout"] = None
        return

    elif text == "🏁 Завершить тренировку":
        if user_data["current_workout"] and user_data["current_workout"]["exercises"]:
            workout = user_data["current_workout"]
            workout["date"] = datetime.now()
            user_data["history"].append(workout)
        user_data["current_workout"] = None
        await update.message.reply_text("✅ Тренировка успешно завершена!", reply_markup=main_menu_keyboard())
        return

    elif text == "📜 История тренировок":
        history = user_data["history"]
        if not history:
            await update.message.reply_text("У вас пока нет записей о тренировках.")
            return
        msg = "📅 Последние тренировки:\n\n"
        for i, workout in enumerate(history[-100:], 1):
            date_str = workout["date"].strftime("%d.%m.%Y %H:%M")
            msg += f"{i}. 💪 {workout['group']}\n🗓 {date_str}\n"
            for ex in workout["exercises"]:
                msg += f" - {ex['name']} | {ex['sets']} сетов × {ex['reps']} повт. @ {ex['weight']} кг\n"
            msg += "\n"

        await update.message.reply_text(msg, reply_markup=main_menu_keyboard())
        return

    elif text == "📊 Статистика прогресса":
        stats = get_exercise_stats(user_data)
        if not stats:
            await update.message.reply_text("Нет данных для отображения статистики.", reply_markup=main_menu_keyboard())
            return

        user_data["mode"] = "stats_choose_exercise"
        keyboard = [[KeyboardButton(ex)] for ex in stats.keys()]
        keyboard.append([KeyboardButton("⬅️ Назад")])
        await update.message.reply_text("Выберите упражнение для анализа:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    elif text == "⬅️ Назад":
        user_data["mode"] = None
        await update.message.reply_text("Возврат в главное меню.", reply_markup=main_menu_keyboard())
        return

    # Выбор упражнения для статистики
    if user_data.get("mode") == "stats_choose_exercise":
        stats = get_exercise_stats(user_data)
        if text in stats:
            exercises = stats[text]
            dates = [ex["date"] for ex in exercises]
            weights = [ex["weight"] for ex in exercises]

            # График
            plt.figure(figsize=(10, 4))
            plt.plot(dates, weights, marker='o', linestyle='-')
            plt.title(f'Прогресс по упражнению "{text}"')
            plt.xlabel('Дата')
            plt.ylabel('Вес (кг)')
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            buf.seek(0)

            # Текстовая статистика
            max_weight = max(weights)
            avg_weight = sum(weights) / len(weights)
            total_sets = sum(ex["sets"] for ex in exercises)

            stats_text = (
                f"📈 Статистика по упражнению '{text}':\n"
                f"📌 Максимальный вес: {max_weight} кг\n"
                f"📌 Средний вес: {avg_weight:.1f} кг\n"
                f"📌 Общее количество подходов: {total_sets}"
            )

            await update.message.reply_photo(photo=buf, caption=stats_text)
            await update.message.reply_text("Выберите другое упражнение или нажмите '⬅️ Назад'.")
        return

    # Обработка выбора группы мышц
    muscle_group = next((key for key, val in MUSCLE_GROUPS.items() if val == text), None)
    if muscle_group:
        exercises = DEFAULT_EXERCISES[muscle_group]
        keyboard = [[KeyboardButton(ex)] for ex in exercises]
        keyboard.append([KeyboardButton("➕ Добавить своё упражнение")])
        keyboard.append([KeyboardButton("🏁 Завершить тренировку")])
        keyboard.append([KeyboardButton("❌ Отменить")])

        if user_data["current_workout"] is None:
            user_data["current_workout"] = {
                "group": MUSCLE_GROUPS[muscle_group],
                "exercises": [],
                "muscle_key": muscle_group
            }
        else:
            user_data["current_workout"]["group"] = MUSCLE_GROUPS[muscle_group]
            user_data["current_workout"]["muscle_key"] = muscle_group

        await update.message.reply_text(
            f"Выберите упражнение на {text}:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    # Добавление своего упражнения
    if text == "➕ Добавить своё упражнение":
        await update.message.reply_text("Введите название упражнения:")
        return
# Сохранение названия упражнения
    if user_data["current_workout"] and "new_exercise" not in user_data["current_workout"]:
        user_data["current_workout"]["new_exercise"] = text
        await update.message.reply_text("Введите количество подходов:")
        return

    # Сохранение количества подходов
    if user_data["current_workout"] and "new_exercise" in user_data["current_workout"] and "sets" not in user_data["current_workout"]:
        try:
            sets = int(text)
            user_data["current_workout"]["sets"] = sets
            await update.message.reply_text("Введите количество повторений:")
        except ValueError:
            await update.message.reply_text("Введите число!")
        return

    # Сохранение количества повторений
    if user_data["current_workout"] and "new_exercise" in user_data["current_workout"] and "reps" not in user_data["current_workout"]:
        try:
            reps = int(text)
            user_data["current_workout"]["reps"] = reps
            await update.message.reply_text("Введите вес (в кг):")
        except ValueError:
            await update.message.reply_text("Введите число!")
        return

    # Сохранение веса и возврат к группе мышц
    if user_data["current_workout"] and "new_exercise" in user_data["current_workout"] and "weight" not in user_data["current_workout"]:
        try:
            weight = float(text)
            user_data["current_workout"]["weight"] = weight

            user_data["current_workout"]["exercises"].append({
                "name": user_data["current_workout"]["new_exercise"],
                "sets": user_data["current_workout"]["sets"],
                "reps": user_data["current_workout"]["reps"],
                "weight": user_data["current_workout"]["weight"]
            })

            del user_data["current_workout"]["new_exercise"]
            del user_data["current_workout"]["sets"]
            del user_data["current_workout"]["reps"]
            del user_data["current_workout"]["weight"]

            # Возвращаем к выбору группы мышц с кнопкой завершения
            keyboard = [[KeyboardButton(group)] for group in MUSCLE_GROUPS.values()]
            keyboard.append([KeyboardButton("🏁 Завершить тренировку")])
            keyboard.append([KeyboardButton("❌ Отменить")])
            await update.message.reply_text(
                "Выберите группу мышц:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        except ValueError:
            await update.message.reply_text("Введите число!")
        return

    # Обработка стандартных упражнений
    if user_data["current_workout"] and "muscle_key" in user_data["current_workout"]:
        muscle_key = user_data["current_workout"]["muscle_key"]
        if text in DEFAULT_EXERCISES[muscle_key]:
            await update.message.reply_text(f"Вы выбрали: {text}")
            await update.message.reply_text("Введите количество подходов:")
            user_data["current_workout"]["new_exercise"] = text
            return

# Запуск бота
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    application.run_polling()
