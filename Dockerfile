# AI Assistant Dockerfile
# 多阶段构建，优化镜像大小和安全性

# 构建阶段
FROM ubuntu:22.04 AS builder

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV CMAKE_VERSION=3.26.0
ENV PYTHON_VERSION=3.11

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    wget \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    libgrpc++-dev \
    libprotobuf-dev \
    protobuf-compiler-grpc \
    && rm -rf /var/lib/apt/lists/*

# 创建工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
COPY CMakeLists.txt .
COPY cpp/ ./cpp/
COPY protos/ ./protos/

# 安装Python依赖
RUN python3 -m pip install --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# 构建C++组件
RUN mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF && \
    cmake --build . --config Release && \
    cmake --install . --prefix /app/install

# 运行阶段
FROM ubuntu:22.04 AS runtime

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH="/app:/app/python"
ENV PATH="/app/install/bin:$PATH"

# 创建非root用户
RUN groupadd -r aiassistant && useradd -r -g aiassistant aiassistant

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libgrpc++1 \
    libprotobuf23 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建应用目录
WORKDIR /app

# 从构建阶段复制文件
COPY --from=builder /app/install/ ./install/
COPY --from=builder /usr/local/lib/python3.10/dist-packages/ /usr/local/lib/python3.10/dist-packages/

# 复制应用代码
COPY python/ ./python/
COPY ui/ ./ui/
COPY scripts/ ./scripts/
COPY requirements.txt .
COPY start_cli.py .
COPY .env.example .

# 安装Python运行时依赖
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# 创建必要的目录
RUN mkdir -p logs data run tmp && \
    chown -R aiassistant:aiassistant /app

# 切换到非root用户
USER aiassistant

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000 50051

# 启动脚本
COPY --chown=aiassistant:aiassistant docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["server"]