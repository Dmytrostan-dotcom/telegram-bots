import asyncio
import json
import os
from html import escape

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter


# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8863305349:AAFEqQpgs3R9zokAtDWx9L9psljCk6bmoc8")

ADMINS = {
    8326482234,
    7217920772,
}

LOG_CHANNEL_ID = -1003913090510

USERS_FILE = "users.json"
BANNED_FILE = "banned.json"


# =========================================================
# БОТ
# =========================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# =========================================================
# ФАЙЛЫ
# =========================================================

def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


users = load_json(USERS_FILE, [])
users = [int(x) for x in users]

banned_users = load_json(BANNED_FILE, {})
banned_users = {int(k): v for k, v in banned_users.items()}


# =========================================================
# ПРОВЕРКА АДМИНА
# =========================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


# =========================================================
# ДОБАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
# =========================================================

def add_user(user_id: int):
    if user_id not in users:
        users.append(user_id)
        save_json(USERS_FILE, users)


# =========================================================
# ЛОГИ
# =========================================================

async def send_log(text: str):
    try:
        await bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка логов: {e}")


# =========================================================
# ПРОВЕРКА БАНА
# =========================================================

async def check_ban(message: types.Message) -> bool:
    user_id = message.from_user.id

    if user_id in banned_users:
        await message.answer(
            "⛔ <b>Вы заблокированы.</b>\n\n"
            "Использование бота для вашего аккаунта запрещено.",
            parse_mode="HTML"
        )
        return True

    return False


# =========================================================
# СОСТОЯНИЯ ДЛЯ /B
# =========================================================

class BroadcastState(StatesGroup):
    waiting_text = State()
    waiting_chat_id = State()


# =========================================================
# СОСТОЯНИЯ ДЛЯ /ALL
# =========================================================

class AllState(StatesGroup):
    waiting_text = State()
    waiting_confirm = State()


# =========================================================
# /START — ДОСТУПЕН ВСЕМ
# =========================================================

@dp.message(Command("start"))
async def start_command(message: types.Message):

    if await check_ban(message):
        return

    add_user(message.from_user.id)

    username = (
        f"@{escape(message.from_user.username)}"
        if message.from_user.username
        else "нет"
    )

    await send_log(
        "🟢 <b>ПОЛЬЗОВАТЕЛЬ ЗАПУСТИЛ БОТА</b>\n\n"
        f"👤 Имя: {escape(message.from_user.full_name)}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>"
    )

    await message.answer(
        "🤖 <b>Что умеет этот бот?</b>\n\n"
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Бот поможет отправить сообщение в нужную группу.\n\n"
        "<b>1.</b> Добавьте бота в группу.\n"
        "<b>2.</b> Введите /b.\n"
        "<b>3.</b> Напишите сообщение.\n"
        "<b>4.</b> Укажите ID группы.\n\n"
        "📌 Узнать ID можно через @userinfobot.\n\n"
        "⚠️ Бот должен иметь право отправлять "
        "сообщения в группе.",
        parse_mode="HTML"
    )


# =========================================================
# /HELP
# =========================================================

@dp.message(Command("help"))
async def help_command(message: types.Message):

    if await check_ban(message):
        return

    add_user(message.from_user.id)

    text = (
        "🤖 <b>Помощь</b>\n\n"
        "/start — информация о боте\n"
        "/b — отправить сообщение в группу или канал\n"
    )

    if is_admin(message.from_user.id):
        text += (
            "\n<b>Администратор:</b>\n"
            "/all — рассылка всем пользователям\n"
            "/ban — заблокировать пользователя\n"
            "/unban — разблокировать пользователя\n"
            "/banlist — список заблокированных\n"
        )

    await message.answer(text, parse_mode="HTML")


# =========================================================
# /B — ДОСТУПЕН ВСЕМ
# =========================================================

@dp.message(Command("b"))
async def b_command(
    message: types.Message,
    state: FSMContext
):

    if await check_ban(message):
        return

    add_user(message.from_user.id)

    await state.set_state(BroadcastState.waiting_text)

    await message.answer(
        "📢 <b>ОТПРАВКА СООБЩЕНИЯ</b>\n\n"
        "📝 Отправьте текст, который нужно отправить "
        "в группу или канал.",
        parse_mode="HTML"
    )


# =========================================================
# ПОЛУЧЕНИЕ ТЕКСТА /B
# =========================================================

@dp.message(BroadcastState.waiting_text)
async def b_get_text(
    message: types.Message,
    state: FSMContext
):

    if await check_ban(message):
        await state.clear()
        return

    if not message.text:
        await message.answer(
            "❌ Отправьте текстовое сообщение."
        )
        return

    await state.update_data(text=message.text)
    await state.set_state(BroadcastState.waiting_chat_id)

    await message.answer(
        "🎯 <b>КУДА ОТПРАВИТЬ?</b>\n\n"
        "Отправьте ID группы или канала.\n\n"
        "Например:\n"
        "<code>-1003941822063</code>",
        parse_mode="HTML"
    )


# =========================================================
# ОТПРАВКА /B
# =========================================================

@dp.message(BroadcastState.waiting_chat_id)
async def b_send(
    message: types.Message,
    state: FSMContext
):

    if await check_ban(message):
        await state.clear()
        return

    data = await state.get_data()
    text = data["text"]

    try:
        chat_id = int(message.text)

        await bot.send_message(
            chat_id=chat_id,
            text=text
        )

        await message.answer(
            "✅ <b>СООБЩЕНИЕ ОТПРАВЛЕНО!</b>\n\n"
            f"🎯 ID чата: <code>{chat_id}</code>",
            parse_mode="HTML"
        )

        await send_log(
            "📤 <b>КОМАНДА /B</b>\n\n"
            f"👤 Пользователь: <code>{message.from_user.id}</code>\n"
            f"🎯 Чат: <code>{chat_id}</code>\n"
            f"📝 Текст:\n{escape(text)}"
        )

    except ValueError:

        await message.answer(
            "❌ ID должен состоять из цифр.\n\n"
            "Например:\n"
            "<code>-1003941822063</code>",
            parse_mode="HTML"
        )
        return

    except Exception as e:

        await message.answer(
            "❌ <b>Не удалось отправить сообщение.</b>\n\n"
            f"<code>{escape(str(e))}</code>",
            parse_mode="HTML"
        )

        await send_log(
            "❌ <b>ОШИБКА /B</b>\n\n"
            f"👤 Пользователь: <code>{message.from_user.id}</code>\n"
            f"⚠️ Ошибка: <code>{escape(str(e))}</code>"
        )

    await state.clear()


# =========================================================
# /ALL — ТОЛЬКО АДМИНЫ
# =========================================================

@dp.message(Command("all"))
async def all_command(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    await state.set_state(AllState.waiting_text)

    await message.answer(
        "📢 <b>РАССЫЛКА ВСЕМ ПОЛЬЗОВАТЕЛЯМ</b>\n\n"
        "Отправьте текст сообщения.",
        parse_mode="HTML"
    )


# =========================================================
# ТЕКСТ /ALL
# =========================================================

@dp.message(AllState.waiting_text)
async def all_get_text(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if not message.text:
        await message.answer(
            "❌ Отправьте текстовое сообщение."
        )
        return

    await state.update_data(text=message.text)
    await state.set_state(AllState.waiting_confirm)

    await message.answer(
        "⚠️ <b>ПРЕДПРОСМОТР РАССЫЛКИ</b>\n\n"
        f"{escape(message.text)}\n\n"
        "Введите <code>ДА</code> для отправки всем.\n"
        "Введите <code>НЕТ</code> для отмены.",
        parse_mode="HTML"
    )


# =========================================================
# ПОДТВЕРЖДЕНИЕ /ALL
# =========================================================

@dp.message(AllState.waiting_confirm)
async def all_confirm(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        await state.clear()
        return

    answer = message.text.lower().strip()

    if answer == "нет":
        await state.clear()

        await message.answer(
            "❌ <b>Рассылка отменена.</b>",
            parse_mode="HTML"
        )
        return

    if answer != "да":
        await message.answer(
            "Введите <code>ДА</code> или <code>НЕТ</code>.",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    text = data["text"]

    await state.clear()

    sent = 0
    blocked = 0
    errors = 0

    await message.answer(
        "📢 <b>РАССЫЛКА НАЧАЛАСЬ...</b>",
        parse_mode="HTML"
    )

    for user_id in users:

        if user_id in banned_users:
            continue

        try:
            await bot.send_message(
                chat_id=user_id,
                text=text
            )

            sent += 1

            await asyncio.sleep(0.05)

        except TelegramForbiddenError:
            blocked += 1

        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)

            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=text
                )
                sent += 1
            except Exception:
                errors += 1

        except Exception:
            errors += 1

    await message.answer(
        "✅ <b>РАССЫЛКА ЗАВЕРШЕНА</b>\n\n"
        f"👥 Всего пользователей: <b>{len(users)}</b>\n"
        f"📨 Отправлено: <b>{sent}</b>\n"
        f"🚫 Недоступно: <b>{blocked}</b>\n"
        f"⚠️ Ошибок: <b>{errors}</b>",
        parse_mode="HTML"
    )

    await send_log(
        "📢 <b>РАССЫЛКА /ALL</b>\n\n"
        f"👮 Администратор: <code>{message.from_user.id}</code>\n"
        f"👥 Пользователей: <code>{len(users)}</code>\n"
        f"📨 Отправлено: <code>{sent}</code>\n"
        f"🚫 Недоступно: <code>{blocked}</code>\n"
        f"⚠️ Ошибок: <code>{errors}</code>\n\n"
        f"📝 Текст:\n{escape(text)}"
    )


# =========================================================
# /BAN — ТОЛЬКО АДМИН
# =========================================================

@dp.message(Command("ban"))
async def ban_command(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    target_id = None
    reason = "Без причины"

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id

        args = message.text.split(maxsplit=1)

        if len(args) > 1:
            reason = args[1]

    else:
        args = message.text.split(maxsplit=2)

        if len(args) < 2:
            await message.answer(
                "Использование:\n\n"
                "<code>/ban ID причина</code>\n\n"
                "Или ответьте на сообщение пользователя "
                "командой /ban.",
                parse_mode="HTML"
            )
            return

        try:
            target_id = int(args[1])
        except ValueError:
            await message.answer(
                "❌ ID должен быть числом."
            )
            return

        if len(args) >= 3:
            reason = args[2]

    if target_id in ADMINS:
        await message.answer(
            "❌ Нельзя заблокировать администратора."
        )
        return

    banned_users[target_id] = {
        "reason": reason,
        "admin_id": message.from_user.id
    }

    save_json(BANNED_FILE, banned_users)

    await message.answer(
        "✅ <b>Пользователь заблокирован.</b>\n\n"
        f"🆔 ID: <code>{target_id}</code>\n"
        f"📄 Причина: {escape(reason)}",
        parse_mode="HTML"
    )

    await send_log(
        "🔨 <b>БАН ПОЛЬЗОВАТЕЛЯ</b>\n\n"
        f"👮 Администратор: <code>{message.from_user.id}</code>\n"
        f"👤 Пользователь: <code>{target_id}</code>\n"
        f"📄 Причина: {escape(reason)}"
    )


# =========================================================
# /UNBAN — ТОЛЬКО АДМИН
# =========================================================

@dp.message(Command("unban"))
async def unban_command(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "Использование:\n"
            "<code>/unban ID</code>",
            parse_mode="HTML"
        )
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer(
            "❌ ID должен быть числом."
        )
        return

    if target_id not in banned_users:
        await message.answer(
            "ℹ️ Пользователь не находится в бане."
        )
        return

    del banned_users[target_id]
    save_json(BANNED_FILE, banned_users)

    await message.answer(
        "✅ <b>Пользователь разблокирован.</b>\n\n"
        f"🆔 ID: <code>{target_id}</code>",
        parse_mode="HTML"
    )

    await send_log(
        "🔓 <b>РАЗБАН ПОЛЬЗОВАТЕЛЯ</b>\n\n"
        f"👮 Администратор: <code>{message.from_user.id}</code>\n"
        f"👤 Пользователь: <code>{target_id}</code>"
    )


# =========================================================
# /BANLIST — ТОЛЬКО АДМИН
# =========================================================

@dp.message(Command("banlist"))
async def banlist_command(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    if not banned_users:
        await message.answer(
            "✅ Заблокированных пользователей нет."
        )
        return

    text = "🔨 <b>ЗАБЛОКИРОВАННЫЕ ПОЛЬЗОВАТЕЛИ</b>\n\n"

    for user_id, info in banned_users.items():
        reason = info.get("reason", "Без причины")

        text += (
            f"👤 <code>{user_id}</code>\n"
            f"📄 {escape(reason)}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# ОБЫЧНЫЕ СООБЩЕНИЯ
# =========================================================

@dp.message()
async def other_messages(message: types.Message):

    if await check_ban(message):
        return

    add_user(message.from_user.id)

    await message.answer(
        "📩 Сообщение получено.\n\n"
        "Используйте /start для информации о боте."
    )


# =========================================================
# ЗАПУСК
# =========================================================

async def main():

    print("🚀 Бот запускается...")

    await send_log(
        "🚀 <b>БОТ ЗАПУЩЕН</b>\n\n"
        "✅ Бот успешно запущен.\n"
        f"👮 Администраторов: {len(ADMINS)}\n"
        f"👥 Пользователей в базе: {len(users)}"
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
