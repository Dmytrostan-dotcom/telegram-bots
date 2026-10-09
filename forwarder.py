import os
import base64
import asyncio
import logging
from pathlib import Path

from telethon import TelegramClient, events


# ==========================================
# НАСТРОЙКИ TELEGRAM
# ==========================================

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "").strip()

SOURCE = -1004360890430

TARGETS = [
    -1002079460983,
    -1003941822063,
]


# ==========================================
# ПОСТОЯННОЕ ХРАНИЛИЩЕ RAILWAY
# ==========================================

SESSION_DIR = Path("/app/session")
SESSION_DIR.mkdir(parents=True, exist_ok=True)

SESSION_FILE = SESSION_DIR / "news_account_new.session"
SESSION_NAME = str(SESSION_DIR / "news_account_new")


def prepare_session():
    """Восстанавливает файл Telethon-сессии из двух переменных Railway."""

    if SESSION_FILE.exists() and SESSION_FILE.stat().st_size > 0:
        print("✅ Файл Telethon-сессии найден в Volume.")
        return

    part1 = os.getenv("TELETHON_SESSION_B64_1", "").strip()
    part2 = os.getenv("TELETHON_SESSION_B64_2", "").strip()

    if not part1 or not part2:
        raise RuntimeError(
            "Не найдены TELETHON_SESSION_B64_1 и "
            "TELETHON_SESSION_B64_2 в Railway Variables."
        )

    encoded = part1 + part2

    try:
        session_data = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise RuntimeError(
            "Не удалось декодировать сессию. Проверь обе переменные."
        ) from exc

    if not session_data.startswith(b"SQLite format 3"):
        raise RuntimeError(
            "Полученный файл не похож на SQLite-файл Telethon-сессии."
        )

    SESSION_FILE.write_bytes(session_data)

    print("✅ Telethon-сессия сохранена в Volume.")


# ==========================================
# ПРОВЕРКА НАСТРОЕК
# ==========================================

if not API_ID or not API_HASH:
    raise RuntimeError(
        "Добавь API_ID и API_HASH в Railway Variables."
    )

prepare_session()


# ==========================================
# TELETHON CLIENT
# ==========================================

client = TelegramClient(
    SESSION_NAME,
    API_ID,
    API_HASH,
    connection_retries=10,
    retry_delay=5,
    auto_reconnect=True,
)


# ==========================================
# АВТОМАТИЧЕСКАЯ ПЕРЕСЫЛКА
# ==========================================

@client.on(events.NewMessage(chats=SOURCE))
async def forward_message(event):
    for target in TARGETS:
        try:
            await client.forward_messages(
                target,
                event.message,
            )

            print(f"✅ Сообщение переслано → {target}")

        except Exception:
            logging.exception(
                "Ошибка пересылки в %s", target
            )

    print("📨 Обработка сообщения завершена.")


# ==========================================
# КОМАНДА /b
# ==========================================

@client.on(events.NewMessage(pattern=r"^/b(?:\s+([\s\S]+))?$"))
async def test_send(event):
    if not event.is_private:
        return

    text = event.pattern_match.group(1)

    if not text:
        await event.reply(
            "❌ Использование:\n\n"
            "/b текст сообщения"
        )
        return

    success = []
    failed = []

    for target in TARGETS:
        try:
            await client.send_message(target, text)
            success.append(target)
            print(f"📤 /b → отправлено в {target}")

        except Exception:
            failed.append(target)
            logging.exception(
                "Ошибка команды /b для %s", target
            )

    if success and not failed:
        await event.reply(
            "✅ Сообщение отправлено во все группы."
        )
    elif success:
        await event.reply(
            f"⚠️ Отправлено: {success}\n"
            f"❌ Не удалось отправить: {failed}"
        )
    else:
        await event.reply(
            "❌ Не удалось отправить сообщение ни в одну группу."
        )


# ==========================================
# МОНИТОРИНГ СОЕДИНЕНИЯ
# ==========================================

async def check_connection():
    was_disconnected = False

    while True:
        try:
            if not client.is_connected():
                if not was_disconnected:
                    print("🔴 Соединение с Telegram потеряно.")
                    was_disconnected = True
            else:
                if was_disconnected:
                    print("🟢 Соединение с Telegram восстановлено.")
                    was_disconnected = False

        except Exception:
            logging.exception("Ошибка проверки соединения")

        await asyncio.sleep(5)


# ==========================================
# MAIN
# ==========================================

async def main():
    print("🚀 Одесские Forwarder запускается...")

    await client.start()

    me = await client.get_me()

    print("✅ Авторизация выполнена.")
    print(f"👤 Аккаунт: {me.first_name}")
    print(f"📡 Источник: {SOURCE}")
    print(f"📤 Получатели: {TARGETS}")
    print("👀 Ожидаю новые сообщения...")

    asyncio.create_task(check_connection())

    await client.run_until_disconnected()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹️ Остановка Forwarder.")
