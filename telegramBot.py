from telegram.ext import Updater, MessageHandler, CommandHandler
from telegram import Bot
from telegram.ext import Filters
from pathlib import Path
import openai
from openai import OpenAI
from pydub import AudioSegment
from telegram import ChatAction
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
import base64
import requests

import time
import os

assistants = {
    "Персональный Ассистент": "asst_UOX6CjnhKf24xdLAI3B94iMY",
    "Учитель Английского": "asst_eLBvtpsZEOqhdmmmlP8ltdkW",
    "Ассистент по программированию": "asst_TA9ey4rIYHGpcJQzjyhrSr7F"
    
}
# Глобальный словарь для хранения текущего ID ассистента каждого пользователя
user_assistants = {}
 # Глобальный словарь для хранения потоков
user_threads = {} 
# Словарь для хранения количества запросов каждого пользователя
user_requests_count = {} 
MY_TELEGRAM_ID = '319761502'
# Список разрешенных User ID
ALLOWED_USER_IDS = ['319761502', 'ID_2', 'ID_3']
# Максимальное количество разрешенных запросов
MAX_REQUESTS_PER_USER = 5
# Токен вашего бота
TOKEN = '1234066681:AAFchJJx9RxHxWeYSGYvt646o3Bab1b8O9s'
# Инициализация клиента OpenAI
client = OpenAI()
# Создаем экземпляр бота и диспетчера
bot = Bot(token=TOKEN)

def is_user_allowed(update, context):
    user_id = str(update.effective_user.id)
    if user_id not in ALLOWED_USER_IDS:
        update.message.reply_text("Извините, у вас нет доступа к этому боту.")
        return False  # Пользователь не в списке разрешенных
    return True  # Пользователь в списке разрешенных

# Пока не используется(возможно при расширении бота буду вводить ограничения)
def is_request_allowed(user_id):
    # Проверяем, является ли пользователь владельцем бота
    if user_id == MY_TELEGRAM_ID:
        return True  # Владелец бота может делать неограниченное количество запросов
    # Увеличиваем счётчик запросов или устанавливаем его в 1, если это первый запрос
    user_requests_count[user_id] = user_requests_count.get(user_id, 0) + 1
    # Проверяем, не превышено ли максимальное количество запросов
    if user_requests_count[user_id] > MAX_REQUESTS_PER_USER:
        return False  # Превышено максимальное количество запросов
    return True  # Всё в порядке, запрос разрешен


# Функция для изменения ассистента
def change_assistant(update, context):
    chat_id = update.message.chat_id
    current_assistant = user_assistants.get(chat_id)
    # Отправка сообщения с выбором ассистентов
    buttons = [[InlineKeyboardButton(text=name + (" ✅" if assistants[name] == current_assistant else ""), callback_data=name)] for name in assistants.keys()]
    reply_markup = InlineKeyboardMarkup(buttons)
    update.message.reply_text('Выберите ассистента:', reply_markup=reply_markup)

    
# Обработчик колбэков от кнопок
def button(update, context):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id
    selected_assistant = query.data
    if selected_assistant in assistants:
        # Устанавливаем нового ассистента и обновляем клавиатуру, чтобы отобразить выбор
        user_assistants[chat_id] = assistants[selected_assistant]
        # Сбрасываем поток (и, следовательно, контекст)
        if chat_id in user_threads:
            del user_threads[chat_id]
        # Создаем клавиатуру с галочкой на выбранном ассистенте
        buttons = [[InlineKeyboardButton(text=name + (" ✅" if assistants[name] == user_assistants[chat_id] else ""), callback_data=name)] for name in assistants.keys()]
        reply_markup = InlineKeyboardMarkup(buttons)
        # Отправляем подтверждение пользователю с обновленной клавиатурой
        query.edit_message_text(text='Выберите ассистента:', reply_markup=reply_markup)
    else:
        query.edit_message_text(text="Ошибка: неверный выбор ассистента.")

# Создание потока для каждого пользователя
def get_user_thread(chat_id):
    # Убедитесь, что для каждого пользователя существует поток
    if chat_id not in user_threads:
        user_threads[chat_id] = client.beta.threads.create()
    return user_threads[chat_id]

# Возвращает ID ассистента для пользователя, или использует ассистента по умолчанию
def get_user_assistant_id(chat_id):
    return user_assistants.get(chat_id, "asst_UOX6CjnhKf24xdLAI3B94iMY")

# Функция для генерации изображения
def generate_image(prompt):
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    return image_url

# Функция обработки текстовых сообщений
def handle_text(update, context):
    if not is_user_allowed(update, context):
        return  # Прекращаем обработку, если пользователь не в списке разрешенных
    chat_id = update.message.chat_id
    # Получение и обработка текстового сообщения
    received_text = update.message.text.lower()
    if received_text.startswith("нарисуй "):
                # Извлеките подсказку для DALL-E из текста сообщения
        prompt = received_text.replace("нарисуй", "").strip()
        image_url = generate_image(prompt)
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url)
        return
    thread = get_user_thread(chat_id)
    assistant_id = get_user_assistant_id(chat_id)
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
        if messages.data[0].role == "assistant":
            context.bot.send_message(chat_id=update.effective_chat.id, text=response_text)
    else:
        # Отправка сообщения об ошибке, если ответ отсутствует
        context.bot.send_message(chat_id=update.effective_chat.id, text="Извините, не смог обработать ваш запрос.")

# Функция обработки голосовых сообщений
def handle_voice(update, context):
    if not is_user_allowed(update, context):
        return  # Прекращаем обработку, если пользователь не в списке разрешенных
    chat_id = update.message.chat_id
    thread = get_user_thread(chat_id)
    assistant_id = get_user_assistant_id(chat_id)
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

# Функция для загрузки изображения на Imgbb и получения URL
def upload_image_to_imgbb(image_path, api_key):
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": api_key,
                "image": encoded_image,
            }
        )
    response_json = response.json()
    return response_json['data']['url']

# Обработчик изображений
def handle_photo(update, context):
    if not is_user_allowed(update, context):
        return  # Прекращаем обработку, если пользователь не в списке разрешенных
    chat_id = update.message.chat_id
    photo_file = update.message.photo[-1].get_file()
    local_image_path = f"{chat_id}_image.jpg"
    photo_file.download(local_image_path)
    
    # Загрузка изображения на Imgbb и получение URL
    imgbb_api_key = "af108b41e9bf6ed74a72b37e4eadf883"
    image_url = upload_image_to_imgbb(local_image_path, imgbb_api_key)

    # Отправка URL в OpenAI и получение ответа
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Что на фото? Давай описание максимально подробно"},
                    {"type": "image_url", "image_url": image_url},
                ],
            }
        ],
        max_tokens=300,
    )
    response_text = response.choices[0].message.content

    # Получение потока пользователя
    thread = get_user_thread(chat_id)

# Добавление ответа в поток для сохранения контекста
    response_message = "Ответ GPT на изображение: " + response_text
    client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content=response_message  # Теперь передаем строку, а не словарь
)
    # Отправка ответа пользователю
    context.bot.send_message(chat_id=chat_id, text=response_text)


# Удалить контекст
def delete_context(update, context):
    chat_id = update.message.chat_id
    if chat_id in user_threads:
        # Удаляем существующий поток
        del user_threads[chat_id]
    update.message.reply_text("Ваш контекст был сброшен.")


def start(update, context):
    start_message = (
        "👋 Привет! Я — твой персональный ассистент-бот. Вот что я умею:\n\n"
        "👁️‍🗨️ Визуальные и аудио функции:\n"
        "   • Я могу видеть и слышать! Отправь мне аудиосообщение, и я отвечу голосом.\n"
        "   • Пришли мне фото или картинку, и я расскажу, что на ней изображено.\n"
        "   • Напиши 'Нарисуй' в начале предложения, и я создам картинку по твоему описанию.\n\n"
        "🔹 Управление задачами и напоминаниями:\n"
        "   • Могу помочь тебе организовать задачи и не забыть о важных делах. 📅\n\n"
        "🔹 Интеллектуальные функции:\n"
        "   • Отвечаю на вопросы различной сложности. 💡\n"
        "   • Поддерживаю беседу на разные темы. 🗣️\n"
        "   • Обучаю английскому языку с помощью второго ассистента. 🇬🇧\n\n"
        "🔄 Управление ботом:\n"
        "   • Чтобы изменить ассистента, используй команду /change_assistant.\n"
        "   • Если хочешь сбросить контекст разговора, используй /delete_context.\n\n"
        "🚀 Давай начнем! Используй мои функции и получай максимум пользы."
    )
    update.message.reply_text(start_message)



def main():
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Добавляем обработчики для текстовых и голосовых сообщений
    dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_text))
    dispatcher.add_handler(MessageHandler(Filters.voice, handle_voice))
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_photo))
    dispatcher.add_handler(CommandHandler("delete_context", delete_context))
    dispatcher.add_handler(CommandHandler("change_assistant", change_assistant))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(CommandHandler("start", start))

    # Начинаем поиск обновлений
    updater.start_polling()

if __name__ == '__main__':
    main()