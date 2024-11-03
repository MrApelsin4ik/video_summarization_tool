import whisper
import requests
import time
import re
from celery import Celery
from redis import Redis
from moviepy.editor import VideoFileClip
import uuid
import os
from llama_cpp import Llama
import torch



# Настройка Celery и Redis
celery_app = Celery("tasks", backend="redis://localhost", broker="redis://localhost")
celery_app.conf.worker_concurrency = 1
redis_client = Redis(host='localhost', port=6379, db=0)



# Функция для обработки текста через Llama

def process_text_with_llama(text, task, max_tokens=-1):
    global llama_model
    torch.cuda.empty_cache()
    prompt = f'Q:{task}{text} A:'

    print(f'\n\n ================= \ntask: {prompt}\n \n')
    response = llama_model(prompt, temperature=0.4, top_p=0.9, top_k=40, stop=["\n", "Q:", "A:", "А:", "L:"],
                           max_tokens=max_tokens)
    print(f'{response}\n=================\n\n')
    if response is None or "error" in response:
        print("Ошибка при обработке текста.")
        return False  # Возвращаем False при ошибке

    return response['choices'][0]['text'].strip()


def calc_token_amount(sentence):
    global llama_model
    sentence_tokens = llama_model.tokenize(bytes(sentence, 'utf-8'))
    sentence_token_count = len(sentence_tokens)
    return sentence_token_count


# Разделение текста на части

def split_text(text, max_tokens=750):
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current_chunk = ""
    current_tokens = 0

    for sentence in sentences:
        # Токенизируем предложение

        sentence_token_count = calc_token_amount(sentence)

        # Проверяем количество токенов в текущем куске
        if current_tokens + sentence_token_count <= max_tokens:
            current_chunk += " "  # Добавляем пробел между предложениями
            current_chunk += sentence
            current_tokens += sentence_token_count
        else:
            # Если превышаем лимит по токенам, сохраняем текущий кусок и начинаем новый
            chunks.append(current_chunk)

            current_chunk = sentence
            current_tokens = sentence_token_count

    # Добавляем последний кусок, если он не пустой
    if current_chunk:
        chunks.append(current_chunk)

    return chunks




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


whisper_model, llama_model = None, None

@celery_app.task
def init_models():
    global whisper_model, llama_model
    print('loading whisper')
    whisper_model = whisper.load_model("base", device="cuda")  #you can change "base" to another models. Check https://github.com/openai/whisper
    print('loading llama')
    llama_model = Llama(model_path="./ggml-model-Q4_K_M.gguf", n_gpu_layers=-1, n_ctx=8192) #change "./ggml-model-Q4_K_M.gguf" to "./ggml-model-Q8_0.gguf" if you have enough performance.


init_models.delay()

# Задача для обработки видео
@celery_app.task(name="tasks.process_video", time_limit=60*20) #change time limit as you need (in seconds)
def process_video(data, task_id):
    global whisper_model, llama_model
    beg_time = time.time()
    torch.cuda.empty_cache()

    if not whisper_model or not llama_model:
        init_models.delay()

    try:

        # Скачивание файла
        video_path = download_from_yandex(data)

        # Извлекаем аудио из видео
        video = VideoFileClip(video_path)
        audio_file = "temp_audio.wav"  # используем WAV напрямую
        video.audio.write_audiofile(audio_file, codec='pcm_s16le')


        # Транскрибируем аудио
        print('STT is working')
        start_time = time.time()
        result = whisper_model.transcribe(audio_file)
        elapsed_time = time.time() - start_time
        print(f"Transcription completed in {elapsed_time:.2f} seconds")
        print(result["text"])

        # Удаляем временный MP3 файл после транскрипции
        os.remove(audio_file)


        chunks = split_text(result["text"])
        topic = process_text_with_llama(chunks[0], "Определи тему (кратко, не более 5-7 слов)")
        summary = ""

        for chunk in chunks:
            success = False
            while not success:
                processed_text = process_text_with_llama(chunk, f'Перепиши текст, максимально сократив его.(Оставь только то, что касается основной темы:{topic})')
                if processed_text is False:
                    print("Повторный запрос для части текста...")

                    continue  # Попробуем снова
                summary += str(processed_text) + str(" ")
                success = True  # Успех, выходим из цикла

        # Обновление статуса и результата задачи
        redis_client.set(task_id, "completed")
        redis_client.set(f"{task_id}_result", summary)
        os.remove(video_path)
        print(f'task finished in {round(time.time()-beg_time)}sec.')
        return summary
    except Exception as e:
        redis_client.set(task_id, "failed")
        print(e)