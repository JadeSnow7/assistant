# 部署指南

本文档提供AI Assistant在不同环境中的完整部署指南。

## 部署选项概览

| 部署方式 | 适用场景 | 复杂度 | 可扩展性 |
|---------|---------|--------|----------|
| 单机部署 | 开发测试 | 低 | 低 |
| Docker容器 | 标准化部署 | 中 | 中 |
| Docker Compose | 本地生产 | 中 | 中 |
| Kubernetes | 云原生生产 | 高 | 高 |

## 环境要求

### 最低系统要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|----------|
| CPU | 2核心 | 4核心+ |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 20GB | 50GB+ |
| 网络 | 1Mbps | 10Mbps+ |

### 软件依赖

#### 基础环境
- **操作系统**: Linux (Ubuntu 20.04+), macOS (10.15+), Windows (10+)
- **Python**: 3.9+ (推荐3.11)
- **Node.js**: 16+ (如需Web界面)
- **CMake**: 3.20+
- **编译器**: GCC 9+, Clang 12+, MSVC 2019+

#### 可选组件
- **Docker**: 20.10+ (容器化部署)
- **Kubernetes**: 1.25+ (集群部署)
- **Redis**: 6.0+ (缓存)
- **PostgreSQL**: 12+ (生产数据库)

## 1. 单机部署

### 1.1 源码部署

#### 克隆代码
```bash
git clone https://github.com/your-org/ai-assistant.git
cd ai-assistant
```

#### 环境配置
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 构建C++组件
```bash
# 使用构建脚本
./scripts/build.sh

# 或手动构建
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
cmake --install . --prefix ../install
```

#### 配置环境变量
```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
vim .env
```

必要的配置项：
```bash
# API服务配置
HOST=0.0.0.0
PORT=8000
DEBUG=false

# gRPC配置
GRPC_SERVER_ADDRESS=localhost:50051

# AI模型配置
GEMINI_API_KEY=your_gemini_api_key
OLLAMA_BASE_URL=http://localhost:11434

# 数据库配置
DATABASE_URL=sqlite:///./ai_assistant.db
```

#### 启动服务
```bash
# 使用启动脚本
./scripts/run_server.sh

# 或分别启动服务
# 1. 启动gRPC服务
./install/bin/ai_assistant_server &

# 2. 启动API服务
cd python && python main.py
```

#### 验证部署
```bash
# 健康检查
curl http://localhost:8000/health

# 测试CLI
python start_cli.py
```

### 1.2 二进制部署

如果提供了预编译二进制包：

```bash
# 下载发布包
wget https://github.com/your-org/ai-assistant/releases/download/v1.0.0/ai-assistant-v1.0.0-linux-x64.tar.gz

# 解压
tar -xzf ai-assistant-v1.0.0-linux-x64.tar.gz
cd ai-assistant-v1.0.0-linux-x64

# 配置
cp .env.example .env
vim .env

# 启动
./run.sh
```

## 2. Docker容器部署

### 2.1 使用预构建镜像

```bash
# 拉取镜像
docker pull ghcr.io/your-org/ai-assistant:latest

# 创建配置目录
mkdir -p ./config ./data ./logs

# 复制配置文件
docker run --rm ghcr.io/your-org/ai-assistant:latest cat /app/.env.example > ./config/.env

# 编辑配置
vim ./config/.env

# 运行容器
docker run -d \
  --name ai-assistant \
  -p 8000:8000 \
  -p 50051:50051 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  ghcr.io/your-org/ai-assistant:latest
```

### 2.2 从源码构建

```bash
# 构建镜像
docker build -t ai-assistant .

# 运行容器
docker run -d \
  --name ai-assistant \
  -p 8000:8000 \
  -p 50051:50051 \
  -e GEMINI_API_KEY=your_api_key \
  ai-assistant
```

### 2.3 容器管理

```bash
# 查看容器状态
docker ps
docker logs ai-assistant

# 进入容器调试
docker exec -it ai-assistant bash

# 停止和重启
docker stop ai-assistant
docker start ai-assistant

# 更新容器
docker pull ghcr.io/your-org/ai-assistant:latest
docker stop ai-assistant
docker rm ai-assistant
# 重新运行 docker run 命令
```

## 3. Docker Compose部署

### 3.1 生产环境配置

使用提供的 `docker-compose.yml`:

```bash
# 创建必要目录
mkdir -p data logs config monitoring

# 配置环境变量
cp .env.example .env
vim .env

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f ai-assistant
```

### 3.2 自定义配置

创建 `docker-compose.override.yml` 来覆盖默认配置：

```yaml
version: '3.8'
services:
  ai-assistant:
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    ports:
      - "8080:8000"  # 更改端口映射
    
  # 添加额外服务
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ai_assistant
      POSTGRES_USER: ai_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 3.3 服务管理

```bash
# 启动特定服务
docker-compose up -d ai-assistant redis

# 重启服务
docker-compose restart ai-assistant

# 查看资源使用
docker-compose top

# 停止所有服务
docker-compose down

# 完全清理（包括数据卷）
docker-compose down -v
```

## 4. Kubernetes部署

### 4.1 准备工作

#### 创建命名空间
```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-assistant
  labels:
    name: ai-assistant
```

```bash
kubectl apply -f namespace.yaml
```

#### 创建配置映射
```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-assistant-config
  namespace: ai-assistant
data:
  .env: |
    HOST=0.0.0.0
    PORT=8000
    GRPC_PORT=50051
    LOG_LEVEL=INFO
    WORKERS=4
    DEBUG=false
```

#### 创建密钥
```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ai-assistant-secrets
  namespace: ai-assistant
type: Opaque
data:
  gemini-api-key: <base64_encoded_api_key>
  database-password: <base64_encoded_password>
```

```bash
# 应用配置
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
```

### 4.2 应用部署

#### 部署AI Assistant服务
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-assistant
  namespace: ai-assistant
  labels:
    app: ai-assistant
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-assistant
  template:
    metadata:
      labels:
        app: ai-assistant
    spec:
      containers:
      - name: ai-assistant
        image: ghcr.io/your-org/ai-assistant:latest
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 50051
          name: grpc
        env:
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-assistant-secrets
              key: gemini-api-key
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: data
          mountPath: /app/data
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: ai-assistant-config
      - name: data
        persistentVolumeClaim:
          claimName: ai-assistant-pvc
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: ai-assistant-service
  namespace: ai-assistant
spec:
  selector:
    app: ai-assistant
  ports:
  - name: http
    port: 80
    targetPort: 8000
  - name: grpc
    port: 50051
    targetPort: 50051
  type: ClusterIP
```

#### 创建持久化存储
```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ai-assistant-pvc
  namespace: ai-assistant
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard
```

#### 创建Ingress
```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-assistant-ingress
  namespace: ai-assistant
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - ai-assistant.yourdomain.com
    secretName: ai-assistant-tls
  rules:
  - host: ai-assistant.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ai-assistant-service
            port:
              number: 80
```

### 4.3 部署执行

```bash
# 应用所有配置
kubectl apply -f pvc.yaml
kubectl apply -f deployment.yaml
kubectl apply -f ingress.yaml

# 检查部署状态
kubectl get pods -n ai-assistant
kubectl get services -n ai-assistant
kubectl get ingress -n ai-assistant

# 查看日志
kubectl logs -f deployment/ai-assistant -n ai-assistant

# 端口转发测试
kubectl port-forward service/ai-assistant-service 8000:80 -n ai-assistant
```

### 4.4 扩缩容管理

#### 手动扩缩容
```bash
# 扩容到5个副本
kubectl scale deployment ai-assistant --replicas=5 -n ai-assistant

# 查看扩容状态
kubectl get pods -n ai-assistant -w
```

#### 水平自动扩缩容
```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-assistant-hpa
  namespace: ai-assistant
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-assistant
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

```bash
kubectl apply -f hpa.yaml
kubectl get hpa -n ai-assistant
```

## 5. 监控和运维

### 5.1 健康检查

#### 基础健康检查
```bash
# HTTP健康检查
curl -f http://localhost:8000/health

# 详细状态检查
curl http://localhost:8000/status
```

#### Kubernetes健康检查
```bash
# 检查Pod状态
kubectl get pods -n ai-assistant

# 检查服务端点
kubectl get endpoints -n ai-assistant

# 查看事件
kubectl get events -n ai-assistant --sort-by='.lastTimestamp'
```

### 5.2 日志管理

#### 日志收集
```bash
# Docker日志
docker logs ai-assistant

# Kubernetes日志
kubectl logs -f deployment/ai-assistant -n ai-assistant

# 日志聚合（如果配置了ELK）
# 访问Kibana仪表板查看日志
```

#### 日志轮转配置
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
```

### 5.3 性能监控

#### 系统指标
```bash
# CPU和内存使用
docker stats ai-assistant

# Kubernetes资源使用
kubectl top pods -n ai-assistant
kubectl top nodes
```

#### 应用指标
访问Prometheus和Grafana（如果配置）：
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

### 5.4 备份策略

#### 数据备份
```bash
# SQLite数据库备份
sqlite3 ai_assistant.db ".backup backup_$(date +%Y%m%d_%H%M%S).db"

# 配置文件备份
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/

# Kubernetes配置备份
kubectl get all -n ai-assistant -o yaml > ai-assistant-backup.yaml
```

#### 恢复流程
```bash
# 数据库恢复
sqlite3 ai_assistant.db ".restore backup_20231201_120000.db"

# 配置恢复
tar -xzf config_backup_20231201.tar.gz

# Kubernetes恢复
kubectl apply -f ai-assistant-backup.yaml
```

## 6. 安全配置

### 6.1 网络安全

#### 防火墙配置
```bash
# 仅开放必要端口
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw allow 8000  # AI Assistant API
ufw enable
```

#### TLS配置
使用Let's Encrypt获取SSL证书：
```bash
# 安装certbot
sudo apt install certbot

# 获取证书
sudo certbot certonly --standalone -d ai-assistant.yourdomain.com

# 配置nginx
server {
    listen 443 ssl;
    server_name ai-assistant.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/ai-assistant.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai-assistant.yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 6.2 访问控制

#### API密钥配置
```bash
# 在.env文件中设置
API_KEYS=["key1", "key2", "key3"]

# 或使用环境变量
export API_KEYS='["your-secret-api-key"]'
```

#### 网络策略（Kubernetes）
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ai-assistant-netpol
  namespace: ai-assistant
spec:
  podSelector:
    matchLabels:
      app: ai-assistant
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS出站
    - protocol: TCP
      port: 53   # DNS
    - protocol: UDP
      port: 53   # DNS
```

## 7. 故障排除

### 7.1 常见问题

#### 服务启动失败
```bash
# 检查端口占用
lsof -i :8000
lsof -i :50051

# 检查依赖
python -c "import fastapi, uvicorn, grpcio"

# 查看详细错误
./scripts/run_server.sh --debug --verbose
```

#### 性能问题
```bash
# 检查资源使用
htop
iostat 1

# 数据库性能
sqlite3 ai_assistant.db ".analyze"

# 网络延迟
ping api.openai.com
```

#### 内存泄漏
```bash
# 监控内存使用
watch -n 1 'ps aux | grep ai-assistant'

# 生成内存报告
python -m memory_profiler python/main.py
```

### 7.2 调试技巧

#### 启用调试模式
```bash
# 环境变量
export DEBUG=true
export LOG_LEVEL=DEBUG

# 配置文件
echo "DEBUG=true" >> .env
echo "LOG_LEVEL=DEBUG" >> .env
```

#### 使用调试工具
```bash
# Python调试
python -m pdb python/main.py

# 远程调试
python -m debugpy --listen 0.0.0.0:5678 python/main.py
```

## 8. 性能优化

### 8.1 系统优化

#### Linux内核参数
```bash
# 增加文件描述符限制
echo "* soft nofile 65535" >> /etc/security/limits.conf
echo "* hard nofile 65535" >> /etc/security/limits.conf

# 优化网络参数
echo "net.core.somaxconn = 65535" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65535" >> /etc/sysctl.conf
sysctl -p
```

#### 资源分配
```bash
# 设置CPU亲和性
taskset -c 0-3 ./ai_assistant_server

# 设置进程优先级
nice -n -10 python python/main.py
```

### 8.2 应用优化

#### 数据库优化
```sql
-- SQLite优化
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = memory;
```

#### 缓存配置
```python
# Redis缓存配置
REDIS_CONFIG = {
    "max_connections": 100,
    "connection_pool_kwargs": {
        "max_connections": 50,
        "retry_on_timeout": True
    }
}
```

---

通过本部署指南，您应该能够在各种环境中成功部署AI Assistant。如有问题，请参考[故障排除文档](troubleshooting.md)或联系技术支持团队。