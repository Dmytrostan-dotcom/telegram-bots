import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "8863305349:AAF8MgJ6SJWLA8uG74pXR8RzimIxrUx_Mi8"

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class BroadcastState(StatesGroup):
    waiting_text = State()
    waiting_chat_id = State()


@dp.message(Command("b"))
async def start_broadcast(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        return

    await state.set_state(BroadcastState.waiting_text)

    await message.answer(
        "📢 <b>ОТПРАВКА СООБЩЕНИЯ</b>\n\n"
        "📝 Отправьте текст, который нужно отправить в группу или канал.",
        parse_mode="HTML"
    )


@dp.message(BroadcastState.waiting_text)
async def get_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(BroadcastState.waiting_chat_id)

    await message.answer(
        "🎯 <b>КУДА ОТПРАВИТЬ?</b>\n\n"
        "Отправьте ID группы или канала.\n\n"
        "Например:\n"
        "<code>-1003941822063</code>",
        parse_mode="HTML"
    )


@dp.message(BroadcastState.waiting_chat_id)
async def send_message(message: types.Message, state: FSMContext):
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

    except ValueError:
        await message.answer(
            "❌ ID должен состоять из цифр.\n\n"
            "Например:\n"
            "<code>-1003941822063</code>",
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(
            "❌ <b>Не удалось отправить сообщение.</b>\n\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML"
        )

    await state.clear()


async def main():
    print("🚀 Бот отправки сообщений запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())