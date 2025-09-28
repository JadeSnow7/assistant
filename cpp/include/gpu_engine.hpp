#pragma once

#include "common.hpp"
#include "performance_analyzer.hpp"
#include <cuda_runtime.h>
#include <cublas_v2.h>
#include <memory>
#include <vector>
#include <future>
#include <queue>

namespace ai_assistant {

// GPU设备信息
struct GPUDeviceInfo {
    int device_id;
    std::string name;
    size_t total_memory_mb;
    size_t free_memory_mb;
    int compute_capability_major;
    int compute_capability_minor;
    int multiprocessor_count;
    bool supports_tensor_cores;
};

// GPU内存池
class CUDAMemoryPool {
public:
    CUDAMemoryPool(size_t pool_size_mb = 1024);
    ~CUDAMemoryPool();
    
    // 分配GPU内存
    void* allocate(size_t size_bytes);
    
    // 释放GPU内存
    void deallocate(void* ptr);
    
    // 获取内存使用统计
    struct MemoryStats {
        size_t total_allocated;
        size_t peak_allocated;
        size_t current_free;
        double fragmentation_ratio;
    };
    MemoryStats get_memory_stats() const;
    
    // 内存整理
    void defragment();

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// GPU张量缓冲区
class TensorBuffer {
public:
    TensorBuffer(const std::vector<size_t>& shape, size_t element_size);
    ~TensorBuffer();
    
    // 复制数据到GPU
    void copy_from_host(const void* host_data, size_t size);
    
    // 复制数据到主机
    void copy_to_host(void* host_data, size_t size) const;
    
    // 获取GPU指针
    void* get_device_ptr() const;
    
    // 获取缓冲区大小
    size_t get_size_bytes() const;
    
    // 获取形状
    const std::vector<size_t>& get_shape() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// CUDA推理上下文
class CUDAInferenceContext {
public:
    CUDAInferenceContext(int device_id = 0);
    ~CUDAInferenceContext();
    
    // 初始化CUDA上下文
    bool initialize();
    
    // 清理资源
    void cleanup();
    
    // 获取CUDA流
    cudaStream_t get_stream() const;
    
    // 获取cuBLAS句柄
    cublasHandle_t get_cublas_handle() const;
    
    // 同步等待完成
    void synchronize();
    
    // 获取设备信息
    GPUDeviceInfo get_device_info() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// GPU加速模型引擎
class GPUModelEngine {
public:
    GPUModelEngine();
    ~GPUModelEngine();
    
    // 初始化GPU引擎
    bool initialize(const std::string& model_path, int device_id = 0);
    
    // 加载模型到GPU
    bool load_model_to_gpu(const std::string& model_path);
    
    // 单次推理（异步）
    std::future<InferenceResponse> inference_async_gpu(const InferenceRequest& request);
    
    // 批量推理
    std::vector<InferenceResponse> batch_inference_gpu(
        const std::vector<InferenceRequest>& requests
    );
    
    // 流式推理
    void inference_stream_gpu(const InferenceRequest& request, StreamCallback callback);
    
    // 预加载模型
    bool preload_model(const std::string& model_id);
    
    // 卸载模型
    bool unload_model(const std::string& model_id);
    
    // 获取支持的模型列表
    std::vector<std::string> get_supported_models() const;
    
    // 获取GPU使用统计
    struct GPUStats {
        double gpu_utilization_percent;
        size_t gpu_memory_used_mb;
        size_t gpu_memory_total_mb;
        std::chrono::milliseconds avg_inference_time;
        size_t completed_inferences;
        double throughput_inferences_per_sec;
    };
    GPUStats get_gpu_stats() const;
    
    // 优化GPU内存使用
    void optimize_gpu_memory();
    
    // 设置批处理大小
    void set_batch_size(size_t batch_size);
    
    // 启用混合精度
    void enable_mixed_precision(bool enable = true);
    
    // 健康检查
    bool is_gpu_healthy() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// GPU加速的推理任务队列
class GPUInferenceQueue {
public:
    GPUInferenceQueue(size_t max_queue_size = 1000);
    ~GPUInferenceQueue();
    
    // 提交推理任务
    std::future<InferenceResponse> submit_task(const InferenceRequest& request);
    
    // 批量提交任务
    std::vector<std::future<InferenceResponse>> submit_batch_tasks(
        const std::vector<InferenceRequest>& requests
    );
    
    // 启动处理队列
    bool start_processing(size_t worker_threads = 2);
    
    // 停止处理队列
    void stop_processing();
    
    // 获取队列统计
    struct QueueStats {
        size_t pending_tasks;
        size_t completed_tasks;
        size_t failed_tasks;
        std::chrono::milliseconds avg_wait_time;
        std::chrono::milliseconds avg_processing_time;
    };
    QueueStats get_queue_stats() const;
    
    // 清空队列
    void clear_queue();

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// CUDA工具函数
namespace cuda_utils {
    // 检查CUDA是否可用
    bool is_cuda_available();
    
    // 获取CUDA设备数量
    int get_device_count();
    
    // 获取所有GPU设备信息
    std::vector<GPUDeviceInfo> get_all_gpu_info();
    
    // 选择最优GPU设备
    int select_best_device();
    
    // 设置GPU设备
    bool set_device(int device_id);
    
    // 获取CUDA错误字符串
    std::string get_cuda_error_string(cudaError_t error);
    
    // 检查CUDA错误
    bool check_cuda_error(cudaError_t error, const std::string& operation);
    
    // 内存对齐工具
    size_t align_memory_size(size_t size, size_t alignment = 256);
    
    // GPU内存拷贝优化
    bool optimized_memcpy_h2d(void* dst, const void* src, size_t size, cudaStream_t stream = nullptr);
    bool optimized_memcpy_d2h(void* dst, const void* src, size_t size, cudaStream_t stream = nullptr);
    
    // GPU核函数启动配置计算
    dim3 calculate_grid_size(size_t total_threads, size_t block_size = 256);
}

// GPU性能优化配置
struct GPUOptimizationConfig {
    bool enable_tensor_cores = true;
    bool enable_mixed_precision = true;
    bool enable_memory_pool = true;
    size_t memory_pool_size_mb = 2048;
    size_t max_batch_size = 32;
    bool enable_concurrent_kernels = true;
    bool enable_zero_copy = false;
    int preferred_device_id = -1; // -1表示自动选择
};

} // namespace ai_assistant