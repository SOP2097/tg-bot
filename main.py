import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7095206192
CHANNEL_ID = -1004417956541

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_admin_kb(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Опубликовать", callback_data=f"pub_{user_id}")
    builder.button(text="❌ Отклонить", callback_data=f"rej_{user_id}")
    builder.adjust(2)
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Отправь мне текст или фото для публикации. Я передам их на модерацию.")

@dp.message(F.content_type.in_({'text', 'photo'}))
async def handle_suggestion(message: types.Message):
    # Формируем подпись с гиперссылкой
    signature = '\n\n<a href="https://t.me/LoveUgoZapad">Признания Юго-Западная</a>'
    user_text = message.html_text or ""
    
    try:
        # Отправляем админу пост уже с приклеенной подписью
        if message.photo:
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=message.photo[-1].file_id,
                caption=user_text + signature,
                parse_mode="HTML",
                reply_markup=get_admin_kb(message.chat.id)
            )
        else:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=user_text + signature,
                parse_mode="HTML",
                reply_markup=get_admin_kb(message.chat.id)
            )
        await message.answer("Твое сообщение улетело на модерацию!")
    except Exception as e:
        await message.answer("Произошла ошибка при отправке. Попробуй еще раз.")

@dp.message()
async def handle_wrong_formats(message: types.Message):
    await message.answer("Я принимаю только текст и фото.")

@dp.callback_query(F.data.startswith("pub_"))
async def cb_publish(callback: types.CallbackQuery):
    _, user_id = callback.data.split("_")
    
    try:
        # Копируем в канал сообщение из чата админа (оно уже с подписью)
        await bot.copy_message(
            chat_id=CHANNEL_ID,
            from_chat_id=ADMIN_ID,
            message_id=callback.message.message_id,
            reply_markup=None
        )
        
        kb = InlineKeyboardBuilder()
        kb.button(text="Опубликовано ✅", callback_data="done")
        await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
        await callback.answer("Успешно отправлено в канал!")
        
        # Уведомляем автора
        await bot.send_message(chat_id=int(user_id), text="Твой пост опубликован в канале!")
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

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
    # Принудительно отключаем всех двойников и сбрасываем залипшие сессии
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
