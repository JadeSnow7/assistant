#include "../include/gpu_engine.hpp"
#include <cuda_runtime.h>
#include <cublas_v2.h>
#include <thread>
#include <queue>
#include <condition_variable>

namespace ai_assistant {

// CUDAMemoryPool实现
class CUDAMemoryPool::Impl {
public:
    struct MemoryBlock {
        void* ptr;
        size_t size;
        bool in_use;
        std::chrono::steady_clock::time_point last_used;
    };
    
    Impl(size_t pool_size_mb) : pool_size_bytes_(pool_size_mb * 1024 * 1024) {
        // 分配大块GPU内存
        cudaError_t error = cudaMalloc(&pool_base_, pool_size_bytes_);
        if (error != cudaSuccess) {
            Logger::error("Failed to allocate GPU memory pool: " + std::string(cudaGetErrorString(error)));
            pool_base_ = nullptr;
            return;
        }
        
        // 初始化为一个大的空闲块
        MemoryBlock initial_block;
        initial_block.ptr = pool_base_;
        initial_block.size = pool_size_bytes_;
        initial_block.in_use = false;
        initial_block.last_used = std::chrono::steady_clock::now();
        
        blocks_.push_back(initial_block);
        Logger::info("GPU memory pool initialized: " + std::to_string(pool_size_mb) + "MB");
    }
    
    ~Impl() {
        if (pool_base_) {
            cudaFree(pool_base_);
        }
    }
    
    void* allocate(size_t size_bytes) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        // 对齐到256字节边界
        size_bytes = cuda_utils::align_memory_size(size_bytes);
        
        // 查找合适的空闲块
        for (auto& block : blocks_) {
            if (!block.in_use && block.size >= size_bytes) {
                block.in_use = true;
                block.last_used = std::chrono::steady_clock::now();
                
                // 如果块太大，分割它
                if (block.size > size_bytes + 256) {
                    MemoryBlock new_block;
                    new_block.ptr = static_cast<char*>(block.ptr) + size_bytes;
                    new_block.size = block.size - size_bytes;
                    new_block.in_use = false;
                    new_block.last_used = std::chrono::steady_clock::now();
                    
                    block.size = size_bytes;
                    blocks_.push_back(new_block);
                }
                
                total_allocated_ += size_bytes;
                peak_allocated_ = std::max(peak_allocated_, total_allocated_);
                
                return block.ptr;
            }
        }
        
        Logger::warning("GPU memory pool allocation failed for size: " + std::to_string(size_bytes));
        return nullptr;
    }
    
    void deallocate(void* ptr) {
        if (!ptr) return;
        
        std::lock_guard<std::mutex> lock(mutex_);
        
        for (auto& block : blocks_) {
            if (block.ptr == ptr && block.in_use) {
                block.in_use = false;
                block.last_used = std::chrono::steady_clock::now();
                total_allocated_ -= block.size;
                
                // 尝试合并相邻的空闲块
                merge_free_blocks();
                return;
            }
        }
    }
    
    MemoryStats get_memory_stats() const {
        std::lock_guard<std::mutex> lock(mutex_);
        
        MemoryStats stats;
        stats.total_allocated = total_allocated_;
        stats.peak_allocated = peak_allocated_;
        stats.current_free = pool_size_bytes_ - total_allocated_;
        
        // 计算碎片化率
        size_t free_blocks = 0;
        for (const auto& block : blocks_) {
            if (!block.in_use) {
                free_blocks++;
            }
        }
        stats.fragmentation_ratio = free_blocks > 1 ? (double)(free_blocks - 1) / blocks_.size() : 0.0;
        
        return stats;
    }

private:
    void* pool_base_;
    size_t pool_size_bytes_;
    std::vector<MemoryBlock> blocks_;
    mutable std::mutex mutex_;
    size_t total_allocated_ = 0;
    size_t peak_allocated_ = 0;
    
    void merge_free_blocks() {
        // 按地址排序
        std::sort(blocks_.begin(), blocks_.end(), 
                 [](const MemoryBlock& a, const MemoryBlock& b) { return a.ptr < b.ptr; });
        
        // 合并相邻的空闲块
        for (size_t i = 0; i < blocks_.size() - 1; ++i) {
            if (!blocks_[i].in_use && !blocks_[i + 1].in_use) {
                char* end_of_current = static_cast<char*>(blocks_[i].ptr) + blocks_[i].size;
                if (end_of_current == blocks_[i + 1].ptr) {
                    blocks_[i].size += blocks_[i + 1].size;
                    blocks_.erase(blocks_.begin() + i + 1);
                    --i; // 重新检查当前位置
                }
            }
        }
    }
};

// CUDAInferenceContext实现
class CUDAInferenceContext::Impl {
public:
    Impl(int device_id) : device_id_(device_id), stream_(nullptr), cublas_handle_(nullptr) {}
    
    ~Impl() {
        cleanup();
    }
    
    bool initialize() {
        // 设置CUDA设备
        cudaError_t error = cudaSetDevice(device_id_);
        if (error != cudaSuccess) {
            Logger::error("Failed to set CUDA device: " + std::string(cudaGetErrorString(error)));
            return false;
        }
        
        // 创建CUDA流
        error = cudaStreamCreate(&stream_);
        if (error != cudaSuccess) {
            Logger::error("Failed to create CUDA stream: " + std::string(cudaGetErrorString(error)));
            return false;
        }
        
        // 创建cuBLAS句柄
        cublasStatus_t cublas_status = cublasCreate(&cublas_handle_);
        if (cublas_status != CUBLAS_STATUS_SUCCESS) {
            Logger::error("Failed to create cuBLAS handle");
            return false;
        }
        
        // 设置cuBLAS流
        cublas_status = cublasSetStream(cublas_handle_, stream_);
        if (cublas_status != CUBLAS_STATUS_SUCCESS) {
            Logger::error("Failed to set cuBLAS stream");
            return false;
        }
        
        Logger::info("CUDA inference context initialized on device " + std::to_string(device_id_));
        return true;
    }
    
    void cleanup() {
        if (cublas_handle_) {
            cublasDestroy(cublas_handle_);
            cublas_handle_ = nullptr;
        }
        
        if (stream_) {
            cudaStreamDestroy(stream_);
            stream_ = nullptr;
        }
    }
    
    cudaStream_t get_stream() const { return stream_; }
    cublasHandle_t get_cublas_handle() const { return cublas_handle_; }
    
    void synchronize() {
        cudaStreamSynchronize(stream_);
    }
    
    GPUDeviceInfo get_device_info() const {
        GPUDeviceInfo info;
        info.device_id = device_id_;
        
        cudaDeviceProp prop;
        cudaGetDeviceProperties(&prop, device_id_);
        
        info.name = prop.name;
        info.total_memory_mb = prop.totalGlobalMem / (1024 * 1024);
        info.compute_capability_major = prop.major;
        info.compute_capability_minor = prop.minor;
        info.multiprocessor_count = prop.multiProcessorCount;
        info.supports_tensor_cores = (prop.major >= 7); // Volta及以上架构
        
        // 获取空闲内存
        size_t free_mem, total_mem;
        cudaMemGetInfo(&free_mem, &total_mem);
        info.free_memory_mb = free_mem / (1024 * 1024);
        
        return info;
    }

private:
    int device_id_;
    cudaStream_t stream_;
    cublasHandle_t cublas_handle_;
};

// GPUModelEngine实现
class GPUModelEngine::Impl {
public:
    Impl() : initialized_(false), memory_pool_(nullptr), context_(nullptr) {}
    
    ~Impl() {
        cleanup();
    }
    
    bool initialize(const std::string& model_path, int device_id) {
        if (initialized_) return true;
        
        // 检查CUDA可用性
        if (!cuda_utils::is_cuda_available()) {
            Logger::error("CUDA is not available");
            return false;
        }
        
        // 初始化CUDA上下文
        context_ = std::make_unique<CUDAInferenceContext>(device_id);
        if (!context_->initialize()) {
            Logger::error("Failed to initialize CUDA context");
            return false;
        }
        
        // 初始化内存池
        memory_pool_ = std::make_unique<CUDAMemoryPool>(2048); // 2GB内存池
        
        // 加载模型
        if (!load_model_to_gpu(model_path)) {
            Logger::error("Failed to load model to GPU");
            return false;
        }
        
        initialized_ = true;
        Logger::info("GPU model engine initialized successfully");
        return true;
    }
    
    bool load_model_to_gpu(const std::string& model_path) {
        // TODO: 实现具体的模型加载逻辑
        // 这里需要根据具体的模型格式(如ONNX、TensorRT等)实现
        Logger::info("Loading model to GPU: " + model_path);
        
        // 模拟模型加载
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
        
        current_model_path_ = model_path;
        return true;
    }
    
    std::future<InferenceResponse> inference_async_gpu(const InferenceRequest& request) {
        return std::async(std::launch::async, [this, request]() {
            return inference_gpu_internal(request);
        });
    }
    
    GPUStats get_gpu_stats() const {
        GPUStats stats;
        
        if (context_) {
            auto device_info = context_->get_device_info();
            stats.gpu_memory_total_mb = device_info.total_memory_mb;
            stats.gpu_memory_used_mb = device_info.total_memory_mb - device_info.free_memory_mb;
            stats.gpu_utilization_percent = static_cast<double>(stats.gpu_memory_used_mb) / stats.gpu_memory_total_mb * 100.0;
        }
        
        stats.avg_inference_time = avg_inference_time_;
        stats.completed_inferences = completed_inferences_;
        stats.throughput_inferences_per_sec = calculate_throughput();
        
        return stats;
    }

private:
    bool initialized_;
    std::unique_ptr<CUDAMemoryPool> memory_pool_;
    std::unique_ptr<CUDAInferenceContext> context_;
    std::string current_model_path_;
    
    std::atomic<size_t> completed_inferences_{0};
    std::chrono::milliseconds avg_inference_time_{0};
    std::chrono::steady_clock::time_point last_throughput_calc_;
    size_t last_completed_count_{0};
    
    InferenceResponse inference_gpu_internal(const InferenceRequest& request) {
        auto start_time = std::chrono::high_resolution_clock::now();
        
        InferenceResponse response;
        
        try {
            // TODO: 实现GPU推理逻辑
            // 1. 准备输入数据
            // 2. 执行GPU推理
            // 3. 处理输出结果
            
            // 模拟GPU推理
            std::this_thread::sleep_for(std::chrono::milliseconds(50)); // GPU推理通常更快
            
            response.text = "GPU accelerated response to: " + request.prompt;
            response.finished = true;
            response.confidence = 0.95f;
            response.token_count = 60;
            response.used_model = ModelType::LOCAL_SMALL;
            
            auto end_time = std::chrono::high_resolution_clock::now();
            response.latency_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();
            
            // 更新统计信息
            update_stats(std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time));
            
        } catch (const std::exception& e) {
            response.text = "GPU inference error: " + std::string(e.what());
            Logger::error("GPU inference failed: " + std::string(e.what()));
        }
        
        return response;
    }
    
    void update_stats(std::chrono::milliseconds inference_time) {
        completed_inferences_++;
        
        // 计算移动平均延迟
        if (completed_inferences_ == 1) {
            avg_inference_time_ = inference_time;
        } else {
            auto count = completed_inferences_.load();
            avg_inference_time_ = std::chrono::milliseconds(
                (avg_inference_time_.count() * (count - 1) + inference_time.count()) / count
            );
        }
    }
    
    double calculate_throughput() const {
        auto now = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::seconds>(now - last_throughput_calc_);
        
        if (duration.count() == 0) return 0.0;
        
        auto current_count = completed_inferences_.load();
        return static_cast<double>(current_count - last_completed_count_) / duration.count();
    }
    
    void cleanup() {
        context_.reset();
        memory_pool_.reset();
    }
};

// 公共接口实现
CUDAMemoryPool::CUDAMemoryPool(size_t pool_size_mb) : pimpl_(std::make_unique<Impl>(pool_size_mb)) {}
CUDAMemoryPool::~CUDAMemoryPool() = default;

void* CUDAMemoryPool::allocate(size_t size_bytes) {
    return pimpl_->allocate(size_bytes);
}

void CUDAMemoryPool::deallocate(void* ptr) {
    pimpl_->deallocate(ptr);
}

CUDAMemoryPool::MemoryStats CUDAMemoryPool::get_memory_stats() const {
    return pimpl_->get_memory_stats();
}

CUDAInferenceContext::CUDAInferenceContext(int device_id) : pimpl_(std::make_unique<Impl>(device_id)) {}
CUDAInferenceContext::~CUDAInferenceContext() = default;

bool CUDAInferenceContext::initialize() {
    return pimpl_->initialize();
}

void CUDAInferenceContext::cleanup() {
    pimpl_->cleanup();
}

cudaStream_t CUDAInferenceContext::get_stream() const {
    return pimpl_->get_stream();
}

cublasHandle_t CUDAInferenceContext::get_cublas_handle() const {
    return pimpl_->get_cublas_handle();
}

void CUDAInferenceContext::synchronize() {
    pimpl_->synchronize();
}

GPUDeviceInfo CUDAInferenceContext::get_device_info() const {
    return pimpl_->get_device_info();
}

GPUModelEngine::GPUModelEngine() : pimpl_(std::make_unique<Impl>()) {}
GPUModelEngine::~GPUModelEngine() = default;

bool GPUModelEngine::initialize(const std::string& model_path, int device_id) {
    return pimpl_->initialize(model_path, device_id);
}

std::future<InferenceResponse> GPUModelEngine::inference_async_gpu(const InferenceRequest& request) {
    return pimpl_->inference_async_gpu(request);
}

GPUModelEngine::GPUStats GPUModelEngine::get_gpu_stats() const {
    return pimpl_->get_gpu_stats();
}

// CUDA工具函数实现
namespace cuda_utils {
    bool is_cuda_available() {
        int device_count = 0;
        cudaError_t error = cudaGetDeviceCount(&device_count);
        return (error == cudaSuccess && device_count > 0);
    }
    
    int get_device_count() {
        int count = 0;
        cudaGetDeviceCount(&count);
        return count;
    }
    
    std::vector<GPUDeviceInfo> get_all_gpu_info() {
        std::vector<GPUDeviceInfo> devices;
        int device_count = get_device_count();
        
        for (int i = 0; i < device_count; ++i) {
            CUDAInferenceContext context(i);
            if (context.initialize()) {
                devices.push_back(context.get_device_info());
                context.cleanup();
            }
        }
        
        return devices;
    }
    
    int select_best_device() {
        auto devices = get_all_gpu_info();
        if (devices.empty()) return -1;
        
        // 选择显存最大的设备
        int best_device = 0;
        size_t max_memory = 0;
        
        for (size_t i = 0; i < devices.size(); ++i) {
            if (devices[i].free_memory_mb > max_memory) {
                max_memory = devices[i].free_memory_mb;
                best_device = static_cast<int>(i);
            }
        }
        
        return best_device;
    }
    
    size_t align_memory_size(size_t size, size_t alignment) {
        return ((size + alignment - 1) / alignment) * alignment;
    }
}

} // namespace ai_assistant