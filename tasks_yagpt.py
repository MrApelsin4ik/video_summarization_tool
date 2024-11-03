import whisper
import requests
import time
import re
from celery import Celery
from redis import Redis
from moviepy.editor import VideoFileClip
import uuid
import os




# Настройка Celery и Redis
celery_app = Celery("tasks", backend="redis://localhost", broker="redis://localhost")
celery_app.conf.worker_concurrency = 1
redis_client = Redis(host='localhost', port=6379, db=0)


# Функция для обработки текста через Yandex GPT
def process_text_with_yandex_gpt(text, task):
    print(f"{task}: {text}")
    prompt = {
        "modelUri": "gpt://<ВАШ_ИДЕНТИФИКАТОР_КАТАЛОГА>/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": "2000"
        },
        "messages": [
            {"role": "system", "text": "Ты языковая модель для обработки текста. В твоём ответе должен быть только обработанный текст и ничто больше."},
            {"role": "user", "text": f"{task}: {text}"}
        ]
    }

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": "Api-Key <your api key>" #put your yagpt api key here
    }

    response = requests.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completion", headers=headers, json=prompt)

    if response.status_code != 200:
        print("Ошибка:", response.status_code, response.text)
        return False

    result = response.json()

    return result.get('result', {}).get('alternatives', [{}])[0].get('message', {}).get('text', '').strip()

# Разделение текста на части
def split_text(text, max_length=1100):
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks, current_chunk = [], ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_length:
            current_chunk += ("" if not current_chunk else " ") + sentence
        else:
            chunks.append(current_chunk)
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

# Генерация конспекта
def create_summary(chunks, topic):
    summary = ""
    for chunk in chunks:
        success = False
        while not success:
            processed_text = process_text_with_yandex_gpt(chunk, f'Перепиши текст, сократив его, оставь только самое главное, касающееся основной темы: {topic}')
            print(processed_text)
            if processed_text is False:
                print('повторный запрос')
                time.sleep(2)
                continue
            summary += processed_text + " "
            success = True
    return summary.strip()


def download_from_yandex(data):
    if data.get("api_key") and data.get("video_path"):
        url = "https://cloud-api.yandex.net/v1/disk/resources/download"
        headers = {"Authorization": f"OAuth {data['api_key']}"}
        params = {"path": data["video_path"]}
        response = requests.get(url, headers=headers, params=params)
    elif data.get("video_url"):
        url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
        params = {"public_key": data["video_url"]}
        response = requests.get(url, params=params)
    else:
        raise ValueError("Invalid data for downloading from Yandex Disk.")

    download_url = response.json().get("href")
    if not download_url:
        raise Exception("Failed to get download link from Yandex Disk.")

    # Создание директории, если ее нет
    os.makedirs("./downloads", exist_ok=True)
    local_path = f"./downloads/{uuid.uuid4()}.mp4"

    # Скачивание файла
    video_content = requests.get(download_url).content
    with open(local_path, "wb") as f:
        f.write(video_content)
    return local_path



whisper_model = None

@celery_app.task
def init():
    global whisper_model
    print('loading whisper')
    whisper_model = whisper.load_model("turbo",device="cuda")  # you can change "turbo" to another models. Check https://github.com/openai/whisper

init.delay()

# Задача для обработки видео
@celery_app.task(name="tasks.process_video")
def process_video(data, task_id):
    global whisper_model
    beg_time = time.time()
    if not whisper_model:
        init.delay()

    try:
        # Скачивание файла
        video_path = download_from_yandex(data)

        # Извлекаем аудио из видео
        video = VideoFileClip(video_path)
        audio_file = "temp_audio.wav"
        video.audio.write_audiofile(audio_file, codec='pcm_s16le')


        # Транскрибируем аудио
        print('STT is working')
        start_time = time.time()
        result = whisper_model.transcribe(audio_file, fp16=True)  # Используем fp16 для ускорения
        elapsed_time = time.time() - start_time
        print(f"Transcription completed in {elapsed_time:.2f} seconds")
        print(result["text"])

        # Удаляем временный MP3 файл после транскрипции
        os.remove(audio_file)


        chunks = split_text(result["text"])
        topic = process_text_with_yandex_gpt(chunks[0], "Определи тему лекции.")
        summary = create_summary(chunks, topic)

        # Обновление статуса и результата задачи
        redis_client.set(task_id, "completed")
        redis_client.set(f"{task_id}_result", summary)
        os.remove(video_path)
        print(f'task finished in {round(time.time() - beg_time)}sec.')
        return summary
    except Exception as e:
        redis_client.set(task_id, "failed")
        raise e
