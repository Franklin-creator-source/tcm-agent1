
# ============================================================
# Dockerfile - 中医知识问答 Flask 应用
# 基于多阶段构建，支持开发和生产环境
# ============================================================

# ─── 第一阶段：构建阶段（安装依赖） ───
FROM python:3.11-slim AS builder

# 设置环境变量，优化 Python 运行行为
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置工作目录
WORKDIR /app

# 只复制依赖文件，利用 Docker 缓存加速后续构建
COPY requirements.txt .

# 安装系统依赖（gcc 用于编译某些 Python 包）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖到用户目录（便于多阶段复制）
RUN pip install --user --no-cache-dir -r requirements.txt

# ─── 第二阶段：运行阶段（最小化镜像） ───
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:${PATH}" \
    PORT=8088 \
    TZ=Asia/Shanghai

# 设置工作目录
WORKDIR /app

# 从构建阶段复制已安装的依赖
COPY --from=builder /root/.local /root/.local

# 复制应用代码
COPY . .

# 创建非 root 用户（增强安全性）
RUN groupadd -r appuser && \
    useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app

# 切换到非 root 用户运行
USER appuser

# 暴露应用端口
EXPOSE ${PORT}

# 健康检查（确保容器正常运行）
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/info || exit 1

# 启动命令（使用 Gunicorn 作为生产级 WSGI 服务器）
CMD ["gunicorn", "--bind", "0.0.0.0:8088", "--workers", "4", "--timeout", "120", "server:app"]
