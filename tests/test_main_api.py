import pytest
from fastapi.testclient import TestClient
import os
import yaml

# client fixture 来自 conftest.py，它会提供一个配置了临时数据目录的 TestClient

def test_read_root(client: TestClient):
    """测试根路径是否返回预期消息和状态码。"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Kanban API"}


def test_get_non_existent_project(client: TestClient):
    """测试获取不存在的项目时是否返回 404 状态码。"""
    project_id = "non_existent_project"
    response = client.get(f"/api/kanban/{project_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_create_and_get_project(client: TestClient):
    """测试创建新项目并成功获取。"""
    project_id = "test_project_1"
    initial_data = {"_version": 1, "columns": [{"name": "Todo", "tasks": []}]}

    # 创建项目
    response = client.post(f"/api/kanban/{project_id}", json=initial_data)
    assert response.status_code == 200
    assert response.json()["message"] == f"Project '{project_id}' updated successfully."
    assert response.json()["new_version"] == 2

    # 获取项目
    response = client.get(f"/api/kanban/{project_id}")
    assert response.status_code == 200
    retrieved_data = response.json()
    # 验证返回的数据，除了 _version 应该更新
    expected_data_retrieved = {"_version": 2, "columns": [{"name": "Todo", "tasks": []}]}
    assert retrieved_data == expected_data_retrieved


def test_update_project_conflict(client: TestClient):
    """测试更新项目时版本冲突是否返回 409 状态码。"""
    project_id = "test_project_conflict"
    initial_data = {"_version": 1, "columns": []}

    # 首次创建项目
    response = client.post(f"/api/kanban/{project_id}", json=initial_data)
    assert response.status_code == 200
    assert response.json()["new_version"] == 2

    # 模拟客户端使用过期的版本号 (1) 进行更新
    outdated_data = {"_version": 1, "columns": [{"name": "Doing", "tasks": []}]}
    response = client.post(f"/api/kanban/{project_id}", json=outdated_data)
    assert response.status_code == 409
    assert response.json() == {"detail": "Conflict, data has been modified by others."}


def test_update_project_missing_version(client: TestClient):
    """测试更新项目时缺少版本字段是否返回 400 状态码。"""
    project_id = "test_project_missing_version"
    invalid_data = {"columns": []}  # 缺少 _version 字段

    response = client.post(f"/api/kanban/{project_id}", json=invalid_data)
    assert response.status_code == 400
    assert response.json() == {"detail": "Missing _version field"}


def test_update_project_success(client: TestClient):
    """测试成功更新项目。"""
    project_id = "test_project_success"
    initial_data = {"_version": 1, "columns": [{"name": "Todo", "tasks": []}]}

    # 首次创建项目
    response = client.post(f"/api/kanban/{project_id}", json=initial_data)
    assert response.status_code == 200
    assert response.json()["new_version"] == 2

    # 模拟客户端使用正确的版本号 (2) 进行更新
    updated_data = {"_version": 2, "columns": [{"name": "Done", "tasks": [{"id": "1", "title": "Task 1"}]}]}
    response = client.post(f"/api/kanban/{project_id}", json=updated_data)
    assert response.status_code == 200
    assert response.json()["new_version"] == 3

    # 验证更新后的数据
    response = client.get(f"/api/kanban/{project_id}")
    assert response.status_code == 200
    retrieved_data = response.json()
    expected_data_retrieved = {"_version": 3, "columns": [{"name": "Done", "tasks": [{"id": "1", "title": "Task 1"}]}]}
    assert retrieved_data == expected_data_retrieved
