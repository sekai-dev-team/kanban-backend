# 使用官方的 Python 基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装依赖
# 这样做可以利用 Docker 的层缓存机制，只有当 requirements.txt 变化时才会重新安装
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 复制项目代码到工作目录
COPY . .

# 暴露端口，FastAPI 默认运行在 8000 端口
EXPOSE 8000

# 启动应用的命令
# 使用 --host 0.0.0.0 使其可以从容器外部访问
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
