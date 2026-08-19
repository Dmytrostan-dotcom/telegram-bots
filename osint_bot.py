import aiohttp
import os
import re
import socket
import asyncio
import ipaddress
from urllib.parse import quote

import aiosqlite
import phonenumbers
import dns.resolver

from dotenv import load_dotenv
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


# =========================================================
# CONFIG
# =========================================================

load_dotenv(r"C:\Botik\.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в C:\\Botik\\.env")

if not ADMIN_ID:
    raise RuntimeError("❌ ADMIN_ID не найден в C:\\Botik\\.env")

DB = "osint.db"

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()

# =========================================================
# STATES
# =========================================================

class Form(StatesGroup):
    person = State()
    username = State()
    phone = State()
    ip = State()
    domain = State()

    admin_user_id = State()


# =========================================================
# DATABASE
# =========================================================

async def db_init():

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            search_type TEXT,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.commit()


async def add_user(user_id):

    async with aiosqlite.connect(DB) as db:

        await db.execute(
            """
            INSERT OR IGNORE INTO users(user_id)
            VALUES(?)
            """,
            (user_id,)
        )

        await db.commit()


async def get_user(user_id):

    async with aiosqlite.connect(DB) as db:

        cur = await db.execute(
            """
            SELECT user_id, status
            FROM users
            WHERE user_id=?
            """,
            (user_id,)
        )

        return await cur.fetchone()


async def set_status(user_id, status):

    async with aiosqlite.connect(DB) as db:

        await db.execute(
            """
            INSERT INTO users(user_id, status)
            VALUES(?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET status=excluded.status
            """,
            (user_id, status)
        )

        await db.commit()


async def save_search(
    user_id,
    query,
    search_type,
    result
):

    async with aiosqlite.connect(DB) as db:

        await db.execute(
            """
            INSERT INTO searches
            (user_id, query, search_type, result)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                query,
                search_type,
                result
            )
        )

        await db.commit()


# =========================================================
# ACCESS
# =========================================================

def is_admin(user_id):

    return user_id == ADMIN_ID


async def has_access(user_id):

    if is_admin(user_id):
        return True

    user = await get_user(user_id)

    if not user:
        return False

    return user[1] == "active"


async def is_blocked(user_id):

    if is_admin(user_id):
        return False

    user = await get_user(user_id)

    return user and user[1] == "blocked"


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(admin=False):

    kb = InlineKeyboardBuilder()

    kb.button(
        text="🔎 Проверить человека",
        callback_data="person"
    )

    if admin:

        kb.button(
            text="📱 Номер",
            callback_data="phone"
        )

        kb.button(
            text="👤 Username",
            callback_data="username"
        )

        kb.button(
            text="🌐 IP",
            callback_data="ip"
        )

        kb.button(
            text="🔗 Домен",
            callback_data="domain"
        )

        kb.button(
            text="🔍 Интернет-поиск",
            callback_data="websearch"
        )

        kb.button(
            text="👑 Админ-панель",
            callback_data="admin"
        )

    kb.button(
        text="ℹ️ Помощь",
        callback_data="help"
    )

    kb.adjust(1, 2)

    return kb.as_markup()


def back_keyboard():

    kb = InlineKeyboardBuilder()

    kb.button(
        text="⬅️ Назад",
        callback_data="back"
    )

    return kb.as_markup()


def admin_keyboard():

    kb = InlineKeyboardBuilder()

    kb.button(
        text="➕ Выдать доступ",
        callback_data="give"
    )

    kb.button(
        text="➖ Забрать доступ",
        callback_data="remove"
    )

    kb.button(
        text="🚫 Заблокировать",
        callback_data="block"
    )

    kb.button(
        text="🔓 Разблокировать",
        callback_data="unblock"
    )

    kb.button(
        text="👥 Пользователи",
        callback_data="users"
    )

    kb.button(
        text="⬅️ Назад",
        callback_data="back"
    )

    kb.adjust(2)

    return kb.as_markup()


# =========================================================
# PUBLIC USERNAME SEARCH
# =========================================================

SITES = {
    "Telegram":
        "https://t.me/{username}",

    "GitHub":
        "https://github.com/{username}",

    "GitLab":
        "https://gitlab.com/{username}",

    "Reddit":
        "https://www.reddit.com/user/{username}",

    "Twitch":
        "https://www.twitch.tv/{username}",

    "Pinterest":
        "https://www.pinterest.com/{username}/",

    "Keybase":
        "https://keybase.io/{username}",
}


async def check_site(
    session,
    name,
    url
):

    try:

        async with session.get(
            url,
            timeout=8,
            allow_redirects=True,
            headers={
                "User-Agent":
                "Mozilla/5.0 PublicOSINTBot"
            }
        ) as response:

            return {
                "name": name,
                "url": url,
                "status": response.status
            }

    except Exception:

        return {
            "name": name,
            "url": url,
            "status": None
        }


async def username_lookup(username):

    username = (
        username
        .strip()
        .lstrip("@")
    )

    if not re.fullmatch(
        r"[A-Za-z0-9_.-]{2,64}",
        username
    ):

        return "❌ Некорректный username."

    async with aiohttp.ClientSession() as session:

        tasks = []

        for name, template in SITES.items():

            url = template.format(
                username=quote(username)
            )

            tasks.append(
                check_site(
                    session,
                    name,
                    url
                )
            )

        results = await asyncio.gather(
            *tasks
        )

    text = [
        f"🔎 <b>Username:</b> "
        f"<code>{username}</code>",
        ""
    ]

    for item in results:

        if item["status"] == 200:

            text.append(
                f"🟢 <b>{item['name']}</b>\n"
                f"{item['url']}"
            )

        else:

            text.append(
                f"⚪ {item['name']} — "
                f"не подтверждено"
            )

    return "\n\n".join(text)


# =========================================================
# PHONE
# =========================================================

def phone_lookup(number):

    try:

        parsed = phonenumbers.parse(
            number,
            None
        )

    except Exception:

        return "❌ Номер не распознан."

    valid = phonenumbers.is_valid_number(
        parsed
    )

    possible = phonenumbers.is_possible_number(
        parsed
    )

    country = phonenumbers.region_code_for_number(
        parsed
    )

    formatted = phonenumbers.format_number(
        parsed,
        phonenumbers.PhoneNumberFormat.INTERNATIONAL
    )

    return (
        "📱 <b>Проверка номера</b>\n\n"
        f"Номер: <code>{formatted}</code>\n"
        f"Страна: <code>{country or '—'}</code>\n"
        f"Валидный: "
        f"{'✅' if valid else '❌'}\n"
        f"Возможный: "
        f"{'✅' if possible else '❌'}\n\n"
        "ℹ️ Проверяется техническая информация "
        "о номере, а не личность владельца."
    )


# =========================================================
# IP
# =========================================================

def ip_lookup(ip):

    try:

        address = ipaddress.ip_address(
            ip
        )

    except ValueError:

        return "❌ Некорректный IP."

    try:

        hostname = socket.gethostbyaddr(
            ip
        )[0]

    except Exception:

        hostname = "не найден"

    return (
        "🌐 <b>IP</b>\n\n"
        f"Адрес: <code>{ip}</code>\n"
        f"Версия: IPv{address.version}\n"
        f"Reverse DNS: <code>{hostname}</code>\n\n"
        "⚠️ IP не является точным "
        "местоположением человека."
    )


# =========================================================
# DOMAIN
# =========================================================

async def domain_lookup(domain):

    domain = (
        domain
        .strip()
        .lower()
        .replace(
            "https://",
            ""
        )
        .replace(
            "http://",
            ""
        )
        .split("/")[0]
    )

    result = [
        "🔗 <b>DOMAIN OSINT</b>",
        "",
        f"Домен: <code>{domain}</code>"
    ]

    # A

    try:

        answers = dns.resolver.resolve(
            domain,
            "A"
        )

        ips = [
            str(x)
            for x in answers
        ]

        result.append(
            "\nIPv4:\n" +
            "\n".join(
                f"• <code>{x}</code>"
                for x in ips
            )
        )

    except Exception:

        result.append(
            "\nIPv4: —"
        )

    # MX

    try:

        answers = dns.resolver.resolve(
            domain,
            "MX"
        )

        mx = [
            str(x.exchange).rstrip(".")
            for x in answers
        ]

        result.append(
            "\nMX:\n" +
            "\n".join(
                f"• {x}"
                for x in mx
            )
        )

    except Exception:

        result.append(
            "\nMX: —"
        )

    # NS

    try:

        answers = dns.resolver.resolve(
            domain,
            "NS"
        )

        ns = [
            str(x).rstrip(".")
            for x in answers
        ]

        result.append(
            "\nNS:\n" +
            "\n".join(
                f"• {x}"
                for x in ns
            )
        )

    except Exception:

        result.append(
            "\nNS: —"
        )

    return "\n".join(result)


# =========================================================
# WEB SEARCH
# =========================================================

def web_search_links(query):

    q = quote(query)

    return (
        "🔍 <b>Публичный поиск</b>\n\n"

        f"🔎 Google:\n"
        f"https://www.google.com/search?q={q}\n\n"

        f"🔎 Bing:\n"
        f"https://www.bing.com/search?q={q}\n\n"

        f"🔎 DuckDuckGo:\n"
        f"https://duckduckgo.com/?q={q}"
    )



# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id

    await add_user(
        user_id
    )

    if is_admin(user_id):

        await message.answer(
            "👑 <b>OSINT ASSISTANT</b>\n\n"
            "Вы администратор.",
            reply_markup=main_keyboard(True)
        )

        return

    if await is_blocked(user_id):

        await message.answer(
            "🚫 Вы заблокированы."
        )

        return

    if await has_access(user_id):

        await message.answer(
            "👤 <b>Добро пожаловать.</b>",
            reply_markup=main_keyboard(False)
        )

    else:

        await message.answer(
            "⛔ Доступ не выдан.\n\n"
            "Обратитесь к администратору."
        )


# =========================================================
# BACK
# =========================================================

@dp.callback_query(F.data == "back")
async def back(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    admin = is_admin(
        callback.from_user.id
    )

    await callback.message.edit_text(
        "🔎 <b>Главное меню</b>",
        reply_markup=main_keyboard(admin)
    )

    await callback.answer()


# =========================================================
# PERSON
# =========================================================

@dp.callback_query(F.data == "person")
async def person(
    callback: CallbackQuery,
    state: FSMContext
):

    if not await has_access(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True
        )

        return

    await state.set_state(
        Form.person
    )

    await callback.message.edit_text(
        "🔎 <b>Проверить человека</b>\n\n"
        "Отправь публичный username.\n\n"
        "Например:\n"
        "<code>@example</code>",
        reply_markup=back_keyboard()
    )

    await callback.answer()


@dp.message(Form.person)
async def person_result(
    message: Message,
    state: FSMContext
):

    target = message.text.strip()

    await message.answer(
        "⏳ Проверяю публичные профили..."
    )

    result = await username_lookup(target)

    await save_search(
    message.from_user.id,
    target,
    "person",
    result
)

    await message.answer(
    result,
    disable_web_page_preview=True
)


# =========================================================
# USERNAME
# =========================================================

@dp.callback_query(F.data == "username")
async def username(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    await state.set_state(
        Form.username
    )

    await callback.message.edit_text(
        "👤 Введи username:",
        reply_markup=back_keyboard()
    )

    await callback.answer()


@dp.message(Form.username)
async def username_result(
    message: Message,
    state: FSMContext
):

    result = await username_lookup(
        message.text
    )

    await save_search(
        message.from_user.id,
        message.text,
        "username",
        result
    )

    await message.answer(
        result,
        disable_web_page_preview=True
    )

    await state.clear()


# =========================================================
# PHONE
# =========================================================

@dp.callback_query(F.data == "phone")
async def phone(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    await state.set_state(
        Form.phone
    )

    await callback.message.edit_text(
        "📱 Введи номер:\n\n"
        "<code>+380...</code>",
        reply_markup=back_keyboard()
    )

    await callback.answer()


@dp.message(Form.phone)
async def phone_result(
    message: Message,
    state: FSMContext
):

    result = phone_lookup(
        message.text
    )

    await save_search(
        message.from_user.id,
        message.text,
        "phone",
        result
    )

    await message.answer(
        result
    )

    await state.clear()


# =========================================================
# IP
# =========================================================

@dp.callback_query(F.data == "ip")
async def ip(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    await state.set_state(
        Form.ip
    )

    await callback.message.edit_text(
        "🌐 Введи IP:",
        reply_markup=back_keyboard()
    )

    await callback.answer()


@dp.message(Form.ip)
async def ip_result(
    message: Message,
    state: FSMContext
):

    result = ip_lookup(
        message.text.strip()
    )

    await save_search(
        message.from_user.id,
        message.text,
        "ip",
        result
    )

    await message.answer(
        result
    )

    await state.clear()


# =========================================================
# DOMAIN
# =========================================================

@dp.callback_query(F.data == "domain")
async def domain(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    await state.set_state(
        Form.domain
    )

    await callback.message.edit_text(
        "🔗 Введи домен:",
        reply_markup=back_keyboard()
    )

    await callback.answer()


@dp.message(Form.domain)
async def domain_result(
    message: Message,
    state: FSMContext
):

    await message.answer(
        "⏳ Проверяю DNS..."
    )

    result = await domain_lookup(
        message.text
    )

    await save_search(
        message.from_user.id,
        message.text,
        "domain",
        result
    )

    await message.answer(
        result
    )

    await state.clear()


# =========================================================
# WEB SEARCH
# =========================================================

@dp.callback_query(F.data == "websearch")
async def websearch(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    await callback.message.edit_text(
        "🔍 Для интернет-поиска отправь запрос "
        "обычным сообщением после нажатия этой кнопки.",
        reply_markup=back_keyboard()
    )

    await callback.answer()


# =========================================================
# ADMIN PANEL
# =========================================================

@dp.callback_query(F.data == "admin")
async def admin(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Только администратор",
            show_alert=True
        )

        return

    await callback.message.edit_text(
        "👑 <b>Админ-панель</b>",
        reply_markup=admin_keyboard()
    )

    await callback.answer()


# =========================================================
# GIVE / REMOVE / BLOCK
# =========================================================

@dp.callback_query(
    F.data.in_({
        "give",
        "remove",
        "block",
        "unblock"
    })
)
async def admin_action(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    await state.set_state(
        Form.admin_user_id
    )

    await state.update_data(
        action=callback.data
    )

    names = {
        "give": "➕ Выдать доступ",
        "remove": "➖ Забрать доступ",
        "block": "🚫 Заблокировать",
        "unblock": "🔓 Разблокировать"
    }

    await callback.message.edit_text(
        f"{names[callback.data]}\n\n"
        "Отправь Telegram ID пользователя.",
        reply_markup=back_keyboard()
    )

    await callback.answer()


@dp.message(Form.admin_user_id)
async def admin_action_result(
    message: Message,
    state: FSMContext
):

    if not is_admin(
        message.from_user.id
    ):
        return

    try:

        target_id = int(
            message.text.strip()
        )

    except ValueError:

        await message.answer(
            "❌ ID должен быть числом."
        )

        return

    data = await state.get_data()

    action = data["action"]

    await add_user(
        target_id
    )

    statuses = {
        "give": "active",
        "remove": "pending",
        "block": "blocked",
        "unblock": "active"
    }

    await set_status(
        target_id,
        statuses[action]
    )

    names = {
        "give": "выдан",
        "remove": "забран",
        "block": "заблокирован",
        "unblock": "разблокирован"
    }

    await message.answer(
        f"✅ Пользователь "
        f"<code>{target_id}</code> "
        f"— доступ {names[action]}.",
        reply_markup=admin_keyboard()
    )

    await state.clear()


# =========================================================
# USERS
# =========================================================

@dp.callback_query(F.data == "users")
async def users(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    async with aiosqlite.connect(DB) as db:

        cur = await db.execute(
            """
            SELECT user_id, status
            FROM users
            ORDER BY user_id
            """
        )

        rows = await cur.fetchall()

    if not rows:

        text = "👥 Пользователей нет."

    else:

        text = "👥 <b>Пользователи</b>\n\n"

        for uid, status in rows:

            text += (
                f"• <code>{uid}</code> — "
                f"{status}\n"
            )

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard()
    )

    await callback.answer()


# =========================================================
# HELP
# =========================================================

@dp.callback_query(F.data == "help")
async def help_button(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "ℹ️ <b>Помощь</b>\n\n"
        "Бот анализирует публичную информацию.\n\n"
        "Он не получает закрытые аккаунты, "
        "пароли, документы, скрытые контакты "
        "или точную геолокацию.",
        reply_markup=back_keyboard()
    )

    await callback.answer()


# =========================================================
# UNKNOWN MESSAGE
# =========================================================

@dp.message()
async def unknown(
    message: Message
):

    if await is_blocked(
        message.from_user.id
    ):

        return

    if not await has_access(
        message.from_user.id
    ):

        await message.answer(
            "⛔ У вас нет доступа."
        )

        return

    await message.answer(
        "Используй кнопки меню 👇",
        reply_markup=main_keyboard(
            is_admin(message.from_user.id)
        )
    )


# =========================================================
# START
# =========================================================

async def main():

    await db_init()

    print(
        "✅ OSINT Assistant запущен"
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )