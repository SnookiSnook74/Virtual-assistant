import openai
import os
from pathlib import Path
import pygame
import speech_recognition as sr
import time

# Инициализация клиента OpenAI
client = openai.OpenAI()

# ID вашего существующего ассистента
assistant_id = "asst_eLBvtpsZEOqhdmmmlP8ltdkW"

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
        #audio = recognizer.record(source, duration=5)
        print("Обработка сообщения")
        try:
            user_input = recognizer.recognize_google(audio, language="ru-RU")
        except sr.UnknownValueError:
            print("Google Web Speech API не понял аудио")
            continue
        except sr.RequestError as e:
            print(f"Не удалось получить результаты от Google Web Speech API; {e}")
            break

        if user_input.lower() == 'выход':
            break

        # Добавление сообщения пользователя в поток
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
            #content="Привет Тая!"
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
        print(assistant_reply)
        # assistant

        # Создание аудио речи с помощью API
        answer = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=assistant_reply
            #input="Во что ты хочешь поиграть?"
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
