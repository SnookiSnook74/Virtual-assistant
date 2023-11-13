from openai import OpenAI
import requests
import base64

client = OpenAI()

def upload_image_to_imgbb(image_path, api_key):
    """
    Загрузка изображения на Imgbb и получение URL изображения.
    """
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read())
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": api_key,
                "image": encoded_image,
            }
        )
    response_json = response.json()
    return response_json['data']['url']

# Предположим, что у тебя есть локальный путь к изображению и ключ API Imgbb
image_path = "test.jpeg"
imgbb_api_key = "af108b41e9bf6ed74a72b37e4eadf883"

# Загрузка изображения и получение URL
uploaded_image_url = upload_image_to_imgbb(image_path, imgbb_api_key)

# Теперь используем этот URL в запросе к OpenAI
response = client.chat.completions.create(
    model="gpt-4-vision-preview",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What’s in this image?"},
                {"type": "image_url", "image_url": {"url": uploaded_image_url}},
            ],
        }
    ],
    max_tokens=300,
)

print(response.choices[0])