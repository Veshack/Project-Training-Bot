import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

import matplotlib.pyplot as plt
from io import BytesIO

class Database:
    def __init__(self, db_name='workout_bot.db'):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Таблица тренировок
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            workout_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            muscle_group TEXT,
            workout_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Таблица упражнений
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER,
            name TEXT,
            sets INTEGER,
            reps INTEGER,
            weight REAL,
            FOREIGN KEY (workout_id) REFERENCES workouts (workout_id)
        )
        ''')
        
        self.conn.commit()

    def save_workout(self, user_id, username, muscle_group, exercises):
        cursor = self.conn.cursor()
        
        # Сохраняем пользователя (если еще не сохранен)
        cursor.execute(
            'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
            (user_id, username)
        )
        
        # Сохраняем тренировку
        cursor.execute(
            'INSERT INTO workouts (user_id, muscle_group) VALUES (?, ?)',
            (user_id, muscle_group)
        )
        workout_id = cursor.lastrowid
        
        # Сохраняем упражнения
        for ex in exercises:
            cursor.execute(
                '''INSERT INTO exercises 
                (workout_id, name, sets, reps, weight) 
                VALUES (?, ?, ?, ?, ?)''',
                (workout_id, ex['name'], ex['sets'], ex['reps'], ex['weight'])
            )
        
        self.conn.commit()

    def get_user_history(self, user_id, limit=100):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT w.workout_id, w.muscle_group, w.workout_date,
                   e.name, e.sets, e.reps, e.weight
            FROM workouts w
            JOIN exercises e ON w.workout_id = e.workout_id
            WHERE w.user_id = ?
            ORDER BY w.workout_date DESC
            LIMIT ?
        ''', (user_id, limit))
        return cursor.fetchall()

    def get_exercise_stats(self, user_id, exercise_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT w.workout_date, e.weight
            FROM exercises e
            JOIN workouts w ON e.workout_id = w.workout_id
            WHERE w.user_id = ? AND e.name = ?
            ORDER BY w.workout_date
        ''', (user_id, exercise_name))
        return cursor.fetchall()

    def close(self):
        self.conn.close()
        
class Exercise:
    """Базовый класс для упражнения"""
    def __init__(self, name: str, sets: int, reps: int, weight: float):
        """
        @brief Конструктор класса Exercise
        @param name: Название упражнения
        @param sets: Количество подходов
        @param reps: Количество повторений
        @param weight: Вес (кг)
        """
        self.name = name
        self.sets = sets
        self.reps = reps
        self.weight = weight


class WeightExercise(Exercise):
    """Класс для упражнений с весом"""
    def __init__(self, name: str, sets: int, reps: int, weight: float):
        """
        @brief Конструктор класса WeightExercise
        @inheritDoc Exercise
        """
        super().__init__(name, sets, reps, weight)


class BodyweightExercise(Exercise):
    """Класс для упражнений с собственным весом"""
    def __init__(self, name: str, sets: int, reps: int):
        """
        @brief Конструктор класса BodyweightExercise
        @param name: Название упражнения
        @param sets: Количество подходов
        @param reps: Количество повторений
        """
        super().__init__(name, sets, reps, 0)  # Вес = 0 для упражнений с собственным весом


class WorkoutBot:
    """Основной класс тренировочного бота"""
    def __init__(self, token: str):
        self.token = token
        self.db = Database()
        
        # Базовые группы мышц
        self.MUSCLE_GROUPS = {
            "back": "Спина",
            "chest": "Грудь",
            "legs": "Ноги",
            "arms": "Руки",
            "shoulders": "Плечи",
            "abs": "Пресс"
        }
        
        # Стандартные упражнения
        self.DEFAULT_EXERCISES = {
            "back": ["Подтягивания", "Тяга штанги", "Тяга гантели"],
            "chest": ["Жим штанги", "Жим гантелей", "Разводка гантелей"],
            "legs": ["Приседания", "Становая тяга", "Выпады"],
            "arms": ["Жим штанги узким хватом", "Подъем гантелей на бицепс", "Французский жим"],
            "shoulders": ["Жим Арнольда", "Махи гантелями", "Подъем передних дельт"],
            "abs": ["Скручивания", "Планка", "Обратные скручивания"]
        }

        # Временное хранилище данных пользователей
        self.user_data_storage = {}

    def get_user_data(self, user_id: int) -> Dict:
        """Получение данных пользователя"""
        if user_id not in self.user_data_storage:
            self.user_data_storage[user_id] = {
                "history": [],
                "current_workout": None,
                "mode": None
            }
        return self.user_data_storage[user_id]

    def main_menu_keyboard(self) -> ReplyKeyboardMarkup:
        """Клавиатура главного меню"""
        keyboard = [
            [KeyboardButton("🏋️‍♂️ Начать тренировку")],
            [KeyboardButton("📜 История тренировок")],
            [KeyboardButton("📊 Статистика прогресса")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        await update.message.reply_text(
            "Добро пожаловать в тренировочный бот! 🏋️\nВыберите действие:",
            reply_markup=self.main_menu_keyboard()
        )

    async def show_workout_history(self, update: Update, user_id: int) -> None:
        """Отображение истории тренировок"""
        history = self.db.get_user_history(user_id)
        if not history:
            await update.message.reply_text("У вас пока нет записей о тренировках.")
            return
        
        msg = "📅 Последние тренировки:\n\n"
        current_workout_id = None
        for row in history:
            if row[0] != current_workout_id:
                date_str = datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
                msg += f"💪 {row[1]}\n🗓 {date_str}\n"
                current_workout_id = row[0]
            msg += f" - {row[3]}: {row[4]}x{row[5]} @ {row[6]} кг\n"
        
        await update.message.reply_text(msg, reply_markup=self.main_menu_keyboard())

    async def show_exercise_stats(self, update: Update, user_id: int, exercise_name: str) -> None:
        """Отображение статистики по упражнению"""
        stats = self.db.get_exercise_stats(user_id, exercise_name)
        if not stats:
            await update.message.reply_text("Нет данных для этого упражнения.")
            return

        # Подготовка данных для графика
        dates = [datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") for row in stats]
        weights = [row[1] for row in stats]

        # Создание графика
        plt.figure(figsize=(10, 5))
        plt.plot(dates, weights, marker='o', linestyle='-')
        plt.title(f'Прогресс по упражнению "{exercise_name}"')
        plt.xlabel('Дата')
        plt.ylabel('Вес (кг)')
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Сохранение графика в буфер
        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)

        # Расчет статистики
        max_weight = max(weights)
        avg_weight = sum(weights) / len(weights)
        total_workouts = len(stats)

        stats_text = (
            f"📈 Статистика по '{exercise_name}':\n"
            f"📌 Максимальный вес: {max_weight} кг\n"
            f"📌 Средний вес: {avg_weight:.1f} кг\n"
            f"📌 Всего тренировок: {total_workouts}"
        )

        await update.message.reply_photo(photo=buf, caption=stats_text)

    async def handle_new_exercise(self, update: Update, user_data: Dict, text: str) -> bool:
        """Обработка ввода данных нового упражнения"""
        current = user_data["current_workout"]
        
        if "new_exercise" not in current:
            current["new_exercise"] = text
            await update.message.reply_text("Введите количество подходов:")
            return True
            
        elif "sets" not in current:
            try:
                current["sets"] = int(text)
                await update.message.reply_text("Введите количество повторений:")
                return True
            except ValueError:
                await update.message.reply_text("Введите число!")
                return False
                
        elif "reps" not in current:
            try:
                current["reps"] = int(text)
                await update.message.reply_text("Введите вес (в кг):")
                return True
            except ValueError:
                await update.message.reply_text("Введите число!")
                return False
                
        elif "weight" not in current:
            try:
                current["weight"] = float(text)
                
                # Добавляем упражнение
                if "exercises" not in current:
                    current["exercises"] = []
                
                current["exercises"].append({
                    "name": current["new_exercise"],
                    "sets": current["sets"],
                    "reps": current["reps"],
                    "weight": current["weight"]
                })
                
                # Очищаем временные данные
                for key in ["new_exercise", "sets", "reps", "weight"]:
                    if key in current:
                        del current[key]
                
                # Возвращаем к выбору группы мышц
                keyboard = [[KeyboardButton(group)] for group in self.MUSCLE_GROUPS.values()]
                keyboard.append([KeyboardButton("🏁 Завершить тренировку")])
                keyboard.append([KeyboardButton("❌ Отменить")])
                
                await update.message.reply_text(
                    "Выберите группу мышц:",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return True
            except ValueError:
                await update.message.reply_text("Введите число!")
                return False
        return False

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Основной обработчик сообщений"""
        text = update.message.text
        user_id = update.effective_user.id
        username = update.effective_user.username or str(user_id)
        user_data = self.get_user_data(user_id)

        try:
            if text == "🏋️‍♂️ Начать тренировку":
                keyboard = [[KeyboardButton(group)] for group in self.MUSCLE_GROUPS.values()]
                keyboard.append([KeyboardButton("🏁 Завершить тренировку")])
                keyboard.append([KeyboardButton("❌ Отменить")])
                await update.message.reply_text(
                    "Выберите группу мышц:",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return

            elif text == "❌ Отменить":
                user_data["current_workout"] = None
                await update.message.reply_text("Тренировка отменена.", reply_markup=self.main_menu_keyboard())
                return

            elif text == "🏁 Завершить тренировку":
                if user_data.get("current_workout") and user_data["current_workout"].get("exercises"):
                    workout = user_data["current_workout"]
                    self.db.save_workout(
                        user_id=user_id,
                        username=username,
                        muscle_group=workout["group"],
                        exercises=workout["exercises"]
                    )
                    await update.message.reply_text("✅ Тренировка сохранена!", reply_markup=self.main_menu_keyboard())
                else:
                    await update.message.reply_text("Тренировка не содержит упражнений.", reply_markup=self.main_menu_keyboard())
                user_data["current_workout"] = None
                return

            elif text == "📜 История тренировок":
                await self.show_workout_history(update, user_id)
                return

            elif text == "📊 Статистика прогресса":
                stats = self.db.get_exercise_stats(user_id, "%")  # Символ % для проверки наличия любых упражнений
                if not stats:
                    await update.message.reply_text("Нет данных для отображения статистики.", reply_markup=self.main_menu_keyboard())
                    return

                user_data["mode"] = "stats_choose_exercise"
                exercises = {ex[0] for ex in self.db.get_user_history(user_id, 1000)}
                keyboard = [[KeyboardButton(ex)] for ex in exercises]
                keyboard.append([KeyboardButton("⬅️ Назад")])
                await update.message.reply_text(
                    "Выберите упражнение для анализа:",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                return

            elif text == "⬅️ Назад":
                user_data["mode"] = None
                await update.message.reply_text("Возврат в главное меню.", reply_markup=self.main_menu_keyboard())
                return

            # Обработка выбора упражнения для статистики
            if user_data.get("mode") == "stats_choose_exercise":
                await self.show_exercise_stats(update, user_id, text)
                return

            # Обработка выбора группы мышц
            muscle_group = next((key for key, val in self.MUSCLE_GROUPS.items() if val == text), None)
            if muscle_group:
                exercises = self.DEFAULT_EXERCISES[muscle_group]
                keyboard = [[KeyboardButton(ex)] for ex in exercises]
                keyboard.append([KeyboardButton("➕ Добавить своё упражнение")])
                keyboard.append([KeyboardButton("🏁 Завершить тренировку")])
                keyboard.append([KeyboardButton("❌ Отменить")])

                if user_data["current_workout"] is None:
                    user_data["current_workout"] = {
                        "group": self.MUSCLE_GROUPS[muscle_group],
                        "exercises": [],
                        "muscle_key": muscle_group
                    }
                else:
                    user_data["current_workout"]["group"] = self.MUSCLE_GROUPS[muscle_group]
                    user_data["current_workout"]["muscle_key"] = muscle_group

                await update.message.reply_text(
                    f"Выберите упражнение на {text}:",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                return

            # Добавление своего упражнения
            if text == "➕ Добавить своё упражнение":
                await update.message.reply_text("Введите название упражнения:")
                return

            # Обработка ввода данных упражнения
            if user_data.get("current_workout"):
                if await self.handle_new_exercise(update, user_data, text):
                    return

                # Обработка стандартных упражнений
                if "muscle_key" in user_data["current_workout"]:
                    muscle_key = user_data["current_workout"]["muscle_key"]
                    if text in self.DEFAULT_EXERCISES[muscle_key]:
                        user_data["current_workout"]["new_exercise"] = text
                        await update.message.reply_text(f"Вы выбрали: {text}\nВведите количество подходов:")
                        return

            await update.message.reply_text("Неизвестная команда. Используйте кнопки меню.")

        except Exception as e:
            logging.error(f"Error in handle_message: {e}")
            await update.message.reply_text("⚠️ Произошла ошибка. Пожалуйста, попробуйте снова.")

    def run(self):
        """Запуск бота"""
        application = ApplicationBuilder().token(self.token).build()
        
        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logging.info("Бот запущен...")
        application.run_polling()

    def __del__(self):
        """Завершение работы с закрытием соединения с БД"""
        if hasattr(self, 'db'):
            self.db.close()


if __name__ == '__main__':
    bot = WorkoutBot(token='7758120985:AAHOid2LvrvC2-u4kZdhnifQTLMcybn_e0o')
    bot.run()
