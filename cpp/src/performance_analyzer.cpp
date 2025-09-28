#include "../include/performance_analyzer.hpp"
#include "../include/sys_manager.hpp"
#include <fstream>
#include <algorithm>
#include <numeric>
#include <sstream>
#include <iomanip>

namespace ai_assistant {

class PerformanceAnalyzer::Impl {
public:
    Impl() : analyzing_(false), thresholds_() {}
    
    ~Impl() {
        stop_analysis();
    }
    
    bool start_analysis(std::chrono::milliseconds interval) {
        if (analyzing_) {
            return true;
        }
        
        collection_interval_ = interval;
        analyzing_ = true;
        
        analysis_thread_ = std::thread([this]() {
            while (analyzing_) {
                collect_metrics();
                std::this_thread::sleep_for(collection_interval_);
            }
        });
        
        Logger::info("Performance analysis started");
        return true;
    }
    
    void stop_analysis() {
        if (!analyzing_) return;
        
        analyzing_ = false;
        if (analysis_thread_.joinable()) {
            analysis_thread_.join();
        }
        
        Logger::info("Performance analysis stopped");
    }
    
    PerformanceMetrics get_current_metrics() const {
        std::lock_guard<std::shared_mutex> lock(metrics_mutex_);
        return current_metrics_;
    }
    
    std::vector<PerformanceMetrics> get_historical_metrics(size_t count) const {
        std::shared_lock<std::shared_mutex> lock(metrics_mutex_);
        
        size_t start_idx = 0;
        if (metrics_history_.size() > count) {
            start_idx = metrics_history_.size() - count;
        }
        
        return std::vector<PerformanceMetrics>(
            metrics_history_.begin() + start_idx,
            metrics_history_.end()
        );
    }
    
    BottleneckAnalysis analyze_bottlenecks() const {
        BottleneckAnalysis analysis;
        analysis.severity_score = 0.0;
        analysis.primary_bottleneck = BottleneckType::NONE;
        
        auto metrics = get_current_metrics();
        std::vector<std::pair<BottleneckType, double>> bottlenecks;
        
        // CPU瓶颈分析
        if (metrics.cpu_usage_percent > 80.0) {
            bottlenecks.emplace_back(BottleneckType::CPU_BOUND, metrics.cpu_usage_percent / 100.0);
        }
        
        // 内存瓶颈分析
        double memory_usage_ratio = static_cast<double>(metrics.memory_usage_mb) / (8 * 1024); // 假设8GB总内存
        if (memory_usage_ratio > 0.85) {
            bottlenecks.emplace_back(BottleneckType::MEMORY_BOUND, memory_usage_ratio);
        }
        
        // GPU瓶颈分析
        if (metrics.gpu_usage_percent > 90.0) {
            bottlenecks.emplace_back(BottleneckType::GPU_BOUND, metrics.gpu_usage_percent / 100.0);
        }
        
        // 并发瓶颈分析
        if (metrics.concurrent_connections > 100) {
            double concurrency_ratio = static_cast<double>(metrics.concurrent_connections) / 200.0;
            bottlenecks.emplace_back(BottleneckType::CONCURRENCY_BOUND, concurrency_ratio);
        }
        
        // 找到主要瓶颈
        if (!bottlenecks.empty()) {
            std::sort(bottlenecks.begin(), bottlenecks.end(), 
                     [](const auto& a, const auto& b) { return a.second > b.second; });
            
            analysis.primary_bottleneck = bottlenecks[0].first;
            analysis.severity_score = bottlenecks[0].second;
            
            if (bottlenecks.size() > 1) {
                analysis.secondary_bottleneck = bottlenecks[1].first;
            }
        }
        
        generate_recommendations(analysis);
        return analysis;
    }

private:
    std::atomic<bool> analyzing_;
    std::chrono::milliseconds collection_interval_;
    std::thread analysis_thread_;
    
    mutable std::shared_mutex metrics_mutex_;
    PerformanceMetrics current_metrics_;
    std::vector<PerformanceMetrics> metrics_history_;
    
    PerformanceThresholds thresholds_;
    std::unordered_map<std::string, PerformanceCallback> callbacks_;
    
    SystemManager sys_manager_;
    
    void collect_metrics() {
        PerformanceMetrics metrics;
        metrics.timestamp = std::chrono::steady_clock::now();
        
        // 获取系统信息
        auto sys_info = sys_manager_.get_system_info();
        metrics.cpu_usage_percent = sys_info.cpu_usage;
        metrics.memory_usage_mb = static_cast<size_t>((sys_info.memory_total_gb - sys_info.memory_free_gb) * 1024);
        metrics.gpu_usage_percent = sys_info.gpu_usage;
        metrics.gpu_memory_mb = static_cast<size_t>(sys_info.gpu_memory_usage * 1024);
        
        // TODO: 添加其他指标收集逻辑
        metrics.active_sessions = 0;
        metrics.avg_response_time = std::chrono::milliseconds(0);
        metrics.requests_per_second = 0;
        metrics.error_rate_percent = 0.0;
        metrics.concurrent_connections = 0;
        metrics.throughput_mbps = 0.0;
        
        {
            std::lock_guard<std::shared_mutex> lock(metrics_mutex_);
            current_metrics_ = metrics;
            metrics_history_.push_back(metrics);
            
            // 保留最近1000个记录
            if (metrics_history_.size() > 1000) {
                metrics_history_.erase(metrics_history_.begin());
            }
        }
        
        // 触发回调
        for (const auto& [name, callback] : callbacks_) {
            try {
                callback(metrics);
            } catch (const std::exception& e) {
                Logger::warning("Performance callback '" + name + "' failed: " + e.what());
            }
        }
    }
    
    void generate_recommendations(BottleneckAnalysis& analysis) const {
        switch (analysis.primary_bottleneck) {
            case BottleneckType::CPU_BOUND:
                analysis.description = "系统CPU使用率过高，影响处理性能";
                analysis.recommendations = {
                    "启用GPU加速推理",
                    "优化算法复杂度",
                    "增加CPU核心数量",
                    "使用异步处理减少CPU阻塞"
                };
                break;
                
            case BottleneckType::MEMORY_BOUND:
                analysis.description = "系统内存使用率过高，可能导致性能下降";
                analysis.recommendations = {
                    "实现内存池管理",
                    "优化内存分配策略",
                    "清理不必要的缓存数据",
                    "增加系统内存容量"
                };
                break;
                
            case BottleneckType::GPU_BOUND:
                analysis.description = "GPU资源使用率过高，推理性能受限";
                analysis.recommendations = {
                    "优化GPU内存使用",
                    "实现批量推理",
                    "使用模型量化技术",
                    "添加更多GPU设备"
                };
                break;
                
            case BottleneckType::CONCURRENCY_BOUND:
                analysis.description = "并发连接数过多，系统处理能力不足";
                analysis.recommendations = {
                    "实现连接池管理",
                    "增加异步处理能力",
                    "使用负载均衡",
                    "优化线程池配置"
                };
                break;
                
            default:
                analysis.description = "系统运行正常，未检测到明显瓶颈";
                analysis.recommendations = {"继续监控系统性能指标"};
                break;
        }
    }
};

// PerformanceAnalyzer公共接口实现
PerformanceAnalyzer::PerformanceAnalyzer() : pimpl_(std::make_unique<Impl>()) {}
PerformanceAnalyzer::~PerformanceAnalyzer() = default;

bool PerformanceAnalyzer::start_analysis(std::chrono::milliseconds interval) {
    return pimpl_->start_analysis(interval);
}

void PerformanceAnalyzer::stop_analysis() {
    pimpl_->stop_analysis();
}

PerformanceMetrics PerformanceAnalyzer::get_current_metrics() const {
    return pimpl_->get_current_metrics();
}

std::vector<PerformanceMetrics> PerformanceAnalyzer::get_historical_metrics(size_t count) const {
    return pimpl_->get_historical_metrics(count);
}

BottleneckAnalysis PerformanceAnalyzer::analyze_bottlenecks() const {
    return pimpl_->analyze_bottlenecks();
}

} // namespace ai_assistant