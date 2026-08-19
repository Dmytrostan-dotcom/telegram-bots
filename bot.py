import asyncio
import json
import os
import time
import json
import os

USERS_FILE = "users.json"

from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.filters import Command
from aiogram.types import ChatPermissions
from aiogram.filters import StateFilter
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

class BroadcastState(StatesGroup):
    waiting_chat = State()
    waiting_message = State()
    confirm = State()

SPAM = {}

BOT_ACTIVE = True
TOKEN = "8640513137:AAGFFVZovHuFalA8nZP6ZishLqFo9vM9rhg"

GROUP_ID = -1003941822063  # Одессские


ADMIN_LOG_CHANNEL = -1004457255370
ACTION_LOG_CHANNEL = -1004382083796
ADMINS_FILE = "admins.json"
STATS_FILE = "stats.json"


def load_admins():

    if not os.path.exists(ADMINS_FILE):
        return [
            7217920772
        ]

    with open(ADMINS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)




def save_admins():

    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(ADMINS, f, indent=4)


def load_stats():

    if not os.path.exists(STATS_FILE):
        return {
            "joins": 0,
            "reports": 0,
            "kicks": 0
        }

    with open(STATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_stats():

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(STATS, f, indent=4)


ADMINS = load_admins()

ADMIN_ACTIVITY = {}

def update_activity(user_id):
    ADMIN_ACTIVITY[user_id] = datetime.now()

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==========================
# УНИВЕРСАЛЬНЫЕ ЛОГИ 
# ==========================

async def full_log(text: str):
    try:
        time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        await bot.send_message(
            ACTION_LOG_CHANNEL,
            f"🕒 {time}\n\n{text}",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Ошибка логов: {e}")





STATS = load_stats()


daily_reports = 0
daily_broadcasts = 0
daily_joins = 0


reported_messages = set()
report_cooldown = {}


# ==========================
# СОСТОЯНИЯ
# ==========================


class DeleteAdminState(StatesGroup):
    waiting_stats = State()
    waiting_reason = State()

class AddAdminState(StatesGroup):
    waiting_name = State()
    waiting_position = State()

class MuteState(StatesGroup):
    waiting_user = State()
    waiting_gender = State()
    waiting_time = State()
    waiting_warns = State()
    waiting_mutes = State()
    waiting_reason = State()
    confirm = State()

# ==========================
# ПРОВЕРКИ
# ==========================

async def is_admin(user_id):

    return user_id in ADMINS



async def is_in_group(user_id):
    try:
        member = await bot.get_chat_member(GROUP_ID, user_id)

        return member.status not in ("left", "kicked")

    except:
        return False


async def admin_check(message):

    if not await is_admin(message.from_user.id):

        await message.answer(
            "⛔ Доступ запрещено!\n\n"
            "У вас нет прав для выполнения этой команды.\n"
            "Эта команда доступна только администраторам бота."
        )

        return False


    update_activity(message.from_user.id)


    if not await is_in_group(message.from_user.id):

        await message.answer(
            "ℹ️ Эта группа не находится под модерацией системы."
        )

        return False


    return True


async def bot_active_check(message):

    if BOT_ACTIVE:
        return True

    if message.from_user.id in ADMINS:
        return True

    await message.answer(
        "🔴 Бот временно отключен администрацией."
    )

    return False

# ==========================
# ЗАПУСК БОТА
# ==========================


@dp.message(Command("start"))
async def start_command(message: Message):

    if not await is_in_group(message.from_user.id):

        await message.answer(
            "ℹ️ Эта группа не находится под модерацией системы."
        )

        return


    await message.answer(
    "👋 <b>Добро пожаловать в официальный бот сообщества «Одесские»!</b>\n\n"
    "🏙️ Здесь вы найдёте всё необходимое для комфортного общения.\n"
    "⚡ Используйте команды бота для быстрого доступа к функциям.\n\n"
    "📖 <b>Список всех команд:</b> /help\n\n"
    "💙 Желаем приятного общения и хорошего настроения!"
)


# ==========================
# PING
# ==========================

@dp.message(Command("ping"))
async def ping(message: Message):

    start_time = datetime.now()

    msg = await message.answer("🏓 Проверяю систему...")

    end_time = datetime.now()

    latency = (end_time - start_time).total_seconds() * 1000

    status = "🟢 Онлайн" if BOT_ACTIVE else "🔴 Выключен"

    await msg.edit_text(
        f"🏓 <b>Статус системы</b>\n\n"
        f"⚡ Задержка: <b>{latency:.0f} мс</b>\n"
        f"🤖 Бот: <b>{status}</b>\n"
        f"🕒 Время проверки: <b>{datetime.now().strftime('%H:%M:%S')}</b>",
        parse_mode="HTML"
    )

    await asyncio.sleep(60)

    try:
        await message.delete()
    except:
        pass

    try:
        await msg.delete()
    except:
        pass



# ==========================
# BOT ONLINE
# ==========================

async def bot_online_message():

    try:

        msg = await bot.send_message(
            ACTION_LOG_CHANNEL,
            "🟢 <b>Бот снова работает</b>\n\n"
            "Система успешно восстановила работу.",
            parse_mode="HTML"
        )


        await asyncio.sleep(60)


        try:
            await msg.delete()

        except:
            pass


    except:

        pass

# ==========================
# REPORT / ЖАЛОБЫ
# ==========================

@dp.message(Command("report"))
async def report_user(message: Message):

    global daily_reports

    if not message.reply_to_message:
        await message.answer(
            "❌ Используйте /report ответом на сообщение."
        )
        return

    report_key = (
        message.chat.id,
        message.reply_to_message.message_id
    )

    if report_key in reported_messages:
        await message.answer(
            "⚠️ На это сообщение уже была отправлена жалоба."
        )
        return

    reported_messages.add(report_key)

    if message.from_user.id in report_cooldown:
        await message.answer(
            "⏳ Подождите перед повторной жалобой."
        )
        return

    report_cooldown[message.from_user.id] = True
    daily_reports += 1
    STATS["reports"] += 1
    save_stats()

    msg = message.reply_to_message

    if msg is None:
        await message.answer(
            "❌ Пожалуйста, ответьте на сообщение, которое хотите отправить в жалобе."
        )
        return

    link = (
        f"https://t.me/c/"
        f"{str(GROUP_ID).replace('-100', '')}/"
        f"{msg.message_id}"
    )

    text = (
        "🚨 <b>Новая жалоба</b>\n\n"
        f"👤 <b>Отправитель:</b> {message.from_user.full_name}\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"📅 <b>Дата:</b> {message.date.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"📌 <b>На сообщение пользователя:</b>\n"
        f"👤 {msg.from_user.full_name}\n"
        f"🆔 <code>{msg.from_user.id}</code>\n\n"
        f"🔗 <b>Сообщение:</b>\n{link}\n\n"
        "⚠️ <i>Требуется проверка администрации.</i>"
    )

    # Сообщение пользователю
    confirm = await message.answer(
        "✅ Жалоба отправлена администрации.\n"
        "📌 Ожидайте рассмотрения."
    )


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Закрыть",
                    callback_data=(
                        f"close_report:"
                        f"{confirm.message_id}:"
                        f"{message.message_id}:"
                        f"{message.chat.id}"
                    )
                )
            ]
        ]
    )

    sent = False

    for admin in ADMINS:
        try:
            await bot.send_message(
                admin,
                text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            sent = True

        except:
            pass
    if not sent:
        try:
            await confirm.delete()
        except:
            pass

        await message.answer(
            "❌ Администрации сейчас нет в сети."
        )

    async def cooldown_remove():
        await asyncio.sleep(30)

        report_cooldown.pop(
            message.from_user.id,
            None
        )

    asyncio.create_task(cooldown_remove())


@dp.callback_query(lambda c: c.data.startswith("close_report"))
async def close_report(callback: CallbackQuery):

    try:
        _, confirm_id, report_id, chat_id = callback.data.split(":")

        confirm_id = int(confirm_id)
        report_id = int(report_id)
        chat_id = int(chat_id)

        # Удаляем сообщение у админа
        try:
            message = callback.message
            if message is not None:
                await message.delete()  # type: ignore[attr-defined]
        except:
            pass

        # Удаляем подтверждение пользователю
        try:
            await bot.delete_message(chat_id, confirm_id)
        except:
            pass

        # Удаляем команду /report
        try:
            await bot.delete_message(chat_id, report_id)
        except:
            pass

        await callback.answer("Жалоба закрыта")

    except Exception as e:
        print(e)
        await callback.answer(
            "Ошибка закрытия",
            show_alert=True
        )

# ==========================
# ПОЗВАТЬ АДМИНИСТРАЦИЮ
# ==========================


@dp.message(Command("admin"))
async def call_admin(message: Message):


    link = (
        f"https://t.me/c/"
        f"{str(GROUP_ID)[4:]}/"
        f"{message.message_id}"
    )


    online = 0



    for admin in ADMINS:

        try:

            await bot.send_message(
                admin,
                "🚨 <b>Вас вызвали участники группы!</b>\n\n"
                f"👤 Пользователь: {message.from_user.full_name}\n"
                f"🆔 ID: <code>{message.from_user.id}</code>\n\n"
                f"🔗 Ссылка на сообщение:\n{link}",
                parse_mode="HTML"
            )


            online += 1


        except:

            pass



    if online == 0:

        await message.answer(
            "❌ Администрации сейчас нет в сети."
        )

        return



    await message.answer(
        "✅ Администрация уведомлена. Ожидайте ответа."
    )



# ==========================
# РАССЫЛКА
# ==========================

@dp.message(Command("b"))
async def broadcast_start(message: Message, state: FSMContext):

    if not await bot_active_check(message):
        return

    if not await admin_check(message):
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Одесские",
                    callback_data="broadcast_group"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📣 Канал",
                    callback_data="broadcast_channel"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="broadcast_cancel"
                )
            ]
        ]
    )

    await state.set_state(BroadcastState.waiting_chat)

    await message.answer(
        "📌 Выберите, куда отправить рассылку:",
        reply_markup=keyboard
    )

    try:
        await message.delete()
    except:
        pass

  


from aiogram.filters import StateFilter


@dp.callback_query(StateFilter(BroadcastState.waiting_chat))
async def broadcast_choose(callback: CallbackQuery, state: FSMContext):

    if callback.data == "broadcast_group":
        chat_id = GROUP_ID
        chat_name = "Одесские"


    elif callback.data == "broadcast_channel":
        chat_id = ADMIN_LOG_CHANNEL      # сюда потом поставишь ID своего канала
        chat_name = "Канал"

    elif callback.data == "broadcast_cancel":
        await state.clear()

        await callback.message.edit_text(
            "❌ Рассылка отменена."
        )

        await callback.answer()
        return

    else:
        return

    await state.update_data(
        chat_id=chat_id,
        chat_name=chat_name
    )

    await state.set_state(BroadcastState.waiting_message)

    await callback.message.edit_text(
        f"✅ Выбрано: <b>{chat_name}</b>\n\n"
        "📨 Теперь отправьте сообщение для рассылки.",
        parse_mode="HTML"
    )

    await callback.answer()

# ==========================
# ПРЕДПРОСМОТР РАССЫЛКИ
# ==========================

@dp.message(BroadcastState.waiting_message)
async def broadcast_preview(message: Message, state: FSMContext):

    if message.text and message.text.startswith("/"):
        await state.clear()
        await message.answer("❌ Рассылка отменена.")
        return

    await state.update_data(
        preview_message=message.message_id,
        preview_chat=message.chat.id
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Отправить",
                    callback_data="broadcast_send"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить",
                    callback_data="broadcast_edit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="broadcast_cancel"
                )
            ]
        ]
    )

    await state.set_state(BroadcastState.confirm)

    await message.answer(
        "👀 <b>Предпросмотр рассылки</b>\n\n"
        "Проверьте сообщение выше.\n\n"
        "Если всё верно — нажмите «📤 Отправить».",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# ==========================
# КНОПКИ ПОДТВЕРЖДЕНИЯ
# ==========================

@dp.callback_query(StateFilter(BroadcastState.confirm))
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    if callback.data == "broadcast_cancel":

        await state.clear()

        await callback.message.edit_text(
            "❌ Рассылка отменена."
        )

        return

    if callback.data == "broadcast_edit":

        await state.set_state(
            BroadcastState.waiting_message
        )

        await callback.message.edit_text(
            "✏️ Отправьте новое сообщение."
        )

        return

    if callback.data != "broadcast_send":
        return

    try:

        sent = await bot.copy_message(
            chat_id=data["chat_id"],
            from_chat_id=data["preview_chat"],
            message_id=data["preview_message"]
        )

    except Exception as e:

        await callback.message.edit_text(
            f"❌ Ошибка отправки\n\n{e}"
        )

        await state.clear()

        return

    link = (
        f"https://t.me/c/"
        f"{str(data['chat_id'])[4:]}/"
        f"{sent.message_id}"
    )

    await send_log(
        "📢 Новая рассылка\n\n"
        f"👤 {callback.from_user.full_name}\n"
        f"🆔 {callback.from_user.id}\n"
        f"📍 {data['chat_name']}\n"
        f"🔗 {link}"
    )

    await callback.message.edit_text(
        "✅ Рассылка успешно отправлена."
    )

    try:
        await bot.delete_message(
            data["preview_chat"],
            data["preview_message"]
        )
    except:
        pass

    await state.clear()
# ==========================
# НАЗНАЧЕНИЕ АДМИНИСТРАТОРА
# ==========================

@dp.message(Command("add"))
async def add_admin(message: Message, state: FSMContext):

    if not await admin_check(message):
        return

    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "❌ <b>Неверное использование команды</b>\n\n"
            "📌 Формат:\n"
            "<code>/add ID</code>",
            parse_mode="HTML"
        )
        return

    try:
        user_id = int(args[1])

    except:
        await message.answer(
            "❌ <b>Укажите корректный ID пользователя.</b>",
            parse_mode="HTML"
        )
        return

    if user_id in ADMINS:
        await message.answer(
            "⚠️ <b>Этот пользователь уже является администратором.</b>",
            parse_mode="HTML"
        )
        return

    await state.update_data(add_user=user_id)

    await state.set_state(AddAdminState.waiting_name)

    await message.answer(
        "📝 <b>Введите имя и фамилию нового администратора:</b>",
        parse_mode="HTML"
    )


# ==========================
# ИМЯ И ФАМИЛИЯ
# ==========================

@dp.message(AddAdminState.waiting_name)
async def add_admin_name(message: Message, state: FSMContext):

    full_name = message.text.strip()

    await state.update_data(full_name=full_name)

    await state.set_state(AddAdminState.waiting_position)

    await message.answer(
        "📌 <b>Выберите должность:</b>\n\n"
        "1 — Главный смотрящий\n"
        "2 — Заместитель главного смотрящего\n"
        "3 — Администратор",
        parse_mode="HTML"
    )


# ==========================
# ДОЛЖНОСТЬ И НАЗНАЧЕНИЕ
# ==========================

@dp.message(AddAdminState.waiting_position)
async def add_admin_position(message: Message, state: FSMContext):

    positions = {
        "1": "Главного смотрящего",
        "2": "Заместителя главного смотрящего",
        "3": "Администратора"
    }

    if message.text not in positions:
        await message.answer(
            "❌ <b>Введите только 1, 2 или 3.</b>",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()

    user_id = data["add_user"]
    full_name = data["full_name"]

    position = positions[message.text]

    # Добавляем в список администраторов
    ADMINS.append(user_id)
    save_admins()

    # Выдаём права в группе
    try:
        await bot.promote_chat_member(
            GROUP_ID,
            user_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=True,
            can_change_info=True,
            can_pin_messages=True,
            can_post_stories=True,
            can_edit_stories=True,
            can_delete_stories=True,
            is_anonymous=True
        )

    except Exception as e:
        await send_log(
            "❌ <b>Ошибка выдачи прав администратора</b>\n\n"
            f"👤 <b>Пользователь:</b> {full_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"📌 <b>Должность:</b> {position}\n\n"
            f"🛠 <b>Ошибка:</b>\n<code>{e}</code>"
        )
        print(f"Ошибка выдачи прав: {e}")

    # Официальное объявление
    announcement = (
        "❗️ <b>ОФИЦИАЛЬНОЕ ОБЪЯВЛЕНИЕ</b>\n\n"
        f"👤 <b>{full_name}</b> назначен(а) на должность "
        f"<b>{position}</b> группы «Одесские».\n\n"
        "Поздравляем с назначением! Желаем успешной работы, "
        "ответственного выполнения обязанностей, справедливых решений "
        "и дальнейшего карьерного роста."
    )

    # Отправка в канал администрации
    await bot.send_message(
        ADMIN_LOG_CHANNEL,
        announcement,
        parse_mode="HTML"
    )

    # Лог действия
    await send_log(
        f"🛡 Назначение администрации\n"
        f"👤 Новый администратор: {full_name}\n"
        f"🆔 ID: {user_id}\n"
        f"📌 Должность: {position}\n"
        f"👮 Назначил: {message.from_user.full_name}\n"
        f"🆔 ID назначившего: {message.from_user.id}"
    )

    await message.answer(
        "✅ <b>Администратор успешно назначен.</b>",
        parse_mode="HTML"
    )

    await state.clear()

# ==========================
# СОСТОЯНИЯ СНЯТИЯ
# ==========================

class DeleteAdminState(StatesGroup):
    waiting_name = State()
    waiting_position = State()
    waiting_stats = State()
    waiting_reason = State()


# ==========================
# СНЯТИЕ АДМИНИСТРАТОРА
# ==========================

@dp.message(Command("del"))
async def delete_admin(message: Message, state: FSMContext):

    if not await admin_check(message):
        return

    args = message.text.split()

    if len(args) < 2:
        await message.answer("❌ Использование:\n/del ID")
        return

    try:
        user_id = int(args[1])

    except:
        await message.answer("❌ Неверный ID.")
        return

    if user_id not in ADMINS:
        await message.answer(
            "❌ Этот пользователь не является администратором."
        )
        return

    await state.update_data(delete_user=user_id)

    await state.set_state(DeleteAdminState.waiting_name)

    await message.answer(
        "📋 Введите имя и фамилию:"
    )


# ==========================
# ИМЯ И ФАМИЛИЯ
# ==========================

@dp.message(DeleteAdminState.waiting_name)
async def delete_name(message: Message, state: FSMContext):

    await state.update_data(full_name=message.text.strip())

    await state.set_state(DeleteAdminState.waiting_position)

    await message.answer(
        "📌 Выберите должность:\n\n"
        "1 — Администратор\n"
        "2 — Главный смотрящий за чатом «Одесские»\n"
        "3 — Заместитель главного смотрящего за чатом «Одесские»"
    )


# ==========================
# ДОЛЖНОСТЬ
# ==========================

@dp.message(DeleteAdminState.waiting_position)
async def delete_position(message: Message, state: FSMContext):

    positions = {
        "1": "администратора",
        "2": "главного смотрящего за чатом «Одесские»",
        "3": "заместителя главного смотрящего за чатом «Одесские»"
    }

    if message.text not in positions:
        await message.answer("❌ Введите 1, 2 или 3.")
        return

    await state.update_data(position=positions[message.text])

    await state.set_state(DeleteAdminState.waiting_stats)

    await message.answer(
        "📊 Укажите текущую ситуацию.\n\n"
        "Формат:\n"
        "варны муты\n\n"
        "Пример:\n"
        "0 0"
    )


# ==========================
# ВАРНЫ И МУТЫ
# ==========================

@dp.message(DeleteAdminState.waiting_stats)
async def delete_stats(message: Message, state: FSMContext):

    try:
        warns, mutes = map(int, message.text.split())

    except:
        await message.answer(
            "❌ Неверный формат.\n\n"
            "Пример:\n0 0"
        )
        return

    await state.update_data(
        warns=warns,
        mutes=mutes
    )

    await state.set_state(DeleteAdminState.waiting_reason)

    await message.answer(
        "📌 Укажите причину снятия:"
    )


# ==========================
# ПРИЧИНА И СНЯТИЕ
# ==========================

@dp.message(DeleteAdminState.waiting_reason)
async def delete_reason(message: Message, state: FSMContext):

    data = await state.get_data()

    user_id = data["delete_user"]
    full_name = data["full_name"]
    position = data["position"]
    warns = data["warns"]
    mutes = data["mutes"]

    reason = message.text.strip()

    # Удаляем из списка
    if user_id in ADMINS:
        ADMINS.remove(user_id)
        save_admins()

    # Забираем права
    try:
        await bot.promote_chat_member(
            GROUP_ID,
            user_id,

            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_pin_messages=False,
            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,
            is_anonymous=False
        )

    except Exception as e:
        print(e)

    # ОБЪЯВЛЕНИЕ
    text = (
        "📢 <b>ОФИЦИАЛЬНОЕ ОБЪЯВЛЕНИЕ</b>\n\n"
        f"{full_name} снят с должности {position}.\n\n"
        f"Причина: {reason}.\n\n"
        "Текущая ситуация:\n"
        f"⚠️ Варны: {warns}/5\n"
        f"🔇 Муты: {mutes}/3"
    )

    # В канал
    await bot.send_message(
        ADMIN_LOG_CHANNEL,
        text,
        parse_mode="HTML"
    )


       # лог
    await bot.send_message(
    ACTION_LOG_CHANNEL,
    "🛡 <b>Снятие администрации</b>\n\n"
    f"👤 {full_name}\n"
    f"🆔 <code>{user_id}</code>\n"
    f"📌 Должность: {position}\n"
    f"📌 Причина: {reason}\n\n"
    f"⚠️ Варны: {warns}/5\n"
    f"🔇 Муты: {mutes}/3\n"
    f"👮 Снял: {message.from_user.full_name}",
    parse_mode="HTML"
)

   

 

    await message.answer(
        "✅ Администратор успешно снят."
    )

    await state.clear()

# ==========================
# KICK
# ==========================

@dp.message(Command("kick"))
async def kick_user(message: Message):

    if not await bot_active_check(message):
        return

    if not await admin_check(message):
        return

    args = message.text.split(maxsplit=2)

    # Кик ответом
    if message.reply_to_message:

        if len(args) < 2:
            await message.answer(
                "❌ Укажите причину.\n"
                "Пример: /kick Флуд"
            )
            return

        user = message.reply_to_message.from_user
        reason = args[1]

    else:

        if len(args) < 3:
            await message.answer(
                "❌ Использование:\n"
                "/kick @username Причина\n\n"
                "/kick ID Причина"
            )
            return

        target = args[1]
        reason = args[2]

        try:
            if target.startswith("@"):
                user = await bot.get_chat(target)
            else:
                user = await bot.get_chat(int(target))

        except:
            await message.answer(
                "❌ Пользователь не найден."
            )
            return

    # Защита от кика самого себя
    if user.id == message.from_user.id:
        await message.answer(
            "❌ Нельзя исключить самого себя."
        )
        return

    # Исключение
    try:
        await bot.ban_chat_member(
            GROUP_ID,
            user.id
        )

        await bot.unban_chat_member(
            GROUP_ID,
            user.id
        )

    except:
        await message.answer(
            "❌ Не удалось исключить пользователя."
        )
        return

    tag = (
        f"@{user.username}"
        if user.username
        else user.full_name
    )

    from datetime import datetime

    now = datetime.now()

    sent = await bot.send_message(
        GROUP_ID,
        "╔════════════════════════╗\n"
        "🚨 <b>Исключение из сообщества</b>\n"
        "╚════════════════════════╝\n\n"
        "👢 <b>Участник исключён из сообщества</b>\n\n"
        f"👤 <b>Пользователь:</b> {tag}\n"
        f"📝 <b>Причина:</b> {reason}\n"
        f"📅 <b>Дата:</b> <code>{now.strftime('%d.%m.%Y')}</code>\n"
        f"🕒 <b>Время:</b> <code>{now.strftime('%H:%M:%S')}</code>\n"
        f"🆔 <b>ID сообщения:</b> <code>AUTO-{now.strftime('%d%m%H%M%S')}</code>\n"
        "📍 <b>Статус:</b> ✅ Исполнено\n\n"
        "════════════════════════\n"
        "⚙️ <i>Запись автоматически сохранена в журнале администрации.</i>",
        parse_mode="HTML"
    )

    # Личное уведомление
    try:
        await bot.send_message(
            user.id,
            "👢 Вы были исключены из группы «Одесские».\n\n"
            f"📌 Причина: {reason}"
        )
    except:
        pass

    # Статистика
    STATS["kicks"] += 1
    save_stats()

    # Ссылка на сообщение
    link = f"https://t.me/c/{str(GROUP_ID)[4:]}/{sent.message_id}"

    # Лог
    await send_log(
        f"👢 Пользователь исключён\n"
        f"👤 Модератор: {message.from_user.full_name}\n"
        f"🆔 ID модератора: {message.from_user.id}\n"
        f"👤 Пользователь: {user.full_name}\n"
        f"🆔 ID пользователя: {user.id}\n"
        f"📌 Причина: {reason}\n"
        f"🔗 Ссылка: {link}"
    )

    # Удаляем команду /kick
    try:
        await message.delete()
    except:
        pass

# ==========================
# ПРОВЕРКА ПОЛЬЗОВАТЕЛЯ /ids
# ==========================


@dp.message(Command("ids"))
async def ids_command(message: Message):

    args = message.text.split(maxsplit=1)


    if len(args) < 2:

        await message.answer(
            "❌ Использование:\n\n"
            "/ids ID\n"
            "или\n"
            "/ids @username"
        )

        return



    target = args[1]


    try:

        if target.startswith("@"):

            user = await bot.get_chat(target)


        else:

            user = await bot.get_chat(
                int(target)
            )


    except:

        await message.answer(
            "❌ Пользователь не найден."
        )

        return



    username = (
        f"@{user.username}"
        if user.username
        else "Нет"
    )


    await message.answer(
        "🔍 <b>Информация о пользователе</b>\n\n"
        f"👤 Имя: {user.full_name}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"🔗 Username: {username}",
        parse_mode="HTML"
    )





# ==========================
# СПИСОК АДМИНИСТРАТОРОВ
# ==========================

@dp.message(Command("admins"))
async def admins_command(message: Message):

    text = (
        "👮 <b>Администрация группы «Одесские»</b>\n\n"
    )

    count = 0
    online_count = 0

    now = datetime.now()

    for admin_id in ADMINS:

        try:
            user = await bot.get_chat(admin_id)

            tag = (
                f"@{user.username}"
                if user.username
                else user.full_name
            )

            # Проверяем активность
            if admin_id in ADMIN_ACTIVITY:

                diff = now - ADMIN_ACTIVITY[admin_id]
                minutes = diff.seconds // 60

                if minutes <= 5:
                    status = "🟢 В сети"
                    online_count += 1

                elif minutes <= 60:
                    status = f"🟡 Был {minutes} мин назад"

                elif minutes < 1440:
                    status = f"🟠 Был {minutes // 60} ч назад"

                else:
                    status = f"⚫ Был {diff.days} дн назад"

            else:
                status = "⚫ Не в сети"

            text += f"• {tag} — {status}\n"

            count += 1

        except:
            pass

    text += (
        f"\n🟢 В сети: {online_count}\n"
        f"📊 Всего администраторов: {count}\n"
        f"🕒 Время запроса: {now.strftime('%d.%m.%Y %H:%M:%S')}"
    )

    await message.answer(
        text,
        parse_mode="HTML"
    )



# ==========================
# ID ПОЛЬЗОВАТЕЛЯ
# ==========================

@dp.message(Command("id"))
async def id_command(message: Message):

    user = message.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "Отсутствует"
    )

    full_name = user.full_name

    # Дата регистрации Telegram недоступна через Bot API
    created = "Недоступно"

    text = (
        "🪪 <b>Информация о вашем аккаунте</b>\n\n"
        f"👤 <b>Имя:</b> {full_name}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"🔗 <b>Username:</b> {username}\n"
        f"📅 <b>Дата создания аккаунта:</b> {created}\n"
        f"🕒 <b>Время запроса:</b> "
        f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
    )

    await message.answer(
        text,
        parse_mode="HTML"
    )




# ==========================
# ИНФОРМАЦИЯ О ГРУППЕ
# ==========================

@dp.message(Command("infogroup"))
async def rules_command(message: Message):

    await message.answer(
        "🏙 <b>СООБЩЕСТВО «ОДЕССКИЕ»</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "👋 <b>Добро пожаловать!</b>\n"
        "Рады видеть вас в официальной группе «Одесские».\n\n"

        "📌 <b>В нашем сообществе вы можете:</b>\n"
        "├ 💬 Общаться с участниками\n"
        "├ 📢 Следить за объявлениями\n"
        "├ 🤝 Получать помощь администрации\n"
        "└ 🎉 Участвовать в жизни сообщества\n\n"

        "⚙️ <b>Полезные команды</b>\n"
        "├ 📖 <b>/help</b> — список всех команд\n"
        "├ 🚨 <b>/admin</b> — вызвать администрацию\n"
        "├ 📜 <b>/report</b> — отправить жалобу\n"
        "└ 🆔 <b>/id</b> — узнать свой ID\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "💙 <i>Желаем приятного общения в сообществе «Одесские»!</i>",
        parse_mode="HTML"
    )



# ==========================
# ПОМОЩЬ
# ==========================


@dp.message(Command("help"))
async def help_command(message: Message):


  await message.answer(
    "✨ <b>ЦЕНТР УПРАВЛЕНИЯ • ОДЕССКИЕ</b>\n"
    "━━━━━━━━━━━━━━━━━━\n\n"

    "👤 <b>Основные команды</b>\n"
    "┌ 🆔 <b>/id</b> — Ваш Telegram ID\n"
    "├ 🔍 <b>/ids</b> — Информация о пользователе\n"
    "├ 📜 <b>/infogroup</b> — Сведения о группе\n"
    "├ 🚨 <b>/report</b> — Отправить жалобу\n"
    "├ 📣 <b>/admin</b> — Вызвать администрацию\n"
    "└ ❌ <b>/cancel</b> — Отменить действие\n\n"

    "🛡 <b>Команды администрации</b>\n"
    "┌ 📢 <b>/b</b> — Создать объявление\n"
    "├ 👢 <b>/kick</b> — Исключить пользователя\n"
    "├ 👮 <b>/admins</b> — Список администрации\n"
    "├ ➕ <b>/add ID</b> — Назначить администратора\n"
    "├ ➖ <b>/del ID причина</b> — Снять администратора\n"
    "├ 📊 <b>/stats</b> — Статистика бота\n"
    "└ 🏓 <b>/ping</b> — Проверка работы\n\n"

    "━━━━━━━━━━━━━━━━━━\n"
    "💙 <i>Спасибо, что пользуетесь ботом сообщества «Одесские»!</i>",
    parse_mode="HTML"
)





# ==========================
# СТАТИСТИКА
# ==========================


@dp.message(Command("stats"))
async def stats_command(message: Message):


    await message.answer(
        "📊 <b>Статистика бота</b>\n\n"
        f"👋 Новых участников: {daily_joins}\n"
        f"🚨 Жалоб: {daily_reports}\n"
        f"📢 Объявлений: {daily_broadcasts}",

        parse_mode="HTML"
    )


async def handle_new_members(message: Message):
    # Новый участник
    if message.new_chat_members:

        for user in message.new_chat_members:

            daily_joins += 1
            STATS["joins"] += 1
            save_stats()

            await send_log(
                "Новый участник",
                message,
                extra=(
                    f"👤 <b>Участник:</b> {user.full_name}\n"
                    f"🆔 <b>ID:</b> <code>{user.id}</code>"
                )
            )

            await message.answer(
    f"👋 Добро пожаловать, <b>{user.first_name}</b>!\n\n"
    "⚓ Вы успешно присоединились к группе «Одесские».\n\n"
    "📋 Для просмотра доступных команд используйте: /help\n"
    "👮 Для связи с администрацией используйте: /admin\n\n"
    "Желаем приятного общения!",
    parse_mode="HTML"
)

        return


# ==========================
# УНИВЕРСАЛЬНЫЕ ЛОГИ
# ==========================

async def send_log(action: str, message: Message = None, extra: str = ""):
    try:
        time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        text = (
            f"🕒 <b>{time}</b>\n\n"
            f"📌 <b>Действие:</b> {action}\n"
        )

        if message:
            text += (
                f"👤 <b>Пользователь:</b> {message.from_user.full_name}\n"
                f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
                f"💬 <b>Чат:</b> <code>{message.chat.id}</code>\n"
                f"📦 <b>Тип:</b> {message.content_type}\n"
            )

            if message.text:
                text += f"📝 <b>Текст:</b> {message.text}\n"

        if extra:
            text += f"\n{extra}"

        await bot.send_message(
            ACTION_LOG_CHANNEL,
            text,
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Ошибка логов: {e}")


# ==========================
# ГЛОБАЛЬНЫЕ ЛОГИ
# ==========================

@dp.message()
async def global_logger(message: Message):

    # Не трогаем команды
    if message.text and message.text.startswith("/"):
        return

    # Новый участник
    if message.new_chat_members:
        for user in message.new_chat_members:

            global daily_joins
            daily_joins += 1

            STATS["joins"] += 1
            save_stats()

            await send_log(
                "Новый участник",
                message,
                extra=(
                    f"👤 <b>Участник:</b> {user.full_name}\n"
                    f"🆔 <b>ID:</b> <code>{user.id}</code>"
                )
            )

            await message.answer(
                f"🎉 <b>Добро пожаловать, {user.first_name}!</b>\n\n"
                "╔════════════════════╗\n"
                "      🏙 <b>Одесские</b>\n"
                "╚════════════════════╝\n\n"
                "🤝 Спасибо, что стали частью нашего сообщества!\n"
                "Здесь вы можете общаться, находить новых друзей и всегда рассчитывать на помощь администрации.\n\n"
                "📌 <b>Для начала рекомендуем:</b>\n"
                "📜 • <b>/rules</b> — ознакомиться с правилами\n"
                "📖 • <b>/help</b> — посмотреть все команды бота\n\n"
                "💬 <i>Желаем приятного общения и отличного настроения!</i> 💙"
            ,
                parse_mode="HTML"
            )

        return

    # Выход участника
    if message.left_chat_member:
        user = message.left_chat_member

        await send_log(
            "Участник покинул группу",
            message,
            extra=(
                f"👤 <b>Участник:</b> {user.full_name}\n"
                f"🆔 <b>ID:</b> <code>{user.id}</code>"
            )
        )
        return

    # Смена названия
    if message.new_chat_title:
        await send_log(
            "Изменено название группы",
            message,
            extra=f"📛 <b>Новое название:</b> {message.new_chat_title}"
        )
        return

    # Фото группы
    if message.new_chat_photo:
        await send_log("Изменено фото группы", message)
        return

    # Удалено фото
    if message.delete_chat_photo:
        await send_log("Удалено фото группы", message)
        return

    # Закреп
    if message.pinned_message:
        await send_log(
            "Закреплено сообщение",
            message,
            extra=f"📌 <b>ID сообщения:</b> {message.pinned_message.message_id}"
        )
        return

    # Обычное сообщение
    text = message.text or message.caption or "Без текста"

    await send_log(
        "Новое сообщение",
        message,
        extra=f"📝 <b>Текст:</b> {text[:500]}"
    )


# ==========================
# ВЫДАЧА ПРАВ
# ==========================

async def grant_user_rights(user_id):
    # Основная группа
    try:
        await bot.promote_chat_member(
            GROUP_ID,
            user_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=True,
            can_change_info=True,
            can_pin_messages=True,
            can_post_stories=True,
            can_edit_stories=True,
            can_delete_stories=True,
            is_anonymous=False
        )
    except Exception as e:
        print(f"Ошибка выдачи прав в группе: {e}")

    # ADMIN_LOG_CHANNEL — выдаём права администратора
    try:
        await bot.promote_chat_member(
            ADMIN_LOG_CHANNEL,
            user_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=True,
            can_change_info=True,
            can_pin_messages=True,
            can_post_stories=True,
            can_edit_stories=True,
            can_delete_stories=True,
            is_anonymous=False
        )
    except Exception as e:
        print(f"Ошибка выдачи прав в ADMIN_LOG_CHANNEL: {e}")

    # ACTION_LOG_CHANNEL — просто добавляем в группу
    try:
        invite = await bot.create_chat_invite_link(
            ACTION_LOG_CHANNEL,
            member_limit=1
        )

        await bot.send_message(
            user_id,
            "📩 Вас добавили в группу логов.\n"
            f"Перейдите по ссылке:\n{invite.invite_link}"
        )

    except Exception as e:
        print(f"Ошибка приглашения в ACTION_LOG_CHANNEL: {e}")


# ==========================
# АНТИ-МАТ
# ==========================

BAD_WORDS = [
    "бля", "блядь", "блять", "блядина", "блядский",
    "сука", "сучка", "сучара",
    "нахуй", "нахуй", "нах", "нахер",
    "похуй", "похер",
    "хуй", "хуйня", "хуево", "хуёв", "хуесос", "хуесоска",
    "еб", "ебать", "ебан", "ёбан", "ебал", "ебло", "еблан",
    "ебаный", "ёбаный", "заеб", "заёб", "выеб", "выёб",
    "пизда", "пиздец", "пизд", "пиздюк", "пиздобол",
    "мудак", "мудак", "мудила",
    "гандон", "гондон", "придурок",
    "долбоеб", "долбоёб", "дебил",
    "идиот", "тварь", "мразь",
    "уебок", "уёбок", "ублюдок",
    "шлюха", "проститутка",
    "соси", "отсоси",
    "залупа", "очко",
    "говно", "дерьмо"
]


@dp.message()
async def anti_swear(message: Message):

    if not message.text:
        return

    text = message.text.lower()

    if any(word in text for word in BAD_WORDS):
        await message.reply(
            "⚠️ Следите за тем, что пишете.\n\n"
            "👮 /admins\n\n"
            "Администрация видит все сообщения. "
            "При необходимости будут приняты меры."
        )



# ==========================
# АНТИСПАМ
# ==========================

@dp.message()
async def anti_spam(message: Message):

    # Игнорируем команды
    if message.text and message.text.startswith("/"):
        return

    user_id = message.from_user.id
    now = time.time()

    if user_id not in SPAM:
        SPAM[user_id] = []

    # Оставляем только сообщения за последние 5 секунд
    SPAM[user_id] = [
        t for t in SPAM[user_id]
        if now - t < 5
    ]

    SPAM[user_id].append(now)

    # Если за 5 секунд отправлено 5 и более сообщений
    if len(SPAM[user_id]) >= 5:

        try:
            await message.delete()
        except:
            pass

        try:
            from datetime import timedelta

            await bot.restrict_chat_member(
                GROUP_ID,
                user_id,
                permissions=ChatPermissions(
                    can_send_messages=False
                ),
                until_date=datetime.now() + timedelta(minutes=10)
            )

            warn = await message.answer(
                f"🔇 <b>{message.from_user.full_name}</b> получил мут на <b>10 минут</b>.\n\n"
                "📌 <b>Причина:</b> Спам сообщениями.",
                parse_mode="HTML"
            )

        except Exception as e:
            print(e)

        await asyncio.sleep(5)

        try:
            await warn.delete()
        except:
            pass

# ==========================
# ПРАВИЛА
# ==========================

@dp.message(Command("rules"))
async def rules_command(message: Message):

    await message.answer(
        "📖 <b>Правила группы «Одесские»</b>\n\n"
        "Просим каждого участника обязательно ознакомиться с действующими правилами группы.\n\n"
        "🔗 https://telegra.ph/OFICIALNYE-PRAVILA-GRUPPY-Odesskie-08-01\n\n"
        "⚠️ <b>1.1.</b> Каждый пользователь, вступивший в группу, обязан соблюдать данные правила. "
        "Незнание правил не освобождает от ответственности.",
        parse_mode="HTML",
        disable_web_page_preview=True
    )


@dp.message()
async def global_logger(message: Message):

# ==========================
# MUTE FSM
# ==========================

   class MuteState(StatesGroup):
    waiting_user = State()
    waiting_gender = State()
    waiting_time = State()
    waiting_warns = State()
    waiting_mutes = State()
    waiting_reason = State()
    confirm = State()

# ========================== #
#  /mute # 
# ==========================
@dp.message(Command("mute"))
async def mute_start(message: Message, state: FSMContext):

    print("MUTE WORK")

    if not await admin_check(message):
        print("NOT ADMIN")
        return

    print("ADMIN OK")

    await state.set_state(MuteState.waiting_user)

    await message.answer(
        "👤 Отправьте:\n\n"
        "• ID пользователя\n"
        "или\n"
        "• @username"
    )

# ==========================
# ВЫБОР ПОЛА
# ==========================

@dp.message(MuteState.waiting_user)
async def mute_user(message: Message, state: FSMContext):

    user = message.text.strip()

    await state.update_data(user=user)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚹 Мужчина",
                    callback_data="mute_male"
                ),
                InlineKeyboardButton(
                    text="🚺 Женщина",
                    callback_data="mute_female"
                )
            ]
        ]
    )

    await state.set_state(MuteState.waiting_gender)

    await message.answer(
        "👤 Выберите пол пользователя:",
        reply_markup=keyboard
    )

    # ==========================
# ПОЛ
# ==========================

@dp.callback_query(StateFilter(MuteState.waiting_gender))
async def mute_gender(callback: CallbackQuery, state: FSMContext):

    if callback.data == "mute_male":
        gender = "получает"

    else:
        gender = "получает"

    await state.update_data(
        gender=gender
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="15 минут",
                    callback_data="time_15"
                ),
                InlineKeyboardButton(
                    text="30 минут",
                    callback_data="time_30"
                )
            ],
            [
                InlineKeyboardButton(
                    text="1 час",
                    callback_data="time_60"
                ),
                InlineKeyboardButton(
                    text="3 часа",
                    callback_data="time_180"
                )
            ],
            [
                InlineKeyboardButton(
                    text="6 часов",
                    callback_data="time_360"
                ),
                InlineKeyboardButton(
                    text="12 часов",
                    callback_data="time_720"
                )
            ],
            [
                InlineKeyboardButton(
                    text="24 часа",
                    callback_data="time_1440"
                )
            ]
        ]
    )

    await state.set_state(MuteState.waiting_time)

    await callback.message.edit_text(
        "⏳ Выберите срок мута:",
        reply_markup=keyboard
    )

    await callback.answer()


    # ==========================
# ВЫБОР ВРЕМЕНИ
# ==========================

@dp.callback_query(StateFilter(MuteState.waiting_time))
async def mute_time(callback: CallbackQuery, state: FSMContext):

    times = {
        "time_15": "15 минут",
        "time_30": "30 минут",
        "time_60": "1 час",
        "time_180": "3 часа",
        "time_360": "6 часов",
        "time_720": "12 часов",
        "time_1440": "24 часа"
    }

    mute_time = times[callback.data]

    await state.update_data(
        mute_time=mute_time
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="0/5", callback_data="warn_0"),
                InlineKeyboardButton(text="1/5", callback_data="warn_1"),
                InlineKeyboardButton(text="2/5", callback_data="warn_2")
            ],
            [
                InlineKeyboardButton(text="3/5", callback_data="warn_3"),
                InlineKeyboardButton(text="4/5", callback_data="warn_4"),
                InlineKeyboardButton(text="5/5", callback_data="warn_5")
            ]
        ]
    )

    await state.set_state(MuteState.waiting_warns)

    await callback.message.edit_text(
        "⚠️ <b>Выберите количество предупреждений:</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await callback.answer()

# ==========================
# ВЫБОР ВАРНОВ
# ==========================

@dp.callback_query(StateFilter(MuteState.waiting_warns))
async def mute_warns(callback: CallbackQuery, state: FSMContext):

    warns = callback.data.replace("warn_", "")

    await state.update_data(
        warns=warns
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1/3", callback_data="mute_1"),
                InlineKeyboardButton(text="2/3", callback_data="mute_2"),
                InlineKeyboardButton(text="3/3", callback_data="mute_3")
            ]
        ]
    )

    await state.set_state(MuteState.waiting_mutes)

    await callback.message.edit_text(
        "⛔ <b>Выберите количество мутов:</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await callback.answer()


# ==========================
# БАЗА ПОЛЬЗОВАТЕЛЕЙ
# ==========================

def load_users():

    if not os.path.exists(USERS_FILE):
        return []

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users):

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)


USERS = load_users()



# ==========================
# СОХРАНЕНИЕ ПОЛЬЗОВАТЕЛЕЙ
# ==========================

@dp.message()
async def save_user(message: Message):

    global USERS

    if message.from_user.is_bot:
        return

    user = {
        "id": message.from_user.id,
        "name": message.from_user.full_name,
        "username": message.from_user.username
    }

    if not any(x["id"] == user["id"] for x in USERS):

        USERS.append(user)

        save_users(USERS)



# ==========================================
# АВТОДУБЛИРОВАНИЕ
# ==========================================

SOURCE_CHAT_ID = -1001377127926   # группа-источник
TARGET_CHAT_ID = -1003941822063   # куда дублировать


@dp.message()
async def duplicate_message(message: Message):

    if message.chat.id != SOURCE_CHAT_ID:
        return

    try:
        await message.send_copy(
            chat_id=TARGET_CHAT_ID
        )

    except Exception as e:
        print(f"Ошибка дублирования: {e}")

    
 # ==========================
# MAIN
# ==========================

async def main():

    try:

        await bot.delete_webhook(
            drop_pending_updates=True
        )

        try:

            bot_message = await bot.send_message(
                GROUP_ID,
                "🟢 <b>Бот снова работает</b>\n\n"
                "Система успешно запущена и продолжает работу.",
                parse_mode="HTML"
            )


            async def delete_message():

                await asyncio.sleep(60)

                try:
                    await bot_message.delete()
                except:
                    pass


            asyncio.create_task(delete_message())


        except Exception:
            pass


        print("✅ Бот запущен!")


        await dp.start_polling(bot)


    except Exception as e:

        print(
            f"❌ Ошибка запуска: {e}"
        )


if __name__ == "__main__":
    asyncio.run(main())
    print("BOT LOADED")