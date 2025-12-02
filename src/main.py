import os
import threading
import logging
from src.utils.logging_config import setup_logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import yaml

# 全局可变变量，用于存储数据目录路径
_data_dir: str = "data"
_file_lock = threading.Lock()  # 将文件锁也关联到应用实例，或者也通过依赖注入管理


def get_data_dir_dependency():
    """FastAPI 依赖项，用于获取数据目录路径。"""
    return _data_dir


def create_app(data_dir: str = "data") -> FastAPI:
    """
    创建并配置 FastAPI 应用实例。
    data_dir: 应用使用的数据目录。
    """
    global _data_dir
    _data_dir = data_dir

    if not os.path.exists(_data_dir):
        os.makedirs(_data_dir)

    APP_ENV = os.getenv("APP_ENV", "development")
    setup_logging(APP_ENV)
    logger = logging.getLogger(__name__)

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # [关键修改] 允许任何 IP 访问，彻底消除 CORS 问题
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(f"FastAPI application created with DATA_DIR: {_data_dir}")

    @app.get("/")
    def read_root():
        logger.info("Root endpoint accessed.")
        return {"message": "Welcome to the Kanban API"}

    @app.get("/api/kanban/{project_id}")
    def get_kanban(
        project_id: str, current_data_dir: str = Depends(get_data_dir_dependency)
    ):
        logger.info(f"Attempting to get kanban for project_id: {project_id}")
        file_path = os.path.join(current_data_dir, f"{project_id}.yaml")

        with _file_lock:
            if not os.path.exists(file_path):
                logger.warning(
                    f"Project not found for project_id: {project_id} in {current_data_dir}"
                )
                raise HTTPException(status_code=404, detail="Project not found")

            with open(file_path, "r+", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

                if "_version" not in data:
                    data["_version"] = 1
                    f.seek(0)
                    yaml.dump(data, f, allow_unicode=True)
                    f.truncate()
                    logger.info(
                        f"Initialized version for new project: {project_id} in {current_data_dir}"
                    )

        logger.info(
            f"Successfully retrieved kanban for project_id: {project_id} from {current_data_dir}"
        )
        return data

    @app.post("/api/kanban/{project_id}")
    def update_kanban(
        project_id: str,
        kanban_data: dict,
        current_data_dir: str = Depends(get_data_dir_dependency),
    ):
        logger.info(f"Attempting to update kanban for project_id: {project_id}")
        file_path = os.path.join(current_data_dir, f"{project_id}.yaml")

        client_version = kanban_data.get("_version")
        if client_version is None:
            logger.error(f"Missing _version field for project_id: {project_id}")
            raise HTTPException(status_code=400, detail="Missing _version field")

        with _file_lock:
            current_data = {}
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    current_data = yaml.safe_load(f) or {}

            server_version = current_data.get("_version", 0)

            # On new file creation, allow version 1
            if not current_data and client_version == 1:
                server_version = 1

            if server_version != client_version:
                logger.warning(
                    f"Version conflict for project_id: {project_id}. "
                    f"Server version: {server_version}, client version: {client_version}"
                )
                raise HTTPException(
                    status_code=409,
                    detail="Conflict, data has been modified by others.",
                )

            kanban_data["_version"] = client_version + 1

            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(kanban_data, f, allow_unicode=True)

        logger.info(
            f"Successfully updated kanban for project_id: {project_id} in {current_data_dir}"
        )
        return {
            "message": f"Project '{project_id}' updated successfully.",
            "new_version": kanban_data["_version"],
        }

    return app


# 应用启动入口
if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
