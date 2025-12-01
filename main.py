from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yaml
import os
import threading

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,  # 允许这些来源
#     allow_credentials=True,
#     allow_methods=["*"],  # 允许所有方法 (GET, POST, OPTIONS 等)
#     allow_headers=["*"],  # 允许所有 Header
# )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # [关键修改] 允许任何 IP 访问，彻底消除 CORS 问题
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
DATA_DIR = "data"
file_lock = threading.Lock()
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Kanban API"}


@app.get("/api/kanban/{project_id}")
def get_kanban(project_id: str):
    file_path = os.path.join(DATA_DIR, f"{project_id}.yaml")

    with file_lock:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Project not found")

        with open(file_path, "r+", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

            if "_version" not in data:
                data["_version"] = 1
                f.seek(0)
                yaml.dump(data, f, allow_unicode=True)
                f.truncate()

    return data


@app.post("/api/kanban/{project_id}")
def update_kanban(project_id: str, kanban_data: dict):
    file_path = os.path.join(DATA_DIR, f"{project_id}.yaml")

    client_version = kanban_data.get("_version")
    if client_version is None:
        raise HTTPException(status_code=400, detail="Missing _version field")

    with file_lock:
        current_data = {}
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                current_data = yaml.safe_load(f) or {}

        server_version = current_data.get("_version", 0)

        # On new file creation, allow version 1
        if not current_data and client_version == 1:
            server_version = 1

        if server_version != client_version:
            raise HTTPException(
                status_code=409, detail="Conflict, data has been modified by others."
            )

        kanban_data["_version"] = client_version + 1

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(kanban_data, f, allow_unicode=True)

    return {
        "message": f"Project '{project_id}' updated successfully.",
        "new_version": kanban_data["_version"],
    }
