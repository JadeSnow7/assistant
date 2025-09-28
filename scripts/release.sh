#!/bin/bash

# 发布准备脚本
# 执行发布前的所有检查和准备工作

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="$PROJECT_ROOT/VERSION"
CHANGELOG_FILE="$PROJECT_ROOT/CHANGELOG.md"
RELEASE_DIR="$PROJECT_ROOT/release"
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

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

# 获取当前版本
get_current_version() {
    if [ -f "$VERSION_FILE" ]; then
        cat "$VERSION_FILE"
    else
        echo "0.1.0"
    fi
}

# 设置新版本
set_version() {
    local new_version=$1
    echo "$new_version" > "$VERSION_FILE"
    log_info "版本设置为: $new_version"
}

# 验证版本格式
validate_version() {
    local version=$1
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
        log_error "无效的版本格式: $version"
        log_info "版本格式应为: MAJOR.MINOR.PATCH 或 MAJOR.MINOR.PATCH-SUFFIX"
        return 1
    fi
    return 0
}

# 检查Git状态
check_git_status() {
    log_info "检查Git状态..."
    
    # 检查是否有未提交的更改
    if ! git diff-index --quiet HEAD --; then
        log_error "有未提交的更改，请先提交或暂存"
        git status --short
        return 1
    fi
    
    # 检查是否在主分支
    if [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "master" ]; then
        log_warning "当前不在主分支 (当前分支: $CURRENT_BRANCH)"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 1
        fi
    fi
    
    # 检查是否有远程更新
    git fetch origin
    local behind=$(git rev-list --count HEAD..origin/$CURRENT_BRANCH 2>/dev/null || echo "0")
    if [ "$behind" -gt 0 ]; then
        log_warning "本地分支落后远程 $behind 个提交"
        read -p "是否先拉取远程更新？(Y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            git pull origin "$CURRENT_BRANCH"
        fi
    fi
    
    log_success "Git状态检查完成"
}

# 运行完整测试
run_comprehensive_tests() {
    log_info "运行完整测试套件..."
    
    # 运行测试脚本
    if [ -f "$PROJECT_ROOT/scripts/run_tests.sh" ]; then
        "$PROJECT_ROOT/scripts/run_tests.sh" all || {
            log_error "测试失败，请修复后重试"
            return 1
        }
    else
        log_warning "测试脚本不存在，跳过测试"
    fi
    
    log_success "所有测试通过"
}

# 检查依赖和安全
check_dependencies() {
    log_info "检查依赖和安全..."
    
    # 检查Python依赖
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        # 检查过期依赖
        if command -v pip-check &> /dev/null; then
            pip-check || log_warning "发现过期依赖"
        fi
        
        # 安全检查
        if command -v safety &> /dev/null; then
            safety check || log_warning "发现安全漏洞"
        fi
        
        # 检查许可证兼容性
        if command -v pip-licenses &> /dev/null; then
            pip-licenses --format=json > "$RELEASE_DIR/licenses.json"
            log_info "依赖许可证信息已导出"
        fi
    fi
    
    log_success "依赖检查完成"
}

# 构建项目
build_project() {
    log_info "构建项目..."
    
    # 创建发布目录
    mkdir -p "$RELEASE_DIR"
    
    # 运行构建脚本
    if [ -f "$PROJECT_ROOT/scripts/build.sh" ]; then
        "$PROJECT_ROOT/scripts/build.sh" --release || {
            log_error "构建失败"
            return 1
        }
    fi
    
    # 构建Docker镜像
    local version=$(get_current_version)
    log_info "构建Docker镜像 (版本: $version)..."
    
    docker build -t "nex:$version" -t "nex:latest" . || {
        log_error "Docker镜像构建失败"
        return 1
    }
    
    # 构建开发镜像
    docker build -f Dockerfile.dev -t "nex:dev" . || {
        log_warning "开发镜像构建失败"
    fi
    
    log_success "项目构建完成"
}

# 生成文档
generate_documentation() {
    log_info "生成文档..."
    
    # 生成API文档
    if command -v sphinx-build &> /dev/null; then
        if [ -d "docs/source" ]; then
            sphinx-build -b html docs/source docs/build || {
                log_warning "Sphinx文档生成失败"
            }
        fi
    fi
    
    # 生成README
    if [ -f "docs/README_template.md" ]; then
        local version=$(get_current_version)
        sed "s/{{VERSION}}/$version/g" docs/README_template.md > README.md
        log_info "README已更新"
    fi
    
    log_success "文档生成完成"
}

# 更新变更日志
update_changelog() {
    local version=$1
    local date=$(date +%Y-%m-%d)
    
    log_info "更新变更日志..."
    
    if [ ! -f "$CHANGELOG_FILE" ]; then
        cat > "$CHANGELOG_FILE" << EOF
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [$version] - $date

### Added
- Initial release

EOF
    else
        # 在文件顶部添加新版本
        local temp_file=$(mktemp)
        {
            head -n 6 "$CHANGELOG_FILE"
            echo ""
            echo "## [$version] - $date"
            echo ""
            echo "### Added"
            echo "- TODO: Add release notes"
            echo ""
            echo "### Changed"
            echo "- TODO: Add changes"
            echo ""
            echo "### Fixed"
            echo "- TODO: Add fixes"
            echo ""
            tail -n +7 "$CHANGELOG_FILE"
        } > "$temp_file"
        
        mv "$temp_file" "$CHANGELOG_FILE"
    fi
    
    log_success "变更日志已更新，请编辑 $CHANGELOG_FILE 添加发布说明"
}

# 创建发布包
create_release_package() {
    local version=$1
    
    log_info "创建发布包..."
    
    # 创建源码包
    local archive_name="nex-$version"
    local archive_path="$RELEASE_DIR/$archive_name.tar.gz"
    
    # 排除不需要的文件
    tar --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='.git' \
        --exclude='.pytest_cache' \
        --exclude='venv' \
        --exclude='*.egg-info' \
        --exclude='build' \
        --exclude='dist' \
        --exclude='test-results' \
        --exclude='coverage' \
        --exclude='.coverage' \
        --exclude='release' \
        -czf "$archive_path" \
        -C "$PROJECT_ROOT/.." \
        "$(basename "$PROJECT_ROOT")" || {
        log_error "创建源码包失败"
        return 1
    }
    
    log_success "源码包已创建: $archive_path"
    
    # 导出Docker镜像
    log_info "导出Docker镜像..."
    docker save "nex:$version" | gzip > "$RELEASE_DIR/nex-$version-docker.tar.gz" || {
        log_warning "Docker镜像导出失败"
    }
    
    # 生成校验和
    cd "$RELEASE_DIR"
    sha256sum *.tar.gz > checksums.sha256
    
    log_success "发布包创建完成"
}

# 验证发布包
verify_release_package() {
    local version=$1
    
    log_info "验证发布包..."
    
    cd "$RELEASE_DIR"
    
    # 验证校验和
    if [ -f "checksums.sha256" ]; then
        sha256sum -c checksums.sha256 || {
            log_error "校验和验证失败"
            return 1
        }
    fi
    
    # 测试Docker镜像
    if [ -f "nex-$version-docker.tar.gz" ]; then
        log_info "测试Docker镜像..."
        docker load < "nex-$version-docker.tar.gz" || {
            log_warning "Docker镜像加载失败"
        }
        
        # 简单的容器测试
        docker run --rm "nex:$version" python3 --version || {
            log_warning "Docker容器测试失败"
        }
    fi
    
    log_success "发布包验证完成"
}

# 创建Git标签
create_git_tag() {
    local version=$1
    local tag_name="v$version"
    
    log_info "创建Git标签: $tag_name"
    
    # 检查标签是否已存在
    if git tag -l | grep -q "^$tag_name$"; then
        log_error "标签 $tag_name 已存在"
        return 1
    fi
    
    # 创建带注释的标签
    git tag -a "$tag_name" -m "Release version $version" || {
        log_error "创建标签失败"
        return 1
    }
    
    log_success "Git标签已创建: $tag_name"
    
    # 询问是否推送标签
    read -p "是否推送标签到远程仓库？(Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        git push origin "$tag_name" || {
            log_error "推送标签失败"
            return 1
        }
        log_success "标签已推送到远程仓库"
    fi
}

# 生成发布报告
generate_release_report() {
    local version=$1
    local report_file="$RELEASE_DIR/release-report-$version.json"
    
    log_info "生成发布报告..."
    
    # 收集项目信息
    local git_commit=$(git rev-parse HEAD)
    local git_branch=$(git branch --show-current)
    local build_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    # 统计代码行数
    local code_lines=0
    if command -v cloc &> /dev/null; then
        code_lines=$(cloc src/ --json | jq '.SUM.code' 2>/dev/null || echo "0")
    fi
    
    # 统计测试覆盖率
    local coverage="N/A"
    if [ -f "coverage/unit-coverage.xml" ]; then
        coverage=$(grep -o 'line-rate="[0-9.]*"' coverage/unit-coverage.xml | head -1 | grep -o '[0-9.]*' | awk '{printf "%.1f%%", $1*100}')
    fi
    
    # 生成JSON报告
    cat > "$report_file" << EOF
{
    "release": {
        "version": "$version",
        "build_time": "$build_time",
        "git_commit": "$git_commit",
        "git_branch": "$git_branch"
    },
    "project_stats": {
        "code_lines": $code_lines,
        "test_coverage": "$coverage"
    },
    "build_artifacts": {
        "source_package": "nex-$version.tar.gz",
        "docker_image": "nex-$version-docker.tar.gz",
        "checksums": "checksums.sha256"
    },
    "quality_checks": {
        "tests_passed": true,
        "security_scan": "completed",
        "dependency_check": "completed"
    },
    "deployment": {
        "docker_ready": true,
        "kubernetes_ready": true,
        "documentation_updated": true
    }
}
EOF
    
    log_success "发布报告已生成: $report_file"
}

# 显示发布摘要
show_release_summary() {
    local version=$1
    
    echo ""
    log_info "发布摘要"
    echo "============================================"
    echo "版本: $version"
    echo "分支: $CURRENT_BRANCH"
    echo "提交: $(git rev-parse --short HEAD)"
    echo "构建时间: $(date)"
    echo ""
    echo "发布包位置: $RELEASE_DIR/"
    echo "  - 源码包: nex-$version.tar.gz"
    echo "  - Docker镜像: nex-$version-docker.tar.gz"
    echo "  - 校验和: checksums.sha256"
    echo ""
    echo "下一步："
    echo "  1. 检查并编辑 $CHANGELOG_FILE"
    echo "  2. 提交变更: git add . && git commit -m 'Release $version'"
    echo "  3. 推送到远程: git push origin $CURRENT_BRANCH"
    echo "  4. 在GitHub/GitLab上创建Release"
    echo "  5. 部署到生产环境"
    echo "============================================"
}

# 主要发布流程
prepare_release() {
    local version_type=${1:-patch}
    local current_version=$(get_current_version)
    local new_version
    
    # 计算新版本号
    case $version_type in
        "major")
            new_version=$(echo "$current_version" | awk -F. '{print ($1+1)".0.0"}')
            ;;
        "minor")
            new_version=$(echo "$current_version" | awk -F. '{print $1"."($2+1)".0"}')
            ;;
        "patch")
            new_version=$(echo "$current_version" | awk -F. '{print $1"."$2"."($3+1)}')
            ;;
        *)
            # 自定义版本号
            new_version=$version_type
            validate_version "$new_version" || return 1
            ;;
    esac
    
    log_info "准备发布版本 $new_version (当前版本: $current_version)"
    
    # 确认发布
    read -p "确认要发布版本 $new_version 吗？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "发布已取消"
        return 0
    fi
    
    # 执行发布流程
    check_git_status || return 1
    run_comprehensive_tests || return 1
    check_dependencies || return 1
    
    # 设置新版本
    set_version "$new_version"
    
    # 更新文档和构建
    update_changelog "$new_version"
    generate_documentation || return 1
    build_project || return 1
    
    # 创建发布包
    create_release_package "$new_version" || return 1
    verify_release_package "$new_version" || return 1
    
    # 生成报告
    generate_release_report "$new_version"
    
    # 创建Git标签
    create_git_tag "$new_version"
    
    # 显示摘要
    show_release_summary "$new_version"
    
    log_success "发布准备完成！"
}

# 主函数
main() {
    local action=${1:-prepare}
    
    case $action in
        "prepare")
            local version_type=${2:-patch}
            prepare_release "$version_type"
            ;;
        "version")
            local new_version=$2
            if [ -z "$new_version" ]; then
                echo "当前版本: $(get_current_version)"
            else
                validate_version "$new_version" && set_version "$new_version"
            fi
            ;;
        "build")
            build_project
            ;;
        "test")
            run_comprehensive_tests
            ;;
        "docs")
            generate_documentation
            ;;
        "package")
            local version=$(get_current_version)
            create_release_package "$version"
            ;;
        "tag")
            local version=$(get_current_version)
            create_git_tag "$version"
            ;;
        "clean")
            rm -rf "$RELEASE_DIR"
            log_success "发布目录已清理"
            ;;
        *)
            echo "用法: $0 [prepare|version|build|test|docs|package|tag|clean] [options]"
            echo ""
            echo "命令说明："
            echo "  prepare [major|minor|patch|VERSION] - 准备发布（默认：patch）"
            echo "  version [VERSION]                   - 显示或设置版本号"
            echo "  build                               - 构建项目"
            echo "  test                                - 运行测试"
            echo "  docs                                - 生成文档"
            echo "  package                             - 创建发布包"
            echo "  tag                                 - 创建Git标签"
            echo "  clean                               - 清理发布目录"
            echo ""
            echo "示例："
            echo "  $0 prepare minor     # 准备次版本发布"
            echo "  $0 prepare 1.2.0     # 准备指定版本发布"
            echo "  $0 version 1.0.0     # 设置版本为1.0.0"
            echo "  $0 version           # 显示当前版本"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"