# Project-Training-Bot
# **Workout Tracker Telegram Bot**  
**Бот для учета тренировок с аналитикой прогресса**  

📌 **О проекте**  
Telegram-бот для спортсменов, который:  
✅ Записывает упражнения (подходы/повторения/вес)  
📊 Строит графики прогресса  
📅 Хранит историю тренировок  

**Поддерживаемые группы мышц**:  
- Спина, грудь, ноги, руки, плечи, пресс  

---

## 🚀 **Быстрый старт**  

**Установка**  
1. Клонируйте репозиторий:  
   ```bash
   git clone https://github.com/yourusername/workout-bot.git
   cd workout-bot
   ```

2. Настройте бота:  
   - Получите токен у [@BotFather](https://t.me/BotFather)  
   - Создайте файл `.env`:  
     ```ini
     TOKEN=ваш_токен
     DB_NAME=workouts.db
     ```

3. Запустите:  
   ```bash
   python main.py
   ```

---

## 🛠 **Технологии**  
- **Backend**: Python 3.10+  
- **Библиотеки**:  
  - `python-telegram-bot` - взаимодействие с Telegram API  
  - `SQLite3` - хранение данных  
  - `matplotlib` - визуализация статистики  
- **Архитектура**: ООП + модульный дизайн  

---

## 📋 **Команды**  
| Команда | Описание |  
|---------|----------|  
| `/start` | Запуск бота |  
| `🏋️‍♂️ Начать тренировку` | Запись новой тренировки |  
| `📜 История` | Последние 100 тренировок |  
| `📊 Статистика` | Графики прогресса по упражнениям |  

---

## 🗃 **Структура базы данных**  
```sql
CREATE TABLE workouts (
    workout_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    muscle_group TEXT,
    date TIMESTAMP
);

CREATE TABLE exercises (
    exercise_id INTEGER PRIMARY KEY,
    workout_id INTEGER,
    name TEXT,
    sets INTEGER,
    reps INTEGER,
    weight REAL
);
```

---

## 📸 **Скриншоты**  
| Главное меню | Статистика |  
|--------------|------------|  
| ![Меню](https://via.placeholder.com/300?text=Main+Menu) | ![График](https://via.placeholder.com/300?text=Stats) |  

---

## 📈 **Пример использования**  
1. Выберите `🏋️‍♂️ Начать тренировку` → `Спина`  
2. Добавьте упражнение:  
   - Название: `Подтягивания`  
   - Подходы: `3`  
   - Повторения: `10`  
3. Через неделю просмотрите прогресс в `📊 Статистика`  

---

## 🤝 **Развитие проекта**  
Планируется:  
- [ ] Поддержка PostgreSQL  
- [ ] Экспорт в Excel  
- [ ] Напоминания о тренировках  



❓ **Поддержка**  
По вопросам и предложениям:  
✉ [Ваш Telegram](https://t.me/yourusername)  
🐞 [Сообщить о баге](https://github.com/yourusername/workout-bot/issues)  

---

<div align="center">
  <sub>Создано с ❤️ для спортивных достижений!</sub>
</div>
