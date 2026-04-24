import telebot
from telebot import types
from config import TOKEN
from logic import *
import speech_recognition as sr
from pydub import AudioSegment
import os 
import time
bot = telebot.TeleBot(TOKEN)
init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OGG_PATH = "voice.ogg"
WAV_PATH = "voice.wav"


def faq_keyboard():
    """Меню с вопросами FAQ."""
    markup = types.ReplyKeyboardMarkup(row_width=1)
    for qid, data in FAQ.items():
        markup.add(types.KeyboardButton(
            text=f" {data['question']}",
            callback_data=f"faq_{qid}",
        ))
    return markup
 
 
def back_keyboard():
    """Кнопка «Назад» к меню."""
    markup = types.ReplyKeyboardMarkup(row_width=1)
    markup.add(types.KeyboardButton("<-- Вернуться к вопросам"))
    return markup

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user
    add_user(user.id, user.full_name)
 
    bot.send_message(
        message.chat.id,
        (
            f"Привет, {user.first_name}!\n\n"
            "Я бот-ассистент магазина *«Продадим всё на свете»*.\n"
            "Выберите интересующий вас вопрос — и я отвечу мгновенно \n"
            "Для того, чтобы разобраться в боте можете нажать /help"
        ),
        parse_mode="Markdown",
        reply_markup=faq_keyboard(),
    )
 
@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        (
            "Как пользоваться ботом:\n\n"
            "Нажмите на кнопку с нужным вопросом — получите ответ.\n"
            "Напишите /start в любой момент, чтобы вернуться к списку вопросов.\n"
            "Если вы отправите голосовое сообщение — я сохраню его и перенаправлю в меню.\n\n"
            "По всем вопросам, которых нет в списке, обращайтесь к живому оператору через сайт."
        ),
        parse_mode="Markdown",
        reply_markup=faq_keyboard(),
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("faq_"))
def handle_faq_callback(call):
    qid = int(call.data.split("_")[1])
    answer = get_answer(qid)
 
    if not answer:
        bot.answer_callback_query(call.id, "Ответ не найден ")
        return
    question_text = FAQ[qid]["question"]
    log_request(call.from_user.id, "faq", question_id=qid, raw_text=question_text)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f" *{question_text}*\n\n{answer}",
        parse_mode="Markdown",
        reply_markup=back_keyboard(),
    )
    bot.answer_callback_query(call.id)
 
 
@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def handle_back(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="📋 Выберите вопрос:",
        reply_markup=faq_keyboard(),
    )
    bot.answer_callback_query(call.id)


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    try:
        # Скачиваем файл
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with open(OGG_PATH, "wb") as f:
            f.write(downloaded_file)

        if not os.path.exists(OGG_PATH):
            bot.reply_to(message, "Ошибка: не удалось сохранить голосовое сообщение.")
            return

        # Конвертируем ogg → wav
        audio = AudioSegment.from_ogg(OGG_PATH)
        audio.export(WAV_PATH, format="wav")

        if not os.path.exists(WAV_PATH):
            bot.reply_to(message, "Ошибка: не удалось конвертировать аудио.")
            return

        # Распознаём речь
        r = sr.Recognizer()
        with sr.AudioFile(WAV_PATH) as source:
            audio_data = r.record(source)

        try:
            text = r.recognize_google(audio_data, language="ru-RU")
            bot.reply_to(message, f"Распознанный текст: {text}")
            log_request(message.from_user.id, "voice", raw_text=text)
        except sr.UnknownValueError:
            bot.reply_to(message, "Не удалось распознать голосовое сообщение.")
        except sr.RequestError as e:
            bot.reply_to(message, f"Ошибка сервиса распознавания: {e}")

    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {e}")
        print(f"[handle_voice] Ошибка: {e}")
    finally:
        # Удаляем временные файлы
        for path in [OGG_PATH, WAV_PATH]:
            if os.path.exists(path):
                os.remove(path)
    
@bot.message_handler(content_types=["text"])
def handle_text(message):
    text = message.text.strip()
    add_user(message.from_user.id, message.from_user.full_name)
    matched_id = _find_matching_faq(text)
    if matched_id:
        answer = get_answer(matched_id)
        question_text = FAQ[matched_id]["question"]
        log_request(message.from_user.id, "text", raw_text=text)
        bot.send_message(
            message.chat.id,
            f"Похоже, ваш вопрос похож на: *{question_text}*\n\n{answer}",
            parse_mode="Markdown",
            reply_markup=faq_keyboard(),
        )
    else:
        bot.send_message(
            message.chat.id,
            "Спасибо за ваше сообщение! Я передал его оператору, и он свяжется с вами в ближайшее время.",
            reply_markup=faq_keyboard(),
        )        

def _find_matching_faq(text: str) -> int | None:
    text_lower = text.lower()
    keywords = {
        1: ["оформить заказ", "как заказать", "купить", "корзина"],
        2: ["статус", "где мой заказ", "отслеживание"],
        3: ["отменить", "отмена заказа"],
        4: ["поврежден", "повреждён", "сломан", "брак", "пришел плохой"],
        5: ["поддержка", "связаться", "контакт", "телефон"],
        6: ["доставка", "сроки", "курьер", "привезут"],
    }
    for qid, words in keywords.items():
        if any(kw in text_lower for kw in words):
            return qid
    return None


if __name__ == "__main__":
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    bot.infinity_polling()
