from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from celery import Celery
from redis import Redis
import uuid

app = FastAPI()
celery_app = Celery(
    "tasks",
    backend="redis://localhost",
    broker="redis://localhost"
)

# Redis-клиент для хранения состояний задач
redis_client = Redis(host='localhost', port=6379, db=0)


# Модель запроса
class SummarizationRequest(BaseModel):
    api_key: str = None
    video_url: str = None
    video_path: str = None



# Добавление задачи на суммаризацию
@app.post("/summarize/")
async def summarize(data: SummarizationRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    # Проверка и отправка задачи на обработку
    if data.video_url or (data.api_key and data.video_path):
        # Сохранение задачи в Redis с "ожиданием" обработки
        redis_client.set(task_id, "pending")

        # Отправка задачи в Celery
        celery_app.send_task(
            "tasks.process_video",
            args=[dict(data), task_id]
        )
        return {"task_id": task_id}
    else:
        raise HTTPException(status_code=400, detail="Некорректные данные")


# Получение статуса задачи
@app.get("/status/{task_id}")
async def get_status(task_id: str):
    status = redis_client.get(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return {"task_id": task_id, "status": status.decode()}


# Получение результата задачи
@app.get("/result/{task_id}")
async def get_result(task_id: str):
    result = redis_client.get(f"{task_id}_result")
    if not result:
        raise HTTPException(status_code=404, detail="Результат не найден")
    return {"task_id": task_id, "result": result.decode()}
