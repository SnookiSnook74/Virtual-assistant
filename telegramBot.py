from telegram.ext import Updater, MessageHandler, CommandHandler
from telegram import Bot
from telegram.ext import Filters
from pathlib import Path
import openai
from openai import OpenAI
from pydub import AudioSegment
from telegram import ChatAction

import time
import os

# Токен вашего бота, полученный от BotFather
TOKEN = '1234066681:AAFchJJx9RxHxWeYSGYvt646o3Bab1b8O9s'

# Инициализация клиента OpenAI
client = OpenAI()
# ID вашего существующего ассистента
assistant_id = "asst_eLBvtpsZEOqhdmmmlP8ltdkW"
# Получение существующего ассистента
assistant = client.beta.assistants.retrieve(assistant_id=assistant_id)
# Создание нового потока для каждого диалога
thread = client.beta.threads.create()

# Создаем экземпляр бота и диспетчера
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Функция обработки текстовых сообщений
def handle_text(update, context):
    # Получение и обработка текстового сообщения
    received_text = update.message.text
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=received_text
    )
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if run_status.status == 'completed':
            break
        elif run_status.status != 'in_progress':
            print(f"Неожиданный статус запуска: {run_status.status}")
            break
        time.sleep(3)
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    # Проверка, есть ли сообщения для отправки
    if messages.data:
        # Получение текста последнего сообщения от OpenAI
        response_text = messages.data[0].content[0].text.value
        # Отправка сообщения обратно пользователю в Telegram
        context.bot.send_message(chat_id=update.effective_chat.id, text=response_text)
    else:
        # Отправка сообщения об ошибке, если ответ отсутствует
        context.bot.send_message(chat_id=update.effective_chat.id, text="Извините, не смог обработать ваш запрос.")


# Функция обработки голосовых сообщений
def handle_voice(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Получил ваше голосовое сообщение, готовлю ответ...")
    # Получение голосового сообщения
    voice_file = update.message.voice.get_file()
    file_path = 'voice_message.ogg'
    voice_file.download(file_path)
        # Конвертация Ogg в WAV
    ogg_version = AudioSegment.from_file(file_path, format="ogg")
    wav_path = 'voice_message.wav'
    ogg_version.export(wav_path, format="wav")
            # Отправляем аудиофайл в OpenAI для транскрипции
    with open(wav_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file, 
                response_format="text"
            )
            user_input = transcript
        # Добавление сообщения пользователя в поток
    message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )
    run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )
            # Ожидание завершения запуска
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
            )
        if run_status.status == 'completed':
            break
        time.sleep(2)

        # Получение и вывод последнего сообщения ассистента
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    assistant_reply = messages.data[0].content[0].text.value
    print(assistant_reply)
        # Создание аудио речи с помощью API
    answer = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=assistant_reply
        )
    # Сохранение аудиофайла ответа GPT
    response_file_path = "response.mp3"
    answer.stream_to_file(response_file_path)
    # Отправка аудиофайла обратно в чат
    with open(response_file_path, 'rb') as audio_file:
        context.bot.send_audio(chat_id=update.effective_chat.id, audio=audio_file)

    
# Добавляем обработчики для текстовых и голосовых сообщений
dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_text))
dispatcher.add_handler(MessageHandler(Filters.voice, handle_voice))

# Начинаем поиск обновлений
updater.start_polling()