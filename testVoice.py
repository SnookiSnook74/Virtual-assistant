import openai
import os
from pathlib import Path
import pygame
import speech_recognition as sr
import time

# Инициализация клиента OpenAI
client = openai.OpenAI()

# ID вашего существующего ассистента
assistant_id = "asst_UOX6CjnhKf24xdLAI3B94iMY"

# Получение существующего ассистента
assistant = client.beta.assistants.retrieve(assistant_id=assistant_id)

# Создание нового потока для каждого диалога
thread = client.beta.threads.create()

# Инициализация pygame
pygame.init()

# Создаем объект распознавателя
recognizer = sr.Recognizer()

while True:
    # Используем микрофон для захвата речи
    with sr.Microphone() as source:
        print("Говорите...")
        audio = recognizer.listen(source)
                # Сохраняем аудио в файл
        audio_file_path = "temp_audio.wav"
        with open(audio_file_path, "wb") as f:
            f.write(audio.get_wav_data())

        # Отправляем аудиофайл в OpenAI для транскрипции
        with open(audio_file_path, "rb") as audio_file:
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

        # Запуск ассистента для обработки запроса в потоке
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
        response_file_path = Path(__file__).parent / "response.mp3"
        answer.stream_to_file(response_file_path)

        # Воспроизведение аудиофайла
        pygame.mixer.music.load(response_file_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        # Удаление аудиофайла после воспроизведения
        os.remove(response_file_path)
