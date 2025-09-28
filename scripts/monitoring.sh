#!/bin/bash

# 监控系统启动脚本
# 用于启动完整的监控堆栈

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
COMPOSE_FILE=${COMPOSE_FILE:-monitoring/docker-compose.yml}
MONITORING_DIR=${MONITORING_DIR:-monitoring}
PROJECT_NAME=${PROJECT_NAME:-nex-monitoring}

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

# 检查前置条件
check_prerequisites() {
    log_info "检查前置条件..."
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
    
    # 检查配置文件
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Docker Compose 文件不存在: $COMPOSE_FILE"
        exit 1
    fi
    
    # 检查监控配置目录
    if [ ! -d "$MONITORING_DIR" ]; then
        log_error "监控配置目录不存在: $MONITORING_DIR"
        exit 1
    fi
    
    log_success "前置条件检查完成"
}

# 创建必要的目录和权限
setup_directories() {
    log_info "设置目录和权限..."
    
    # 创建数据目录
    mkdir -p \
        monitoring/data/prometheus \
        monitoring/data/grafana \
        monitoring/data/alertmanager \
        monitoring/data/loki \
        logs
    
    # 设置权限
    # Grafana 需要 472 用户权限
    sudo chown -R 472:472 monitoring/data/grafana 2>/dev/null || true
    
    # Prometheus 需要 65534 用户权限
    sudo chown -R 65534:65534 monitoring/data/prometheus 2>/dev/null || true
    
    # AlertManager 需要 65534 用户权限
    sudo chown -R 65534:65534 monitoring/data/alertmanager 2>/dev/null || true
    
    # Loki 需要 10001 用户权限
    sudo chown -R 10001:10001 monitoring/data/loki 2>/dev/null || true
    
    log_success "目录设置完成"
}

# 生成默认配置
generate_configs() {
    log_info "生成默认配置..."
    
    # 如果不存在监控配置，创建基本配置
    if [ ! -f "monitoring/prometheus/prometheus.yml" ]; then
        log_warning "Prometheus 配置不存在，将使用默认配置"
    fi
    
    if [ ! -f "monitoring/alertmanager/alertmanager.yml" ]; then
        log_warning "AlertManager 配置不存在，将使用默认配置"
    fi
    
    # 创建 Grafana 配置目录
    mkdir -p monitoring/grafana/provisioning/{datasources,dashboards}
    
    log_success "配置生成完成"
}

# 启动监控服务
start_monitoring() {
    log_info "启动监控服务..."
    
    # 使用 Docker Compose 启动
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d
    else
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d
    fi
    
    log_success "监控服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."
    
    local services=(
        "prometheus:9090"
        "grafana:3000"
        "alertmanager:9093"
        "loki:3100"
    )
    
    for service in "${services[@]}"; do
        local name=$(echo $service | cut -d: -f1)
        local port=$(echo $service | cut -d: -f2)
        
        log_info "等待 $name 服务..."
        local timeout=60
        local count=0
        
        while ! curl -f -s "http://localhost:$port" >/dev/null 2>&1; do
            if [ $count -ge $timeout ]; then
                log_error "$name 服务启动超时"
                return 1
            fi
            sleep 1
            ((count++))
        done
        
        log_success "$name 服务已就绪"
    done
}

# 配置 Grafana
setup_grafana() {
    log_info "配置 Grafana..."
    
    # 等待 Grafana 完全启动
    sleep 10
    
    # 设置默认密码 (如果需要)
    local grafana_url="http://admin:admin123@localhost:3000"
    
    # 检查数据源
    if curl -f -s "$grafana_url/api/datasources" | grep -q "Prometheus"; then
        log_success "Prometheus 数据源已配置"
    else
        log_warning "请手动配置 Prometheus 数据源"
    fi
    
    log_success "Grafana 配置完成"
}

# 显示访问信息
show_access_info() {
    log_info "服务访问信息："
    echo "----------------------------------------"
    echo "🔍 Prometheus:   http://localhost:9090"
    echo "📊 Grafana:      http://localhost:3000 (admin/admin123)"
    echo "🚨 AlertManager: http://localhost:9093"
    echo "📋 Loki:         http://localhost:3100"
    echo "🕸️  Jaeger:       http://localhost:16686"
    echo "📈 Node Exporter: http://localhost:9100"
    echo "🐳 cAdvisor:      http://localhost:8080"
    echo "----------------------------------------"
    echo ""
    echo "📖 快速操作："
    echo "  查看服务状态: docker-compose -f $COMPOSE_FILE ps"
    echo "  查看服务日志: docker-compose -f $COMPOSE_FILE logs -f [service]"
    echo "  停止监控:     ./scripts/monitoring.sh stop"
    echo "  重启监控:     ./scripts/monitoring.sh restart"
}

# 停止监控服务
stop_monitoring() {
    log_info "停止监控服务..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
    else
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
    fi
    
    log_success "监控服务已停止"
}

# 重启监控服务
restart_monitoring() {
    log_info "重启监控服务..."
    stop_monitoring
    sleep 2
    start_services
}

# 查看服务状态
status_monitoring() {
    log_info "监控服务状态："
    
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    else
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    fi
}

# 查看服务日志
logs_monitoring() {
    local service=${1:-}
    
    if [ -n "$service" ]; then
        log_info "查看 $service 服务日志..."
        if command -v docker-compose &> /dev/null; then
            docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f "$service"
        else
            docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f "$service"
        fi
    else
        log_info "查看所有服务日志..."
        if command -v docker-compose &> /dev/null; then
            docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f
        else
            docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f
        fi
    fi
}

# 启动完整监控
start_services() {
    check_prerequisites
    setup_directories
    generate_configs
    start_monitoring
    wait_for_services
    setup_grafana
    show_access_info
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    local failed=0
    local services=(
        "prometheus:9090:/metrics"
        "grafana:3000:/api/health"
        "alertmanager:9093:/api/v1/status"
        "loki:3100:/ready"
    )
    
    for service in "${services[@]}"; do
        local name=$(echo $service | cut -d: -f1)
        local port=$(echo $service | cut -d: -f2)
        local path=$(echo $service | cut -d: -f3)
        
        if curl -f -s "http://localhost:$port$path" >/dev/null 2>&1; then
            log_success "$name 健康检查通过"
        else
            log_error "$name 健康检查失败"
            ((failed++))
        fi
    done
    
    if [ $failed -eq 0 ]; then
        log_success "所有服务健康检查通过"
        return 0
    else
        log_error "$failed 个服务健康检查失败"
        return 1
    fi
}

# 清理监控数据
cleanup_data() {
    log_warning "这将删除所有监控数据！"
    read -p "确认要继续吗？(y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "清理监控数据..."
        stop_monitoring
        sudo rm -rf monitoring/data/*/
        log_success "监控数据已清理"
    else
        log_info "清理已取消"
    fi
}

# 主函数
main() {
    local action=${1:-start}
    
    case $action in
        "start")
            start_services
            ;;
        "stop")
            stop_monitoring
            ;;
        "restart")
            restart_monitoring
            ;;
        "status")
            status_monitoring
            ;;
        "logs")
            logs_monitoring "${2:-}"
            ;;
        "health")
            health_check
            ;;
        "cleanup")
            cleanup_data
            ;;
        "info")
            show_access_info
            ;;
        *)
            echo "用法: $0 [start|stop|restart|status|logs|health|cleanup|info]"
            echo ""
            echo "命令说明："
            echo "  start    - 启动监控服务"
            echo "  stop     - 停止监控服务"
            echo "  restart  - 重启监控服务"
            echo "  status   - 查看服务状态"
            echo "  logs     - 查看服务日志 (可指定服务名)"
            echo "  health   - 执行健康检查"
            echo "  cleanup  - 清理监控数据"
            echo "  info     - 显示访问信息"
            echo ""
            echo "示例："
            echo "  $0 start                    # 启动监控"
            echo "  $0 logs prometheus          # 查看 Prometheus 日志"
            echo "  $0 health                   # 健康检查"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"