import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.state import StateFilter

TOKEN = "8920521491:AAHoc1ld2Pz_1yoyYROakRFAIRHSboumIYQ"
CHANNEL_ID = -1004449814472
CHAT_ID = -1004499154170
ADMINS = [8326482234, 7217920772]

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

class BroadcastState(StatesGroup):
    waiting_chat = State()
    waiting_message = State()

async def admin_check(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ Нет доступа.")
        return False
    return True

@dp.message(Command("b"))
async def b_start(message: Message, state: FSMContext):
    if not await admin_check(message):
        return
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📣 Канал",callback_data="bc_channel")],
        [InlineKeyboardButton(text="💬 Чат",callback_data="bc_chat")],
        [InlineKeyboardButton(text="❌ Отмена",callback_data="bc_cancel")]
    ])
    await state.set_state(BroadcastState.waiting_chat)
    await message.answer("Выберите место для рассылки:", reply_markup=kb)

@dp.callback_query(StateFilter(BroadcastState.waiting_chat))
async def choose(call: CallbackQuery, state:FSMContext):
    if call.data=="bc_cancel":
        await state.clear()
        await call.message.edit_text("❌ Отменено.")
        return
    chat_id = CHANNEL_ID if call.data=="bc_channel" else CHAT_ID
    await state.update_data(chat_id=chat_id)
    await state.set_state(BroadcastState.waiting_message)
    await call.message.edit_text("📨 Отправьте сообщение для рассылки.")
    await call.answer()

@dp.message(StateFilter(BroadcastState.waiting_message))
async def send_broadcast(message:Message,state:FSMContext):
    data=await state.get_data()
    try:
        await message.send_copy(data["chat_id"])
        await message.answer("✅ Рассылка отправлена.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
