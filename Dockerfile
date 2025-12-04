# --------------------------------- Build ---------------------------------
FROM python:3.10-slim AS builder
WORKDIR /opt/app

# 设置 PYTHONDONTWRITEBYTECODE 来阻止 Python 写入 .pyc 文件
# 设置 PYTHONUNBUFFERED 来确保日志直接输出，方便 Docker 收集
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN addgroup --system app && adduser --system --group app

COPY requirements.txt ./

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------- Run ---------------------------------
FROM python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /home/app
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

# 从构建阶段复制安装好依赖的虚拟环境
COPY --from=builder /opt/venv /opt/venv

COPY ./src ./src
RUN mkdir -p /home/app/log /home/app/data && \
    chown -R app:app /home/app
USER app
EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]