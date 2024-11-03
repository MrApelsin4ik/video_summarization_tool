# Tool for Video Summarization from YaDisk

This FastAPI-based tool allows you to summarize video content stored on Yandex Disk. It processes video requests and returns concise summaries.

## Getting Started

To use this tool, you’ll need a Yandex Disk API key. Obtain it by following this link: [Get YaDisk API Key](https://oauth.yandex.ru/authorize?response_type=token&client_id=eebf0e9b08e8464a83ba35ae5c746cf5)

### Requirements
- **Python 3.9+**

### Installation

1. **Update and Install Dependencies**
    ```bash
   sudo apt update
   sudo apt install python3.9
   sudo apt install redis-server
   sudo apt install ffmpeg
    ```
2. **Install Python Packages**
    ```bash
    pip install fastapi[all]
    pip install git+https://github.com/openai/whisper.git
    pip install celery
    pip install redis
    pip install moviepy
    ```
3. **Optional: Install LLaMA Support**    
    To use the version with LLaMA support, install the package below. If you need GPU support or alternative installation methods, refer to the [llama-cpp-python documentation](https://github.com/abetlen/llama-cpp-python).
   ```bash
    pip install llama-cpp-python
    ```

   
**Quick Install**

To install everything at once, use one of the following commands:

With LLaMA support:
```bash
sudo apt update && sudo apt install ffmpeg && sudo apt install redis-server && pip install fastapi[all] git+https://github.com/openai/whisper.git celery redis moviepy llama-cpp-python
 ```
Without LLaMA support:
```bash
sudo apt update && sudo apt install ffmpeg && sudo apt install redis-server && pip install fastapi[all] git+https://github.com/openai/whisper.git celery redis moviepy
```

**Download llama models**
To download llama models [click here](https://huggingface.co/Apeellsin4ik/saiga_on_llama3).

**Running the Server**
    To start the FastAPI server and Celery worker:
    Llama:
    ```bash
        uvicorn main:app --reload --host 0.0.0.0 & celery -A tasks_llama worker
     ```
    YaGPT:
    ```bash
        uvicorn main:app --reload --host 0.0.0.0 & celery -A tasks_yagpt worker
     ```

**Usage Example**
    Refer to the using.py file for examples on how to make API requests to this tool.

