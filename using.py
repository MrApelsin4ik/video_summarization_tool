import requests
import time

BASE_URL = "http://127.0.0.1:8000" #change to your server ip

# Example data for summarization
data1 = {
    "api_key": "", # yandex disk api key. You can get it here https://oauth.yandex.ru/authorize?response_type=token&client_id=eebf0e9b08e8464a83ba35ae5c746cf5
    "video_path": "/Вторая мировая война.mp4",  # full path to video

}

data2 = {
    "video_url": "https://disk.yandex.ru/i/t_qbkVAf-q1Egw",  # url to video (if the video is shared)
}

data = data1 # or data2

def submit_summarization_task(data):
    """
    Sends summarization request and return id of task
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
    Checks task status by id
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
    Gets result of summarization by id
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
    # Sending summarization request
    task_id = submit_summarization_task(data)

    if not task_id:
        print("Не удалось создать задачу.")
        return

    # Waiting for finish of task and getiing result
    while True:
        status = check_task_status(task_id)
        if status == "completed":
            break
        elif status == "pending":
            print("Задача ещё выполняется...")
            time.sleep(5)  # Wait 5 sec before next try
        else:
            print("Ошибка выполнения задачи.")
            return

    # Getting and printing summarization result
    get_summarization_result(task_id)


if __name__ == "__main__":
    main()
