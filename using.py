import requests
import time

BASE_URL = "http://127.0.0.1:8000" #change to your server ip

# Пример данных для запроса суммаризации
data1 = {
    "api_key": "", # yandex disk api key. You can get it here https://oauth.yandex.ru/authorize?response_type=token&client_id=eebf0e9b08e8464a83ba35ae5c746cf5
    "video_path": "/Вторая мировая война.mp4",  # полный путь до видео

}

data2 = {
    "video_url": "https://disk.yandex.ru/i/t_qbkVAf-q1Egw",  # ссылка на видео
}

data = data1 # or data2

def submit_summarization_task(data):
    """
    Отправляет запрос на суммаризацию видео и возвращает ID задачи.
    """
    response = requests.post(f"{BASE_URL}/summarize/", json=data)
    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"Задача создана. ID задачи: {task_id}")
        return task_id
    else:
        print(f"Ошибка: {response.status_code}, {response.text}")
        return None


def check_task_status(task_id):
    """
    Проверяет статус задачи по ID.
    """
    response = requests.get(f"{BASE_URL}/status/{task_id}")
    if response.status_code == 200:
        status = response.json().get("status")
        print(f"Статус задачи {task_id}: {status}")
        return status
    else:
        print(f"Ошибка: {response.status_code}, {response.text}")
        return None


def get_summarization_result(task_id):
    """
    Получает результат суммаризации по ID задачи.
    """
    response = requests.get(f"{BASE_URL}/result/{task_id}")
    if response.status_code == 200:
        result = response.json().get("result")
        print(f"Результат задачи {task_id}: {result}")
        return result
    else:
        print(f"Ошибка: {response.status_code}, {response.text}")
        return None


def main():
    # Отправляем запрос на суммаризацию
    task_id = submit_summarization_task(data)

    if not task_id:
        print("Не удалось создать задачу.")
        return

    # Ожидаем выполнения задачи и проверяем её статус
    while True:
        status = check_task_status(task_id)
        if status == "completed":
            break
        elif status == "pending":
            print("Задача ещё выполняется...")
            time.sleep(5)  # Ждем 5 секунд перед повторной проверкой
        else:
            print("Ошибка выполнения задачи.")
            return

    # Получаем и выводим результат суммаризации
    get_summarization_result(task_id)


if __name__ == "__main__":
    main()
