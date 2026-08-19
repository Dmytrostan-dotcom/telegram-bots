import asyncio
from telethon import TelegramClient, events


# ==========================
# TELEGRAM
# ==========================

API_ID = 33876323
API_HASH = "8807feaa2c10beb3f07eb7cee16b75cf"

# Канал/группа-источник
SOURCE = -1001455546058

# Группы, куда пересылать
TARGETS = [
    -1002079460983,
    -1003941822063,
]


client = TelegramClient(
    "odesskie_forwarder",
    API_ID,
    API_HASH
)


# ==========================
# АВТОМАТИЧЕСКАЯ ПЕРЕСЫЛКА
# ==========================

@client.on(events.NewMessage(chats=SOURCE))
async def forward_message(event):

    try:

        for target in TARGETS:

            await client.forward_messages(
                target,
                event.message
            )

            print(
                f"✅ Сообщение переслано → {target}"
            )

        print("📨 Новое сообщение обработано")

    except Exception as e:

        print(
            f"❌ Ошибка пересылки: {e}"
        )


# ==========================
# КОМАНДА /b
# ==========================

@client.on(
    events.NewMessage(
        pattern=r"^/b(?:\s+([\s\S]+))?$"
    )
)
async def test_send(event):

    # Команда работает только в личных сообщениях
    if not event.is_private:
        return

    text = event.pattern_match.group(1)

    if not text:

        await event.reply(
            "❌ Использование:\n\n"
            "/b текст сообщения"
        )

        return

    try:

        for target in TARGETS:

            await client.send_message(
                target,
                text
            )

            print(
                f"📤 /b → сообщение отправлено в {target}"
            )

        await event.reply(
            "✅ Сообщение отправлено в обе группы."
        )

    except Exception as e:

        await event.reply(
            f"❌ Ошибка отправки:\n{e}"
        )

        print(
            f"❌ Ошибка /b: {e}"
        )


# ==========================
# МОНИТОРИНГ СОЕДИНЕНИЯ
# ==========================

async def check_connection():

    was_disconnected = False

    while True:

        try:

            if not client.is_connected():

                if not was_disconnected:

                    print(
                        "🔴 Соединение с Telegram потеряно..."
                    )

                    was_disconnected = True

            else:

                if was_disconnected:

                    print(
                        "🟢 Соединение с Telegram восстановлено!"
                    )

                    print(
                        "📡 Продолжаю работу..."
                    )

                    was_disconnected = False

        except Exception as e:

            print(
                f"⚠️ Ошибка проверки соединения: {e}"
            )

        await asyncio.sleep(5)


# ==========================
# MAIN
# ==========================

async def main():

    print(
        "🚀 Одесские Forwarder запускается..."
    )

    await client.start()

    print(
        "✅ Авторизация выполнена"
    )

    print(
        f"📡 Источник: {SOURCE}"
    )

    print(
        f"📤 Получатели: {TARGETS}"
    )

    print(
        "👀 Ожидаю новые сообщения..."
    )

    # Запускаем мониторинг соединения
    asyncio.create_task(
        check_connection()
    )

    await client.run_until_disconnected()


# ==========================
# ЗАПУСК
# ==========================

if __name__ == "__main__":

    asyncio.run(main())