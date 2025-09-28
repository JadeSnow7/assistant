# Kubernetes 部署指南

本文档描述如何将 NEX 应用部署到 Kubernetes 集群。

## 前置条件

### 系统要求
- Kubernetes 集群 (版本 1.20+)
- kubectl 命令行工具
- Helm 3.0+ (可选，用于 Helm 部署)
- Docker 镜像仓库访问权限

### 集群组件 (可选但推荐)
- Ingress Controller (如 NGINX Ingress)
- Cert-Manager (用于自动 TLS 证书)
- Prometheus Operator (用于监控)
- StorageClass (用于持久化存储)

## 快速开始

### 1. 构建 Docker 镜像

```bash
# 构建生产镜像
docker build -t nex:latest .

# 构建开发镜像
docker build -f Dockerfile.dev -t nex:dev .

# 推送到镜像仓库
docker tag nex:latest your-registry.com/nex:latest
docker push your-registry.com/nex:latest
```

### 2. 使用脚本部署 (推荐)

```bash
# 部署到生产环境
./k8s/deploy.sh deploy

# 部署到开发环境
NAMESPACE=nex-dev ENVIRONMENT=development ./k8s/deploy.sh deploy

# 预览部署 (不实际执行)
DRY_RUN=true ./k8s/deploy.sh deploy
```

### 3. 手动部署

```bash
# 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 部署配置和密钥
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/rbac.yaml

# 部署存储
kubectl apply -f k8s/pvc.yaml

# 部署应用
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 部署 Ingress (可选)
kubectl apply -f k8s/ingress.yaml

# 部署自动扩缩容 (可选)
kubectl apply -f k8s/hpa.yaml
```

## Helm 部署

### 1. 安装

```bash
# 添加 Helm 仓库 (如果有)
helm repo add nex https://charts.nex.example.com
helm repo update

# 或者使用本地 Chart
cd helm

# 安装到生产环境
helm install nex . -n nex --create-namespace

# 安装到开发环境
helm install nex-dev . -n nex-dev --create-namespace \
  --set image.tag=dev \
  --set replicaCount=1 \
  --set autoscaling.enabled=false
```

### 2. 自定义配置

创建 `values-production.yaml`:

```yaml
# 生产环境配置
replicaCount: 3

image:
  tag: "v1.0.0"

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi

ingress:
  enabled: true
  hosts:
    - host: nex.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: nex-tls
      hosts:
        - nex.yourdomain.com

persistence:
  size: 50Gi

monitoring:
  enabled: true
```

应用配置：

```bash
helm install nex . -n nex --create-namespace \
  -f values-production.yaml
```

### 3. 升级和回滚

```bash
# 升级
helm upgrade nex . -n nex -f values-production.yaml

# 查看发布历史
helm history nex -n nex

# 回滚
helm rollback nex 1 -n nex
```

## 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `NEX_ENV` | 运行环境 | `production` |
| `NEX_HOST` | 绑定主机 | `0.0.0.0` |
| `NEX_PORT` | HTTP 端口 | `8000` |
| `NEX_GRPC_PORT` | gRPC 端口 | `50051` |
| `DATABASE_PATH` | 数据库路径 | `/app/data/nex.db` |
| `LOG_PATH` | 日志目录 | `/app/logs` |

### 密钥配置

在部署前，请更新 `k8s/secrets.yaml` 中的密钥值：

```bash
# 生成 base64 编码的密钥
echo -n "your-secret-key" | base64
```

### 存储配置

根据集群的存储类型，更新 `storageClassName`:

```yaml
# 使用默认存储类
storageClassName: ""

# 使用 SSD 存储类
storageClassName: "fast-ssd"

# 使用 NFS 存储类
storageClassName: "nfs-client"
```

## 网络配置

### Ingress 配置

更新 `k8s/ingress.yaml` 中的域名：

```yaml
spec:
  rules:
  - host: your-domain.com  # 替换为您的域名
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: nex-service
            port:
              number: 80
```

### TLS 证书

使用 cert-manager 自动获取证书：

```yaml
annotations:
  cert-manager.io/cluster-issuer: "letsencrypt-prod"
```

或手动配置证书：

```bash
kubectl create secret tls nex-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n nex
```

## 监控配置

### Prometheus 监控

如果集群安装了 Prometheus Operator：

```bash
# 部署 ServiceMonitor
kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: nex-monitor
  namespace: nex
spec:
  selector:
    matchLabels:
      app: nex
  endpoints:
  - port: http
    path: /metrics
EOF
```

### 日志收集

使用 Fluentd 或 Filebeat 收集日志：

```yaml
# 添加日志收集注解
annotations:
  fluentd.io/parser: "json"
  co.elastic.logs/enabled: "true"
```

## 扩缩容配置

### 水平自动扩缩容 (HPA)

```bash
# 确保 metrics-server 已安装
kubectl top nodes

# 应用 HPA
kubectl apply -f k8s/hpa.yaml

# 查看 HPA 状态
kubectl get hpa -n nex
```

### 垂直自动扩缩容 (VPA)

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: nex-vpa
  namespace: nex
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nex-app
  updatePolicy:
    updateMode: "Auto"
```

## 安全配置

### 网络策略

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: nex-netpol
  namespace: nex
spec:
  podSelector:
    matchLabels:
      app: nex
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
```

### Pod 安全策略

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: nex-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

## 故障排除

### 常见问题

1. **Pod 启动失败**
```bash
# 查看 Pod 状态
kubectl get pods -n nex

# 查看 Pod 详情
kubectl describe pod <pod-name> -n nex

# 查看日志
kubectl logs <pod-name> -n nex
```

2. **存储问题**
```bash
# 查看 PVC 状态
kubectl get pvc -n nex

# 查看存储类
kubectl get storageclass
```

3. **网络问题**
```bash
# 测试服务连接
kubectl run debug --image=busybox -it --rm --restart=Never -- sh
wget -qO- http://nex-service.nex.svc.cluster.local/health
```

4. **性能问题**
```bash
# 查看资源使用
kubectl top pods -n nex

# 查看 HPA 状态
kubectl get hpa -n nex

# 查看事件
kubectl get events -n nex --sort-by='.lastTimestamp'
```

### 调试工具

```bash
# 进入容器调试
kubectl exec -it <pod-name> -n nex -- /bin/bash

# 端口转发
kubectl port-forward svc/nex-service 8000:80 -n nex

# 查看配置
kubectl get configmap nex-config -n nex -o yaml
```

## 备份和恢复

### 数据备份

```bash
# 备份数据库
kubectl exec <pod-name> -n nex -- tar czf - /app/data | \
  kubectl cp -:/dev/stdin backup-$(date +%Y%m%d).tar.gz

# 使用 Velero 备份整个命名空间
velero backup create nex-backup --include-namespaces nex
```

### 数据恢复

```bash
# 恢复数据库
kubectl cp backup-20231201.tar.gz <pod-name>:/tmp/ -n nex
kubectl exec <pod-name> -n nex -- tar xzf /tmp/backup-20231201.tar.gz -C /

# 使用 Velero 恢复
velero restore create --from-backup nex-backup
```

## 维护操作

### 滚动更新

```bash
# 更新镜像
kubectl set image deployment/nex-app nex=nex:v1.1.0 -n nex

# 查看更新状态
kubectl rollout status deployment/nex-app -n nex

# 回滚更新
kubectl rollout undo deployment/nex-app -n nex
```

### 清理资源

```bash
# 使用脚本清理
./k8s/deploy.sh cleanup

# 手动清理
kubectl delete namespace nex

# 清理 Helm 发布
helm uninstall nex -n nex
kubectl delete namespace nex
```

## 最佳实践

1. **资源限制**: 始终设置资源请求和限制
2. **健康检查**: 配置存活性和就绪性探针
3. **安全**: 使用非 root 用户运行容器
4. **监控**: 部署监控和告警系统
5. **备份**: 定期备份重要数据
6. **测试**: 在生产环境部署前充分测试
7. **文档**: 维护部署和运维文档

更多信息请参考：
- [Kubernetes 官方文档](https://kubernetes.io/docs/)
- [Helm 文档](https://helm.sh/docs/)
- [项目 GitHub 仓库](https://github.com/your-org/nex)