import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Токен теперь берется из безопасного поля на Bothost
ADMIN_ID = 7095206192
CHANNEL_ID = -1004417956541

logging.basicConfig(level=logging.INFO)
# Запуск обычный, без всяких прокси, так как сервер находится в Нидерландах
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_admin_kb(user_id: int, msg_id: int) -> InlineKeyboardMarkup:
    """Генерирует инлайн-кнопки для админа."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Опубликовать", callback_data=f"pub_{user_id}_{msg_id}")
    builder.button(text="❌ Отклонить", callback_data=f"rej_{user_id}_{msg_id}")
    builder.adjust(2)
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Отправь мне текст или фото для публикации. Я передам их на модерацию.")

@dp.message(F.content_type.in_({'text', 'photo'}))
async def handle_suggestion(message: types.Message):
    await bot.copy_message(
        chat_id=ADMIN_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        reply_markup=get_admin_kb(message.chat.id, message.message_id)
    )
    await message.answer("Твое сообщение улетело на модерацию!")

@dp.message()
async def handle_wrong_formats(message: types.Message):
    await message.answer("Я принимаю только текст и фото.")

@dp.callback_query(F.data.startswith("pub_"))
async def cb_publish(callback: types.CallbackQuery):
    _, user_id, msg_id = callback.data.split("_")
    
    try:
        await bot.copy_message(
            chat_id=CHANNEL_ID,
            from_chat_id=int(user_id),
            message_id=int(msg_id)
        )
        
        kb = InlineKeyboardBuilder()
        kb.button(text="Опубликовано ✅", callback_data="done")
        await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
        await callback.answer("Успешно отправлено в канал!")
        
    except Exception as e:
        await callback.answer(f"Ошибка публикации: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("rej_"))
async def cb_reject(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="Отклонено ❌", callback_data="done")
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
    await callback.answer("Сообщение отклонено.")

@dp.callback_query(F.data == "done")
async def cb_done(callback: types.CallbackQuery):
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())