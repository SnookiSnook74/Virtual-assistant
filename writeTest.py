import openai
from openai import OpenAI
import time

# Инициализация клиента OpenAI
client = OpenAI()
# ID вашего существующего ассистента
assistant_id = "asst_eLBvtpsZEOqhdmmmlP8ltdkW"
# Получение существующего ассистента
assistant = client.beta.assistants.retrieve(assistant_id=assistant_id)
# Создание нового потока для каждого диалога
thread = client.beta.threads.create()

while True:
    user_input = input("Введите ваш вопрос (или 'выход' для завершения): ")
    if user_input.lower() == 'выход':
        break
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
        elif run_status.status != 'in_progress':
            print(f"Неожиданный статус запуска: {run_status.status}")
            break
        time.sleep(2)

    # Получение и вывод последнего сообщения ассистента
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    print(f" Content: {messages.data[0].content[0].text.value}")
