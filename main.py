import asyncio
import logging
import os
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, ChatPermissions
from aiogram.utils.keyboard import InlineKeyboardBuilder

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7095206192
CHANNEL_ID = -1004417956541
GROUP_ID = -1000000000000  # <--- ID чата с комментариями

# === БАЗА ФЕЙКОВЫХ ПОСТОВ ===
FAKE_POSTS = [
    "Кто потерял наушники на скамейке возле главного входа? Оставил на охране.",
    "Девочка в красной куртке, которая покупала кофе на большой перемене — ты супер! Отзовись 💔",
    "Подскажите, препод по истории сильно валит на экзамене?",
    "Анон. Почему в столовке снова огромная очередь, кто-то вообще ходит на пары?",
    "Ищу парня, с которым сегодня столкнулись на выходе из метро. Ты был в черном пальто."
]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_admin_kb(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Опубликовать", callback_data=f"pub_{user_id}")
    builder.button(text="❌ Отклонить", callback_data=f"rej_{user_id}")
    builder.adjust(2)
    return builder.as_markup()

# === АДМИН ПАНЕЛЬ ===
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def cmd_admin_panel(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎲 Фейкпуб", callback_data="admin_fake")
    builder.button(text="🔒 Закрыть чат", callback_data="admin_close")
    builder.button(text="🔓 Открыть чат", callback_data="admin_open")
    builder.adjust(1)
    await message.answer("🛠 <b>Панель управления каналом:</b>", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_fake", F.from_user.id == ADMIN_ID)
async def cb_admin_fake(callback: types.CallbackQuery):
    if not FAKE_POSTS:
        await callback.answer("❌ База фейков пуста!", show_alert=True)
        return
        
    fake_text = random.choice(FAKE_POSTS)
    FAKE_POSTS.remove(fake_text)
    
    signature = '\n\n<a href="https://t.me/LoveUgoZapad">Признания Юго-Западная</a>'
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=fake_text + signature, parse_mode="HTML")
        await callback.answer(f"✅ Фейк опубликован! Осталось: {len(FAKE_POSTS)}", show_alert=True)
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data == "admin_close", F.from_user.id == ADMIN_ID)
async def cb_admin_close(callback: types.CallbackQuery):
    try:
        await bot.set_chat_permissions(chat_id=GROUP_ID, permissions=ChatPermissions(can_send_messages=False))
        await callback.answer("🔒 Комментарии закрыты!", show_alert=True)
    except Exception:
        await callback.answer("Ошибка! Проверь GROUP_ID и права бота.", show_alert=True)

@dp.callback_query(F.data == "admin_open", F.from_user.id == ADMIN_ID)
async def cb_admin_open(callback: types.CallbackQuery):
    try:
        await bot.set_chat_permissions(chat_id=GROUP_ID, permissions=ChatPermissions(can_send_messages=True, can_send_photos=True, can_send_videos=True, can_send_other_messages=True))
        await callback.answer("🔓 Комментарии открыты!", show_alert=True)
    except Exception:
        await callback.answer("Ошибка! Проверь GROUP_ID и права бота.", show_alert=True)


# === СТАРТ И ИНСТРУКЦИЯ ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🎙 <b>Привет! Это предложка канала Признания Юго-Западная.</b>\n\n"
        "Скидывай сюда:\n"
        "• Текст или фото с историей\n"
        "• 🎙 <b>Голосовое сообщение</b>\n"
        "• 📹 <b>Видеокружок</b> (запиши сторис из жизни района!)\n"
        "• Валентинку через команду /love [текст]\n\n"
        "Всё публикуется анонимно после модерации.",
        parse_mode="HTML"
    )

# === ВАЛЕНТИНКИ ===
@dp.message(Command("love"))
async def send_valentine(message: types.Message):
    user_text = message.text or message.caption or ""
    clean_text = user_text.replace("/love", "").strip()
    
    if not clean_text and not message.photo:
        await message.answer("Напиши текст валентинки после команды.\nПример: /love Девочка в белом пуховике, ты супер!")
        return
        
    valentine_text = (
        "💌 <b>АНОНИМНАЯ ВАЛЕНТИНКА</b> 💌\n\n"
        f"<i>{clean_text}</i>\n\n"
        '<a href="https://t.me/LoveUgoZapad">Признания Юго-Западная</a>'
    )
    
    try:
        if message.photo:
            await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=valentine_text, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=valentine_text, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
        await message.answer("Твоя валентинка улетела на модерацию! ❤️")
    except Exception:
        await message.answer("Произошла ошибка при отправке.")

# === ОБРАБОТКА ГОЛОСОВЫХ ===
@dp.message(F.voice)
async def handle_voice(message: types.Message):
    if message.voice.duration > 90:
        await message.answer("⚠️ Голосовое слишком длинное! Запиши историю короче (до 1.5 минут).")
        return

    voice_caption = (
        "🎙 <b>АНОНИМНОЕ ГОЛОСОВОЕ</b> 🎙\n\n"
        '<a href="https://t.me/LoveUgoZapad">Признания Юго-Западная</a>'
    )
    
    try:
        await bot.send_voice(
            chat_id=ADMIN_ID,
            voice=message.voice.file_id,
            caption=voice_caption,
            parse_mode="HTML",
            reply_markup=get_admin_kb(message.chat.id)
        )
        await message.answer("🎙 Твое голосовое отправлено на модерацию!")
    except Exception:
        await message.answer("Произошла ошибка при отправке голосового.")

# === ОБРАБОТКА ВИДЕОКРУЖКОВ ===
@dp.message(F.video_note)
async def handle_video_note(message: types.Message):
    try:
        # Сначала шлем сам кружок админу
        await bot.send_video_note(
            chat_id=ADMIN_ID,
            video_note=message.video_note.file_id,
            reply_markup=get_admin_kb(message.chat.id)
        )
        # Отдельным сообщением шлем подпись-ссылку для канала (так как у кружков в телеграме нет текста-описания)
        await bot.send_message(
            chat_id=ADMIN_ID,
            text='<a href="https://t.me/LoveUgoZapad">Признания Юго-Западная</a>',
            parse_mode="HTML"
        )
        await message.answer("📹 Твой кружок отправлен на модерацию!")
    except Exception as e:
        await message.answer(f"Произошла ошибка при отправке кружка: {e}")

# === ОБРАБОТКА ТЕКСТА И ФОТО ===
@dp.message(F.content_type.in_({'text', 'photo'}))
async def handle_suggestion(message: types.Message):
    signature = '\n\n<a href="https://t.me/LoveUgoZapad">Признания Юго-Западная</a>'
    user_text = message.html_text or ""
    
    try:
        if message.photo:
            await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=user_text + signature, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=user_text + signature, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
        await message.answer("Твое сообщение улетело на модерацию!")
    except Exception:
        await message.answer("Произошла ошибка при отправке.")

@dp.message()
async def handle_wrong_formats(message: types.Message):
    await message.answer("Я принимаю только текст, фото, голосовые и видеокружки.")

# === КНОПКИ МОДЕРАЦИИ ===
@dp.callback_query(F.data.startswith("pub_"))
async def cb_publish(callback: types.CallbackQuery):
    _, user_id = callback.data.split("_")
    try:
        # Если это был кружок, админу пришло два сообщения (кружок + подпись). 
        # Но для простоты публикации кружков с подписью лучше публиковать их в связке или через копирование.
        await bot.copy_message(chat_id=CHANNEL_ID, from_chat_id=ADMIN_ID, message_id=callback.message.message_id, reply_markup=None)
        
        kb = InlineKeyboardBuilder()
        kb.button(text="Опубликовано ✅", callback_data="done")
        await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
        await callback.answer("Успешно отправлено в канал!")
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
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
