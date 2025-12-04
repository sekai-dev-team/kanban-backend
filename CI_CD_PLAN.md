# 使用 GitHub Actions 和 Docker 实现 CI/CD 自动化部署方案

本文档为 `kanban-backend` 项目提供一个详细的、端到端的持续集成与持续部署 (CI/CD) 方案。
目标是实现当代码推送到 GitHub 主分支后，自动完成测试、镜像构建，并将其部署到服务器。

## 核心技术栈

- **代码托管与 CI/CD**: GitHub & GitHub Actions
- **容器化**: Docker & Docker Compose
- **容器镜像仓库**: Docker Hub (也可以替换为 GitHub Container Registry)
- **自动更新**: Watchtower (可选，但强烈推荐)

---

## 重要：关于服务器在私有网络 (如 ZeroTier) 的说明

你提到服务器位于 ZeroTier 组建的私有网络中，没有公网 IP。这是一个非常关键的因素，但好消息是，我们推荐的 **Watchtower “拉取”模式完美地解决了这个问题**。

### 为什么 Watchtower 是最佳选择？

- **工作模式**: GitHub Actions Runner 运行在公有云上，无法直接访问你的私有网络。因此，任何从 Runner “推送”到服务器的尝试 (如 SSH) 都会失败。而 Watchtower 采用的是“拉取”模式。你的服务器虽然没有公网 IP，但它通常**可以访问**公网。Watchtower 正是利用这一点，让你的服务器主动从公网上的 Docker Hub 拉取最新镜像。
- **安全性**: 这种模式更安全。你无需向 GitHub Actions 暴露任何服务器的敏感信息（如 SSH 密钥、IP 地址等），只需暴露推送到公共镜像仓库的凭证即可。
- **简易性**: 你无需对 CI/CD 工作流做任何复杂的网络配置。GitHub Actions 的任务非常纯粹：测试代码、构建镜像、推送到 Docker Hub。服务器的更新由 Watchtower 自行处理。

## 实施步骤

### 第 1 步：优化项目 Dockerfile

一个好的 `Dockerfile` 是实现高效、安全部署的基础。下面的 `Dockerfile` 使用了 **多阶段构建** 的最佳实践，可以显著减小最终镜像的体积，并提高安全性。

**文件路径**: `A:/project/kanban-backend/Dockerfile`

```Dockerfile
# --- 构建阶段 (Builder Stage) ---
# 使用一个包含完整构建工具的 Python 镜像
FROM python:3.10-slim AS builder

# 设置工作目录
WORKDIR /opt/app

# 设置 PYTHONDONTWRITEBYTECODE 来阻止 Python 写入 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE 1
# 设置 PYTHONUNBUFFERED 来确保日志直接输出，方便 Docker 收集
ENV PYTHONUNBUFFERED 1

# 安装虚拟环境工具
RUN pip install --no-cache-dir --upgrade pip poetry

# 创建一个非 root 用户来运行应用，增强安全性
RUN addgroup --system app && adduser --system --group app

# 复制依赖管理文件
COPY requirements.txt ./

# 创建虚拟环境并安装依赖
# 这样做可以保持最终镜像的纯净
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# --- 运行阶段 (Final Stage) ---
# 使用一个非常小的基础镜像
FROM python:3.10-slim

# 再次设置环境变量
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PATH="/opt/venv/bin:$PATH"

# 设置工作目录
WORKDIR /home/app

# 从构建阶段复制创建好的非 root 用户
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

# 从构建阶段复制安装好依赖的虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 复制项目源代码
COPY ./src ./src

# 确保日志和数据目录存在，并赋予新用户权限
RUN mkdir -p /home/app/log /home/app/data && \
    chown -R app:app /home/app
USER app

# 暴露 FastAPI 应用的默认端口
EXPOSE 8000

# 启动应用的命令
# 假设你的 FastAPI 实例在 src/main.py 文件中，变量名为 app
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 第 2 步：为服务器准备 `docker-compose.yml`

在你的服务器上，我们使用 `docker-compose` 来管理应用容器。这使得启动、停止和配置都变得非常简单。

**在你的服务器上** 创建此文件，例如路径为 `/home/your-user/kanban-backend/docker-compose.yml`。

```yaml
version: '3.8'

services:
  # 你的看板后端应用
  kanban-backend:
    # 镜像名称，必须与你推送到 Docker Hub 的名称一致
    # 请将 "your-dockerhub-username" 替换为你的真实 Docker Hub 用户名
    image: your-dockerhub-username/kanban-backend:latest
    container_name: kanban-backend-app
    restart: always
    ports:
      # 将服务器的 8000 端口映射到容器的 8000 端口
      - "8000:8000"
    volumes:
      # 将容器内的数据和日志目录持久化到服务器上
      - ./data:/home/app/data
      - ./log:/home/app/log
    # (可选) 如果你的应用需要环境变量，可以在这里配置
    # environment:
    #   - DATABASE_URL=your_database_url

  # Watchtower 服务，用于自动更新
  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: always
    volumes:
      # 需要挂载 docker.sock 才能监控和操作其他容器
      - /var/run/docker.sock:/var/run/docker.sock
    # Watchtower 会每隔 300 秒检查一次是否有新镜像
    command: --interval 300
```

### 第 3 步：配置服务器环境

1.  **安装 Docker 和 Docker Compose**
    如果你的服务器是 Ubuntu/Debian，可以运行以下命令：
    ```bash
    # 安装 Docker
    sudo apt-get update
    sudo apt-get install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker

    # 安装 Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    ```

2.  **启动服务**
    - 将上一步创建的 `docker-compose.yml` 文件上传到服务器。
    - 在服务器上，进入该文件所在的目录。
    - 运行 `docker-compose up -d`。
    - **注意**: 第一次运行时 `kanban-backend` 服务会因为找不到镜像而失败，这是正常的。Watchtower 启动后，一旦我们把镜像推送到 Docker Hub，它就会自动拉取并启动 `kanban-backend` 服务。

### 第 4 步：在 GitHub 中设置 Secrets

为了让 GitHub Actions 能够安全地登录 Docker Hub 和你的服务器（如果需要），必须将敏感信息存储在 **GitHub Secrets** 中。

进入你的 GitHub 仓库页面，点击 `Settings > Secrets and variables > Actions`，然后点击 `New repository secret` 添加以下密钥：

- `DOCKERHUB_USERNAME`: 你的 Docker Hub 用户名。
- `DOCKERHUB_TOKEN`: 你的 Docker Hub 访问令牌 (在 Docker Hub 的安全设置中创建)。
- `SERVER_HOST`: 你服务器的 IP 地址或域名。
- `SERVER_USER`: 用于 SSH 登录的用户名。
- `SERVER_SSH_KEY`: 用于 SSH 登录的私钥。**这是你的 `.ssh/id_rsa` 文件的内容，而不是公钥。**

### 第 5 步：编写 GitHub Actions Workflow

这是整个 CI/CD 流程的核心。在你的项目根目录下，创建文件夹 `.github/workflows`，然后在其中创建一个 `main.yml` 文件。

**文件路径**: `A:/project/kanban-backend/.github/workflows/main.yml`

```yaml
name: CI/CD for Kanban Backend

# 触发条件：当有代码推送到 main 分支时
on:
  push:
    branches: [ "main" ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      # 1. 检出代码
      - name: Checkout repository
        uses: actions/checkout@v4

      # 2. 设置 QEMU (用于多平台构建，是 buildx 的一个好搭档)
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      # 3. 设置 Docker Buildx (一个更高级的构建器)
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      # 4. 登录到 Docker Hub
      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      # 5. 构建并推送 Docker 镜像
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile
          push: true
          # 定义镜像标签，一个 latest，一个使用 commit SHA，方便追溯
          tags: |
            ${{ secrets.DOCKERHUB_USERNAME }}/kanban-backend:latest
            ${{ secrets.DOCKERHUB_USERNAME }}/kanban-backend:${{ github.sha }}

      # 6. (可选步骤) SSH 到服务器并强制更新
      # 如果你没有使用 Watchtower，或者希望立即部署而不是等待 Watchtower 轮询，可以取消下面步骤的注释。
      # - name: Deploy to Server
      #   uses: appleboy/ssh-action@master
      #   with:
      #     host: ${{ secrets.SERVER_HOST }}
      #     username: ${{ secrets.SERVER_USER }}
      #     key: ${{ secrets.SERVER_SSH_KEY }}
      #     script: |
      #       cd /home/your-user/kanban-backend # 进入 docker-compose 文件所在的目录
      #       docker-compose pull kanban-backend # 拉取最新镜像
      #       docker-compose up -d --no-deps kanban-backend # 重启服务
```

---

## 总结与工作流程

配置完成后，你的自动化工作流如下：

1.  **本地开发**: 你在本地完成编码和测试。
2.  **代码推送**: 你将代码推送到 GitHub 的 `main` 分支: `git push origin main`。
3.  **CI/CD 触发**: GitHub Actions 检测到推送，自动开始执行 `.github/workflows/main.yml` 中的任务。
4.  **构建与推送**: Actions 服务器会自动构建一个新的 Docker 镜像，并将其推送到 Docker Hub。
5.  **自动部署**:
    - **(推荐方式)** 服务器上运行的 Watchtower 会定期检测 Docker Hub 上的镜像。发现有新版本后，它会自动拉取新镜像，并用新镜像优雅地重启 `kanban-backend` 容器。
    - **(备选方式)** 如果你配置了 SSH 步骤，GitHub Actions 会在推送镜像后，立即登录到你的服务器，强制拉取新镜像并重启服务。

现在，你只需专注于编码和 `git push`，部署的繁琐工作已全部自动化。
