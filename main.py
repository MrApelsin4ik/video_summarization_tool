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

# Redis-client for storing task states
redis_client = Redis(host='localhost', port=6379, db=0)


# Request model
class SummarizationRequest(BaseModel):
    api_key: str = None
    video_url: str = None
    video_path: str = None



# Adding a summation task
@app.post("/summarize/")
async def summarize(data: SummarizationRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    # Checking and submitting a task for processing
    if data.video_url or (data.api_key and data.video_path):
        # Saving a task in Redis with "waiting" for processing
        redis_client.set(task_id, "pending")

        # Sending a task to Celery
        celery_app.send_task(
            "tasks.process_video",
            args=[dict(data), task_id]
        )
        return {"task_id": task_id}
    else:
        raise HTTPException(status_code=400, detail="Incorrect data")


# Getting the task status
@app.get("/status/{task_id}")
async def get_status(task_id: str):
    status = redis_client.get(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="The task was not found")
    return {"task_id": task_id, "status": status.decode()}


# Getting the result of the task
@app.get("/result/{task_id}")
async def get_result(task_id: str):
    result = redis_client.get(f"{task_id}_result")
    if not result:
        raise HTTPException(status_code=404, detail="The result was not found")
    return {"task_id": task_id, "result": result.decode()}
