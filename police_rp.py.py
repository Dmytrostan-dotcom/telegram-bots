import asyncio
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = "8795104547:AAHyQ-GuuV4AfWuKDbkKry4maKDJTp4AKgg"

# Твой Telegram ID — владелец системы
OWNER_ID = 7913251778

DB_NAME = "police_rp.db"

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# =========================================================
# БАЗА ДАННЫХ
# =========================================================

db = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS citizens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rp_name TEXT NOT NULL,
    username TEXT,
    birth_date TEXT,
    phone TEXT,
    address TEXT,
    nationality TEXT,
    photo_id TEXT,
    wanted TEXT DEFAULT 'НЕТ',
    notes TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS relatives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    citizen_id INTEGER,
    relation TEXT,
    rp_name TEXT,
    birth_date TEXT,
    phone TEXT,
    photo_id TEXT,
    FOREIGN KEY(citizen_id) REFERENCES citizens(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    citizen_id INTEGER,
    model TEXT,
    plate TEXT,
    color TEXT,
    FOREIGN KEY(citizen_id) REFERENCES citizens(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    citizen_id INTEGER,
    article TEXT,
    date TEXT,
    punishment TEXT,
    FOREIGN KEY(citizen_id) REFERENCES citizens(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    action TEXT,
    target TEXT,
    created_at TEXT
)
""")

db.commit()


# =========================================================
# СОСТОЯНИЯ
# =========================================================

class AddCitizen(StatesGroup):
    name = State()
    username = State()
    birth = State()
    phone = State()
    address = State()
    nationality = State()
    photo = State()
    notes = State()


class SearchCitizen(StatesGroup):
    query = State()


class AddRelative(StatesGroup):
    citizen_id = State()
    relation = State()
    name = State()
    birth = State()
    phone = State()
    photo = State()


# =========================================================
# ДОСТУП
# =========================================================

def has_access(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True

    cursor.execute(
        "SELECT telegram_id FROM users WHERE telegram_id = ?",
        (user_id,)
    )

    return cursor.fetchone() is not None


def log_action(user_id: int, action: str, target: str = ""):
    cursor.execute(
        """
        INSERT INTO logs (telegram_id, action, target, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            action,
            target,
            datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        )
    )
    db.commit()


# =========================================================
# КЛАВИАТУРЫ
# =========================================================

def main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔎 Поиск",
                    callback_data="search"
                ),
                InlineKeyboardButton(
                    text="➕ Добавить",
                    callback_data="add"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👨‍👩‍👧 Семья",
                    callback_data="family"
                ),
                InlineKeyboardButton(
                    text="🚗 Транспорт",
                    callback_data="vehicle"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚠️ Нарушения",
                    callback_data="violation"
                ),
                InlineKeyboardButton(
                    text="🚨 Розыск",
                    callback_data="wanted"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📜 Журнал",
                    callback_data="logs"
                )
            ]
        ]
    )


def citizen_keyboard(citizen_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👨‍👩‍👧 Родственники",
                    callback_data=f"family:{citizen_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚗 Транспорт",
                    callback_data=f"cars:{citizen_id}"
                ),
                InlineKeyboardButton(
                    text="⚠️ Нарушения",
                    callback_data=f"violations:{citizen_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚨 Розыск",
                    callback_data=f"wanted:{citizen_id}"
                )
            ]
        ]
    )


# =========================================================
# START
# =========================================================

@dp.message(Command("start"))
async def start(message: types.Message):
    if not has_access(message.from_user.id):
        await message.answer(
            "⛔ <b>Доступ запрещён.</b>\n\n"
            "Обратитесь к администратору системы.",
            parse_mode="HTML"
        )
        return

    log_action(message.from_user.id, "Открыл главное меню")

    await message.answer(
        "👮 <b>ПОЛИЦЕЙСКАЯ ИНФОРМАЦИОННАЯ СИСТЕМА</b>\n\n"
        "Выберите необходимый раздел:",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# =========================================================
# ВЫДАЧА ДОСТУПА
# =========================================================

@dp.message(Command("grant"))
async def grant_access(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "❌ Использование:\n"
            "<code>/grant 123456789</code>",
            parse_mode="HTML"
        )
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
        return

    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
        (user_id,)
    )
    db.commit()

    await message.answer(
        f"✅ Доступ выдан.\n"
        f"👤 ID: <code>{user_id}</code>\n"
        f"🔓 Уровень: <b>ПОЛНЫЙ ДОСТУП</b>",
        parse_mode="HTML"
    )


@dp.message(Command("revoke"))
async def revoke_access(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "❌ Использование:\n"
            "<code>/revoke 123456789</code>",
            parse_mode="HTML"
        )
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
        return

    cursor.execute(
        "DELETE FROM users WHERE telegram_id = ?",
        (user_id,)
    )
    db.commit()

    await message.answer(
        f"✅ Доступ забран.\n"
        f"👤 ID: <code>{user_id}</code>",
        parse_mode="HTML"
    )


# =========================================================
# ДОБАВЛЕНИЕ ГРАЖДАНИНА
# =========================================================

@dp.callback_query(F.data == "add")
async def add_citizen_start(callback: types.CallbackQuery, state: FSMContext):
    if not has_access(callback.from_user.id):
        return

    await state.set_state(AddCitizen.name)

    await callback.message.answer(
        "➕ <b>НОВОЕ ДОСЬЕ</b>\n\n"
        "Введите ФИО персонажа:",
        parse_mode="HTML"
    )

    await callback.answer()


@dp.message(AddCitizen.name)
async def add_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddCitizen.username)

    await message.answer("Введите username персонажа или напишите <code>нет</code>:")


@dp.message(AddCitizen.username)
async def add_username(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text)
    await state.set_state(AddCitizen.birth)

    await message.answer("Введите дату рождения:")


@dp.message(AddCitizen.birth)
async def add_birth(message: types.Message, state: FSMContext):
    await state.update_data(birth=message.text)
    await state.set_state(AddCitizen.phone)

    await message.answer("Введите телефон персонажа:")


@dp.message(AddCitizen.phone)
async def add_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(AddCitizen.address)

    await message.answer("Введите место регистрации:")


@dp.message(AddCitizen.address)
async def add_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(AddCitizen.nationality)

    await message.answer("Введите гражданство:")


@dp.message(AddCitizen.nationality)
async def add_nationality(message: types.Message, state: FSMContext):
    await state.update_data(nationality=message.text)
    await state.set_state(AddCitizen.photo)

    await message.answer(
        "📸 Отправьте фотографию персонажа."
    )


@dp.message(AddCitizen.photo, F.photo)
async def add_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id

    await state.update_data(photo=photo_id)
    await state.set_state(AddCitizen.notes)

    await message.answer(
        "📝 Введите примечания.\n"
        "Если нет — напишите <code>нет</code>:"
    )


@dp.message(AddCitizen.notes)
async def add_notes(message: types.Message, state: FSMContext):
    data = await state.get_data()

    cursor.execute(
        """
        INSERT INTO citizens
        (rp_name, username, birth_date, phone, address,
         nationality, photo_id, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["name"],
            data["username"],
            data["birth"],
            data["phone"],
            data["address"],
            data["nationality"],
            data["photo"],
            message.text
        )
    )

    db.commit()

    citizen_id = cursor.lastrowid

    log_action(
        message.from_user.id,
        "Создал досье",
        str(citizen_id)
    )

    await state.clear()

    await message.answer(
        f"✅ <b>ДОСЬЕ СОЗДАНО</b>\n\n"
        f"🆔 ID записи: <code>{citizen_id}</code>",
        parse_mode="HTML"
    )


# =========================================================
# ПОИСК
# =========================================================

@dp.callback_query(F.data == "search")
async def search_start(callback: types.CallbackQuery, state: FSMContext):
    if not has_access(callback.from_user.id):
        return

    await state.set_state(SearchCitizen.query)

    await callback.message.answer(
        "🔎 <b>ПОИСК ГРАЖДАНИНА</b>\n\n"
        "Введите ФИО, ID или username:",
        parse_mode="HTML"
    )

    await callback.answer()


@dp.message(SearchCitizen.query)
async def search_result(message: types.Message, state: FSMContext):
    query = message.text.strip()

    cursor.execute(
        """
        SELECT id, rp_name, username, birth_date, phone,
               address, nationality, photo_id, wanted, notes
        FROM citizens
        WHERE rp_name LIKE ?
           OR username LIKE ?
           OR CAST(id AS TEXT) = ?
        LIMIT 10
        """,
        (
            f"%{query}%",
            f"%{query}%",
            query
        )
    )

    rows = cursor.fetchall()
    await state.clear()

    if not rows:
        await message.answer("❌ Ничего не найдено.")
        return

    for row in rows:
        (
            citizen_id,
            name,
            username,
            birth,
            phone,
            address,
            nationality,
            photo_id,
            wanted,
            notes
        ) = row

        text = (
            f"👤 <b>{name}</b>\n\n"
            f"🆔 ID записи: <code>{citizen_id}</code>\n"
            f"🎂 Дата рождения: {birth}\n"
            f"👤 Username: {username}\n"
            f"📱 Телефон: {phone}\n"
            f"🏠 Регистрация: {address}\n"
            f"🌍 Гражданство: {nationality}\n"
            f"🚨 Розыск: {wanted}\n"
            f"📝 Примечание: {notes}"
        )

        log_action(
            message.from_user.id,
            "Поиск гражданина",
            str(citizen_id)
        )

        if photo_id:
            await message.answer_photo(
                photo=photo_id,
                caption=text,
                parse_mode="HTML",
                reply_markup=citizen_keyboard(citizen_id)
            )
        else:
            await message.answer(
                text,
                parse_mode="HTML",
                reply_markup=citizen_keyboard(citizen_id)
            )


# =========================================================
# СЕМЬЯ
# =========================================================

@dp.callback_query(F.data.startswith("family:"))
async def family_view(callback: types.CallbackQuery):
    if not has_access(callback.from_user.id):
        return

    citizen_id = int(callback.data.split(":")[1])

    cursor.execute(
        """
        SELECT relation, rp_name, birth_date, phone, photo_id
        FROM relatives
        WHERE citizen_id = ?
        """,
        (citizen_id,)
    )

    rows = cursor.fetchall()

    if not rows:
        await callback.message.answer(
            "👨‍👩‍👧 <b>Семья не указана.</b>",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    for relation, name, birth, phone, photo in rows:

        text = (
            f"👤 <b>{name}</b>\n\n"
            f"🔗 Родство: {relation}\n"
            f"🎂 Дата рождения: {birth}\n"
            f"📱 Телефон: {phone}"
        )

        if photo:
            await callback.message.answer_photo(
                photo=photo,
                caption=text,
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                text,
                parse_mode="HTML"
            )

    await callback.answer()


# =========================================================
# ТРАНСПОРТ
# =========================================================

@dp.callback_query(F.data.startswith("cars:"))
async def cars_view(callback: types.CallbackQuery):
    if not has_access(callback.from_user.id):
        return

    citizen_id = int(callback.data.split(":")[1])

    cursor.execute(
        """
        SELECT model, plate, color
        FROM vehicles
        WHERE citizen_id = ?
        """,
        (citizen_id,)
    )

    rows = cursor.fetchall()

    if not rows:
        await callback.message.answer(
            "🚗 Транспорт не найден."
        )
        await callback.answer()
        return

    text = "🚗 <b>ТРАНСПОРТ</b>\n\n"

    for model, plate, color in rows:
        text += (
            f"🚘 {model}\n"
            f"🔢 Номер: {plate}\n"
            f"🎨 Цвет: {color}\n\n"
        )

    await callback.message.answer(
        text,
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# НАРУШЕНИЯ
# =========================================================

@dp.callback_query(F.data.startswith("violations:"))
async def violations_view(callback: types.CallbackQuery):
    if not has_access(callback.from_user.id):
        return

    citizen_id = int(callback.data.split(":")[1])

    cursor.execute(
        """
        SELECT article, date, punishment
        FROM violations
        WHERE citizen_id = ?
        """,
        (citizen_id,)
    )

    rows = cursor.fetchall()

    if not rows:
        await callback.message.answer(
            "⚠️ Нарушений не найдено."
        )
        await callback.answer()
        return

    text = "⚠️ <b>НАРУШЕНИЯ</b>\n\n"

    for article, date, punishment in rows:
        text += (
            f"📌 Статья: {article}\n"
            f"📅 Дата: {date}\n"
            f"⚖️ Наказание: {punishment}\n\n"
        )

    await callback.message.answer(
        text,
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# РОЗЫСК
# =========================================================

@dp.callback_query(F.data.startswith("wanted:"))
async def wanted_view(callback: types.CallbackQuery):
    if not has_access(callback.from_user.id):
        return

    citizen_id = int(callback.data.split(":")[1])

    cursor.execute(
        "SELECT rp_name, wanted FROM citizens WHERE id = ?",
        (citizen_id,)
    )

    row = cursor.fetchone()

    if not row:
        await callback.answer("Не найдено.")
        return

    name, wanted = row

    await callback.message.answer(
        f"🚨 <b>РОЗЫСК</b>\n\n"
        f"👤 {name}\n"
        f"📌 Статус: <b>{wanted}</b>",
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ЖУРНАЛ
# =========================================================

@dp.callback_query(F.data == "logs")
async def logs_view(callback: types.CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("⛔ Только для владельца.")
        return

    cursor.execute(
        """
        SELECT telegram_id, action, target, created_at
        FROM logs
        ORDER BY id DESC
        LIMIT 20
        """
    )

    rows = cursor.fetchall()

    if not rows:
        await callback.message.answer(
            "📜 Журнал пока пуст."
        )
        await callback.answer()
        return

    text = "📜 <b>ПОСЛЕДНИЕ ДЕЙСТВИЯ</b>\n\n"

    for telegram_id, action, target, created_at in rows:
        text += (
            f"👮 <code>{telegram_id}</code>\n"
            f"📌 {action}\n"
            f"🎯 {target}\n"
            f"🕒 {created_at}\n\n"
        )

    await callback.message.answer(
        text,
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# НЕИСПОЛЬЗОВАННЫЕ КНОПКИ
# =========================================================

@dp.callback_query(F.data == "family")
async def family_button(callback: types.CallbackQuery):
    await callback.message.answer(
        "👨‍👩‍👧 Откройте досье гражданина и нажмите "
        "кнопку «Родственники»."
    )
    await callback.answer()


@dp.callback_query(F.data == "vehicle")
async def vehicle_button(callback: types.CallbackQuery):
    await callback.message.answer(
        "🚗 Откройте досье гражданина для просмотра транспорта."
    )
    await callback.answer()


@dp.callback_query(F.data == "violation")
async def violation_button(callback: types.CallbackQuery):
    await callback.message.answer(
        "⚠️ Откройте досье гражданина для просмотра нарушений."
    )
    await callback.answer()


@dp.callback_query(F.data == "wanted")
async def wanted_button(callback: types.CallbackQuery):
    await callback.message.answer(
        "🚨 Откройте досье гражданина для проверки розыска."
    )
    await callback.answer()


# =========================================================
# ЗАПУСК
# =========================================================

async def main():
    print("👮 Полицейская RP-система запускается...")
    print("✅ Система готова.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())