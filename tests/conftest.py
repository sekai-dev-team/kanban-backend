import pytest
from fastapi.testclient import TestClient
import os
import shutil
import sys

from src.main import create_app


@pytest.fixture(name="client")
def client_fixture(tmp_path):
    """
    为每个测试函数创建一个全新的、隔离的 app 实例和 TestClient。
    app 的数据目录指向由 pytest 提供的唯一临时目录 (tmp_path)。
    """
    # 使用 tmp_path 为每个测试创建一个隔离的数据目录
    test_data_dir = tmp_path / "test_data"
    test_data_dir.mkdir()

    # 每次测试都创建一个新的 app 实例，确保状态完全隔离
    app = create_app(data_dir=str(test_data_dir))

    with TestClient(app) as client:
        yield client
