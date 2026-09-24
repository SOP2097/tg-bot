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
GROUP_ID =  -1003993560990  # <--- Не забудь поменять на реальный ID чата с комментариями

# === БАЗА ФЕЙКОВЫХ ПОСТОВ (100 штук) ===
FAKE_POSTS = [
    "ищу парня который сегодня в столовой на 3 этаже уронил вилку и смешно выругался. ты был в сером свитшоте найдись",
    "девочка с каре и красными прядями стояла возле автоматов с кофе на первом этаже около 14:00. ты очень красивая дай инст",
    "сегодня утром на выходе из метро кто-то из наших помогал бабушке поднять сумку. высокий с темными волосами. респект тебе",
    "понравилась девушка на лекции по праву у перваков (сидела на 3 ряду). ты всё время рисовала в тетрадке отзовись пж",
    "парень с проколотой губой и кольцами на пальцах, курил у 6 корпуса где-то в час дня. найдись",
    "парень сидел сегодня в зоне отдыха в наушниках маршал и черной кожанке. отпиши в коменты",
    "21.09. девчонка в широких джинсах и огромном зеленом худи, мы столкнулись в дверях 2 корпуса. сорри еще раз",
    "парень из 3 группы фнн, который сегодня отвечал у доски, у тебя очень красивый голос",
    "ищу девочку блондинку с голубыми глазами, были сегодня на одном потоке в 315 ауд. на тебе был еще розовый шарф",
    "ребята с юрфака которые вчера громко обсуждали доту в коридоре 4 этажа, можно с вами как-нибудь сыграть?",
    "парень в бежевом пальто и круглых очках, спускался по лестнице в главном здании часов в 11. выглядишь очень атмосферно",
    "девушка с татуировкой змеи на ключице, стояла в очереди в гардероб, мы переглянулись. найдись",
    "кто потерял черный картхолдер тинькофф возле библиотеки? отдал охраннику",
    "ищу типа который на паре по макре сегодня уснул на задней парте. понимаю тебя",
    "девочка с веснушками в желтом свитере, ты покупала булочку на перемене. у тебя красивая улыбка",
    "парень который вчера около 16:30 стоял на остановке возле уника под зонтом. был в черных конверсах. найдись",
    "понравился мальчик, высокий, светлые волосы, был в синей ветровке. играл в теннис на физре сегодня",
    "девчонки с 1 курса дизайна, вы очень стильно одеваетесь",
    "парень со скейтом, проехал мимо меня у главного входа примерно в 10 утра.",
    "девушка в черном платье и грубых ботинках на шнуровке, сидела на подоконнике на 2 этаже. отзовись если свободна",
    "парень с рюкзаком ванс, ты сегодня споткнулся на лестнице и сделал вид что так и задумано. забавно вышло",
    "ищу девочку в наушниках эпл макс, видела тебя в очереди за кофе. ты была в бежевом тренче",
    "парень из ибда который всегда ходит в костюмах тройках. выглядит очень круто",
    "девочка в розовом шарфе, шли сегодня вместе от метро к универу. ты очень милая",
    "кто тот парень брюнет из 12 группы который постоянно шутит на семинарах?",
    "парень в футболке с принтом евангелиона, стоял у расписания на 1 этаже. давай общаться",
    "девушка со стаканчиком кофе, стояла сегодня возле вкусно и точка на южке примерно в 15:00. была в черной куртке, найдись",
    "парень который сегодня на физре забил трехочковый в самом конце. хорош",
    "ищу парня, глаза карие, волосы немного вьются, был в серой зипке. стоял курил возле курилки с высоким другом",
    "девчонка в белых брюках карго и черном топе, были на совместной лекции по истории. ты постоянно крутила ручку",
    "мальчик с гитарой который сидел на пуфиках в коворкинге, очень красиво играл",
    "девушка с красной помадой и в черном берете, видела тебя в столовой. очень эстетично выглядишь",
    "парни с 4 курса фмб, спасибо что помогли найти нужную аудиторию сегодня первашу",
    "ищу девочку, темные волосы по плечи, была в рубашке в клетку оверсайз. сидели рядом в читальном зале",
    "молодой человек в белых джорданах и кепке, стоял сегодня у банкомата. ты оч стильный",
    "девушка в зеленом кардигане, ты сегодня выронила пропуск на турникетах, я тебе его подал.",
    "парень с пирсингом брови из 8 группы, найдись",
    "девчонка с длинными русыми волосами, была в джинсовке. шла сегодня от авеню в сторону 5 корпуса примерно в 15:30",
    "парень в футболке slipknot найдись, я тоже их слушаю",
    "ищу парня в черном худи с капюшоном, ты сидел на лавочке перед универом и пил энергетик",
    "девочка в черной юбке в складку и белых гольфах. видела тебя на перемене, выглядишь супер",
    "парень который сегодня на паре по вышмату решал судоку в телефоне.",
    "девушка с рыжими кудряшками, мы вместе ехали в лифте на 6 этаж. у тебя классный парфюм",
    "мальчики из 2 корпуса которые сегодня пели макса коржа на весь хор, подняли настроение",
    "ищу парня с тату паутины на локте, видел тебя в курилке.",
    "девчонка в леопардовых штанах, которая сегодня громко разговаривала по телефону возле деканата.",
    "парень с хвостиком на голове, в черной водолазке. стоял у автомата с едой на 2 этаже. отзовись",
    "девушка в очках авиаторах и кожаном плаще, выглядишь очень стильно",
    "ищу парня из команды по волейболу, номер 7 вроде. круто играешь",
    "девочка с розовым рюкзаком канкен, ты забыла тетрадь по инглишу в 412 аудитории, я отнесла на кафедру",
    "парень в сером пальто и белом шарфе, ты сегодня смотрел на меня в метро а потом вышел на станции юго-западная и пошел к универу. найдись",
    "девушка с челкой и в черном чокере, сидела в телефоне возле 3 аудитории.",
    "парень который гоняет на электросамокате в желтой куртке, будь осторожнее, чуть не сбил сегодня",
    "ищу девочку в синем худи с надписью GAP, ты сегодня покупала двойной капучино",
    "парень с кудряшками из 1 курса журналистики. ты очень харизматичный",
    "девчонка в белых кроссах на высокой платформе, выглядит очень необычно",
    "молодой человек в очках, сидел на 1 парте на философии. ты очень интересно спорил с преподавателем",
    "девушка с зеленым шоппером, на котором нарисован лягушонок.",
    "ищу парня который сегодня в гардеробе отдал мне свою куртку без очереди. спасибо тебе",
    "девчонки из танцевальной сборной, вы вчера на репетиции были супер. удачи на выступлении",
    "парень в спортивках адидас и черной панаме, стоял на крыльце 4 корпуса.",
    "девушка в розовом пуховике, мы с тобой столкнулись глазами на эскалаторе.",
    "парень из 5 группы ит, который всегда ходит с термосом.",
    "ищу девочку с короткими светлыми волосами, была в черной водолазке и серебряной цепочке.",
    "мальчик в рубашке с драконами, ты сидел сегодня в коворкинге за ноутом.",
    "девушка с пирсингом септума и в берцах, видела тебя в курилке 2 корпуса.",
    "парень который сегодня читал стихи на литературе. очень красиво",
    "ищу парня с синими прядями в волосах, был в джинсовой куртке с нашивками.",
    "девочка в бежевом тренче и с шелковым платком на шее, очень красиво выглядишь",
    "парень который сегодня переходил проспект вернадского в сторону академии около 9:40. был в черном пальто и с кожаным портфелем. отзовись",
    "девушка с татуировкой бабочки на руке, стояла сегодня в очереди за пиццей в столовой.",
    "парень в черной рубашке расстегнутой на пару пуговиц, ты проходил мимо 210 кабинета примерно в 14:20.",
    "девчонка с дредокудрями, ты сегодня сидела на лавочке в сквере.",
    "парень с сумкой мессенджером через плечо, постоянно вижу тебя в коридорах.",
    "ищу девушку из 2 группы фмп, ты сегодня была в красивом красном платье на парах.",
    "парень в футболке с риком и морти, мы переглянулись возле расписания.",
    "девочка с пучком на голове и в очках для зрения, ты мило морщила нос когда читала конспект",
    "парень из студсовета который сегодня бегал с документами по 1 этажу.",
    "ищу девушку в серых спортивных штанах и белом топе, мы вместе бегали на физре в тропаревском парке сегодня. ты быстро бегаешь",
    "мальчик с веснушками и русыми волосами, ты сегодня покупал воду в автомате",
    "девчонка в черном корсете поверх белой рубашки, очень стильный образ",
    "парень с бородой и в клетчатой рубашке, ты сидел в библиотеке за 3 столом.",
    "девушка с розовым маникюром, мы вместе сидели на задней парте на экономике.",
    "ищу парня который сегодня играл на пианино в актовом зале.",
    "парень который стоял на остановке возле мирэа и ждал автобус. ты был в наушниках и бордовой толстовке. найдись",
    "девочка с сережками в виде вишен, стояла сегодня возле деканата и грустила. не грусти",
    "парень в кожаной куртке и с гитарным чехлом за спиной, ты заходил в 5 корпус в 9 утра.",
    "девушка в синих джинсах клеш и белом кроп топе, видела тебя возле зеркала на 2 этаже.",
    "ищу парня из 7 группы, ты всегда ходишь в наушниках.",
    "девчонка с гетерохромией (разные глаза), видела тебя на лекции потока. очень необычно",
    "парень который сегодня на матане задал смешной вопрос преподу.",
    "девушка в пушистом белом свитере, видела тебя на фудкорте в авеню после пар. ты сидела с подругой",
    "парень с кольцом на большом пальце и татуировкой на шее, стоял курил возле главного входа в 15:40. отзовись",
    "ищу девочку в черной юбке карандаш и красных туфлях, ты сегодня защищала проект на семинаре. выступила отлично",
    "мальчик в белом худи трешер, ты сегодня смеялся над чем-то в телефоне на паре.",
    "девчонка с зелеными стрелками, ты сидела сегодня на подоконнике 3 этажа. красивый макияж",
    "парень который сегодня помогал носить стулья в актовом зале.",
    "ищу девушку с черным рюкзаком со значками, мы ехали вместе в автобусе до универа.",
    "парень в синем спортивном костюме, ты сегодня подтянулся на турнике на физре 20 раз.",
    "девочка которая сегодня плакала на лестнице запасного выхода, надеюсь у тебя все наладилось"
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
        await callback.answer("❌ База фейков полностью исчерпана!", show_alert=True)
        return
        
    fake_text = random.choice(FAKE_POSTS)
    FAKE_POSTS.remove(fake_text)
    
    signature = '\n\n<a href="https://t.me/LoveUgoZapad">Признания Юго-Западная</a>'
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=fake_text + signature, parse_mode="HTML")
        await callback.answer(f"✅ Опубликовано! Осталось в базе: {len(FAKE_POSTS)} шт.", show_alert=True)
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data == "admin_close", F.from_user.id == ADMIN_ID)
async def cb_admin_close(callback: types.CallbackQuery):
    try:
        await bot.set_chat_permissions(chat_id=GROUP_ID, permissions=ChatPermissions(can_send_messages=False))
        await callback.answer("🔒 Комментарии закрыты!", show_alert=True)
    except Exception:
        await callback.answer("Ошибка! Проверь GROUP_ID и права бота в группе.", show_alert=True)

@dp.callback_query(F.data == "admin_open", F.from_user.id == ADMIN_ID)
async def cb_admin_open(callback: types.CallbackQuery):
    try:
        await bot.set_chat_permissions(chat_id=GROUP_ID, permissions=ChatPermissions(can_send_messages=True, can_send_photos=True, can_send_videos=True, can_send_other_messages=True))
        await callback.answer("🔓 Комментарии открыты!", show_alert=True)
    except Exception:
        await callback.answer("Ошибка! Проверь GROUP_ID и права бота в группе.", show_alert=True)

# === СТАРТ И ИНСТРУКЦИЯ ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🎙 <b>Привет! Это предложка канала Признания Юго-Западная.</b>\n\n"
        "Скидывай сюда:\n"
        "• Текст или фото с историей\n"
        "• 🎙 <b>Голосовое сообщение</b>\n"
        "• 📹 <b>Видеокружок</b>\n"
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

# === ГОЛОСОВЫЕ ===
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

# === ВИДЕОКРУЖКИ ===
@dp.message(F.video_note)
async def handle_video_note(message: types.Message):
    try:
        await bot.send_video_note(
            chat_id=ADMIN_ID,
            video_note=message.video_note.file_id,
            reply_markup=get_admin_kb(message.chat.id)
        )
        await bot.send_message(
            chat_id=ADMIN_ID,
            text='<a href="https://t.me/LoveUgoZapad">Признания Юго-Западная</a>',
            parse_mode="HTML"
        )
        await message.answer("📹 Твой кружок отправлен на модерацию!")
    except Exception as e:
        await message.answer(f"Произошла ошибка при отправке кружка: {e}")

# === ТЕКСТ И ФОТО ===
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
