FROM python:3.12-slim

# git 供『更新』按钮拉取代码;ca-certificates 供 HTTPS
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# -u 关闭输出缓冲,docker logs 能实时看到
CMD ["python", "-u", "bot.py"]
