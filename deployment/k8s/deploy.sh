#!/bin/bash

# Kubernetes部署脚本
# 用于自动化部署NEX应用到Kubernetes集群

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
NAMESPACE=${NAMESPACE:-nex}
ENVIRONMENT=${ENVIRONMENT:-production}
IMAGE_TAG=${IMAGE_TAG:-latest}
DRY_RUN=${DRY_RUN:-false}

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查必要工具
check_prerequisites() {
    log_info "检查部署前置条件..."
    
    # 检查kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl 未安装或不在PATH中"
        exit 1
    fi
    
    # 检查集群连接
    if ! kubectl cluster-info &> /dev/null; then
        log_error "无法连接到Kubernetes集群"
        exit 1
    fi
    
    # 检查Docker镜像
    if ! docker images | grep -q "nex.*${IMAGE_TAG}"; then
        log_warning "未找到Docker镜像 nex:${IMAGE_TAG}，将尝试构建..."
        build_image
    fi
    
    log_success "前置条件检查完成"
}

# 构建Docker镜像
build_image() {
    log_info "构建Docker镜像..."
    
    cd "$(dirname "$0")/.."
    
    if [ "$ENVIRONMENT" = "development" ]; then
        docker build -f Dockerfile.dev -t nex:${IMAGE_TAG} .
    else
        docker build -f Dockerfile -t nex:${IMAGE_TAG} .
    fi
    
    log_success "Docker镜像构建完成"
}

# 创建命名空间
create_namespace() {
    log_info "创建命名空间..."
    
    local cmd="kubectl apply -f k8s/namespace.yaml"
    if [ "$DRY_RUN" = "true" ]; then
        cmd="$cmd --dry-run=client"
    fi
    
    eval $cmd
    log_success "命名空间已创建/更新"
}

# 部署配置资源
deploy_configs() {
    log_info "部署配置资源..."
    
    local configs=("configmap.yaml" "secrets.yaml" "rbac.yaml")
    
    for config in "${configs[@]}"; do
        log_info "部署 $config..."
        local cmd="kubectl apply -f k8s/$config"
        if [ "$DRY_RUN" = "true" ]; then
            cmd="$cmd --dry-run=client"
        fi
        eval $cmd
    done
    
    log_success "配置资源部署完成"
}

# 部署存储资源
deploy_storage() {
    log_info "部署存储资源..."
    
    local cmd="kubectl apply -f k8s/pvc.yaml"
    if [ "$DRY_RUN" = "true" ]; then
        cmd="$cmd --dry-run=client"
    fi
    
    eval $cmd
    
    # 等待PVC绑定
    if [ "$DRY_RUN" != "true" ]; then
        log_info "等待PVC绑定..."
        kubectl wait --for=condition=Bound pvc/nex-data-pvc -n $NAMESPACE --timeout=300s
        kubectl wait --for=condition=Bound pvc/nex-logs-pvc -n $NAMESPACE --timeout=300s
    fi
    
    log_success "存储资源部署完成"
}

# 部署应用
deploy_application() {
    log_info "部署应用..."
    
    # 更新镜像标签
    sed -i.bak "s|image: nex:.*|image: nex:${IMAGE_TAG}|g" k8s/deployment.yaml
    
    local cmd="kubectl apply -f k8s/deployment.yaml"
    if [ "$DRY_RUN" = "true" ]; then
        cmd="$cmd --dry-run=client"
    fi
    
    eval $cmd
    
    # 恢复原文件
    mv k8s/deployment.yaml.bak k8s/deployment.yaml
    
    if [ "$DRY_RUN" != "true" ]; then
        log_info "等待应用就绪..."
        kubectl rollout status deployment/nex-app -n $NAMESPACE --timeout=600s
    fi
    
    log_success "应用部署完成"
}

# 部署服务
deploy_services() {
    log_info "部署服务..."
    
    local services=("service.yaml")
    
    for service in "${services[@]}"; do
        local cmd="kubectl apply -f k8s/$service"
        if [ "$DRY_RUN" = "true" ]; then
            cmd="$cmd --dry-run=client"
        fi
        eval $cmd
    done
    
    log_success "服务部署完成"
}

# 部署Ingress (可选)
deploy_ingress() {
    if [ -f "k8s/ingress.yaml" ]; then
        log_info "部署Ingress..."
        
        local cmd="kubectl apply -f k8s/ingress.yaml"
        if [ "$DRY_RUN" = "true" ]; then
            cmd="$cmd --dry-run=client"
        fi
        
        eval $cmd
        log_success "Ingress部署完成"
    else
        log_warning "Ingress配置文件不存在，跳过"
    fi
}

# 部署HPA (可选)
deploy_hpa() {
    if [ -f "k8s/hpa.yaml" ]; then
        log_info "部署水平扩缩容..."
        
        local cmd="kubectl apply -f k8s/hpa.yaml"
        if [ "$DRY_RUN" = "true" ]; then
            cmd="$cmd --dry-run=client"
        fi
        
        eval $cmd
        log_success "HPA部署完成"
    else
        log_warning "HPA配置文件不存在，跳过"
    fi
}

# 验证部署
verify_deployment() {
    if [ "$DRY_RUN" = "true" ]; then
        log_info "DRY_RUN模式，跳过验证"
        return
    fi
    
    log_info "验证部署状态..."
    
    # 检查Pod状态
    log_info "检查Pod状态..."
    kubectl get pods -n $NAMESPACE -l app=nex
    
    # 检查服务状态
    log_info "检查服务状态..."
    kubectl get svc -n $NAMESPACE
    
    # 健康检查
    log_info "执行健康检查..."
    local pod_name=$(kubectl get pods -n $NAMESPACE -l app=nex -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$pod_name" ]; then
        log_info "测试Pod连接..."
        kubectl exec -n $NAMESPACE $pod_name -- curl -f http://localhost:8080/health || {
            log_warning "健康检查失败，查看日志..."
            kubectl logs -n $NAMESPACE $pod_name --tail=50
        }
    fi
    
    log_success "部署验证完成"
}

# 显示部署信息
show_deployment_info() {
    if [ "$DRY_RUN" = "true" ]; then
        return
    fi
    
    log_info "部署信息："
    echo "----------------------------------------"
    echo "命名空间: $NAMESPACE"
    echo "环境: $ENVIRONMENT"
    echo "镜像标签: $IMAGE_TAG"
    echo ""
    
    log_info "获取服务访问信息..."
    kubectl get svc -n $NAMESPACE
    
    echo ""
    log_info "获取Ingress信息..."
    kubectl get ingress -n $NAMESPACE 2>/dev/null || log_warning "未配置Ingress"
    
    echo ""
    log_info "获取Pod状态..."
    kubectl get pods -n $NAMESPACE -l app=nex
}

# 清理部署
cleanup_deployment() {
    log_warning "开始清理部署..."
    
    read -p "确认要删除 $NAMESPACE 命名空间中的所有资源吗？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete namespace $NAMESPACE --ignore-not-found=true
        log_success "清理完成"
    else
        log_info "清理已取消"
    fi
}

# 主函数
main() {
    local action=${1:-deploy}
    
    case $action in
        "deploy")
            log_info "开始部署NEX应用到Kubernetes..."
            check_prerequisites
            create_namespace
            deploy_configs
            deploy_storage
            deploy_application
            deploy_services
            deploy_ingress
            deploy_hpa
            verify_deployment
            show_deployment_info
            log_success "部署完成！"
            ;;
        "cleanup")
            cleanup_deployment
            ;;
        "verify")
            verify_deployment
            ;;
        "info")
            show_deployment_info
            ;;
        *)
            echo "用法: $0 [deploy|cleanup|verify|info]"
            echo ""
            echo "环境变量："
            echo "  NAMESPACE    - Kubernetes命名空间 (默认: nex)"
            echo "  ENVIRONMENT  - 部署环境 (默认: production)"
            echo "  IMAGE_TAG    - Docker镜像标签 (默认: latest)"
            echo "  DRY_RUN      - 预览模式 (默认: false)"
            echo ""
            echo "示例："
            echo "  $0 deploy                    # 部署应用"
            echo "  ENVIRONMENT=dev $0 deploy    # 部署到开发环境"
            echo "  DRY_RUN=true $0 deploy       # 预览部署"
            echo "  $0 cleanup                   # 清理部署"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"