"""
GPU加速配置管理
"""
import asyncio
import subprocess
import logging
import platform
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class GPUType(str, Enum):
    """GPU类型"""
    NVIDIA = "nvidia"
    AMD = "amd" 
    INTEL = "intel"
    APPLE = "apple"
    UNKNOWN = "unknown"


@dataclass
class GPUInfo:
    """GPU信息"""
    id: int
    name: str
    gpu_type: GPUType
    memory_total: int  # MB
    memory_free: int   # MB
    memory_used: int   # MB
    utilization: float  # 百分比
    temperature: Optional[int] = None  # 摄氏度
    power_usage: Optional[int] = None  # 瓦特
    driver_version: Optional[str] = None
    compute_capability: Optional[str] = None


@dataclass
class GPUConfig:
    """GPU配置"""
    enabled: bool = True
    gpu_ids: List[int] = None  # 使用的GPU ID列表
    gpu_layers: int = 35  # 卸载到GPU的层数
    main_gpu: int = 0  # 主GPU ID
    tensor_split: List[float] = None  # 多GPU张量分割比例
    memory_limit: Optional[int] = None  # 内存限制(MB)
    low_vram: bool = False  # 低显存模式
    batch_size: int = 512  # 批处理大小
    
    def __post_init__(self):
        if self.gpu_ids is None:
            self.gpu_ids = [0]
        if self.tensor_split is None:
            self.tensor_split = []


class GPUManager:
    """GPU管理器"""
    
    def __init__(self):
        self.gpus: List[GPUInfo] = []
        self.gpu_type = GPUType.UNKNOWN
        self.initialized = False
        self.config = GPUConfig()
    
    async def initialize(self) -> bool:
        """初始化GPU管理器"""
        try:
            logger.info("初始化GPU管理器...")
            
            # 检测GPU类型和信息
            await self._detect_gpus()
            
            # 自动配置GPU参数
            await self._auto_configure()
            
            self.initialized = True
            logger.info(f"GPU管理器初始化完成，检测到 {len(self.gpus)} 个GPU")
            return True
            
        except Exception as e:
            logger.error(f"GPU管理器初始化失败: {e}")
            self.initialized = True  # 即使检测失败也继续，使用CPU
            return False
    
    async def _detect_gpus(self):
        """检测GPU设备"""
        # 首先尝试检测NVIDIA GPU
        nvidia_gpus = await self._detect_nvidia_gpus()
        if nvidia_gpus:
            self.gpus = nvidia_gpus
            self.gpu_type = GPUType.NVIDIA
            return
        
        # 检测AMD GPU
        amd_gpus = await self._detect_amd_gpus()
        if amd_gpus:
            self.gpus = amd_gpus
            self.gpu_type = GPUType.AMD
            return
        
        # 检测Intel GPU
        intel_gpus = await self._detect_intel_gpus()
        if intel_gpus:
            self.gpus = intel_gpus
            self.gpu_type = GPUType.INTEL
            return
        
        # 检测Apple GPU (M1/M2)
        if platform.system() == "Darwin":
            apple_gpus = await self._detect_apple_gpus()
            if apple_gpus:
                self.gpus = apple_gpus
                self.gpu_type = GPUType.APPLE
                return
        
        logger.warning("未检测到支持的GPU设备，将使用CPU模式")
    
    async def _detect_nvidia_gpus(self) -> List[GPUInfo]:
        """检测NVIDIA GPU"""
        gpus = []
        
        try:
            # 使用nvidia-smi获取GPU信息
            cmd = [
                "nvidia-smi", 
                "--query-gpu=index,name,memory.total,memory.free,memory.used,utilization.gpu,temperature.gpu,power.draw,driver_version",
                "--format=csv,noheader,nounits"
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                lines = stdout.decode().strip().split('\n')
                
                for line in lines:
                    if not line.strip():
                        continue
                    
                    parts = [part.strip() for part in line.split(',')]
                    if len(parts) >= 9:
                        gpu_info = GPUInfo(
                            id=int(parts[0]),
                            name=parts[1],
                            gpu_type=GPUType.NVIDIA,
                            memory_total=int(parts[2]),
                            memory_free=int(parts[3]),
                            memory_used=int(parts[4]),
                            utilization=float(parts[5]),
                            temperature=int(parts[6]) if parts[6] != '[N/A]' else None,
                            power_usage=float(parts[7]) if parts[7] != '[N/A]' else None,
                            driver_version=parts[8]
                        )
                        gpus.append(gpu_info)
            
            # 获取计算能力
            for gpu in gpus:
                try:
                    cmd = ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader,nounits", f"--id={gpu.id}"]
                    result = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await result.communicate()
                    
                    if result.returncode == 0:
                        gpu.compute_capability = stdout.decode().strip()
                except:
                    pass
        
        except FileNotFoundError:
            logger.debug("nvidia-smi 未找到，跳过NVIDIA GPU检测")
        except Exception as e:
            logger.debug(f"NVIDIA GPU检测失败: {e}")
        
        return gpus
    
    async def _detect_amd_gpus(self) -> List[GPUInfo]:
        """检测AMD GPU"""
        gpus = []
        
        try:
            # 使用rocm-smi获取GPU信息
            cmd = ["rocm-smi", "--showallinfo"]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                # 解析rocm-smi输出
                output = stdout.decode()
                # 简化的解析逻辑，实际需要更复杂的解析
                if "GPU" in output:
                    gpu_info = GPUInfo(
                        id=0,
                        name="AMD GPU",
                        gpu_type=GPUType.AMD,
                        memory_total=0,
                        memory_free=0,
                        memory_used=0,
                        utilization=0.0
                    )
                    gpus.append(gpu_info)
        
        except FileNotFoundError:
            logger.debug("rocm-smi 未找到，跳过AMD GPU检测")
        except Exception as e:
            logger.debug(f"AMD GPU检测失败: {e}")
        
        return gpus
    
    async def _detect_intel_gpus(self) -> List[GPUInfo]:
        """检测Intel GPU"""
        gpus = []
        
        try:
            # 检查Intel GPU工具
            cmd = ["intel_gpu_top", "-l"]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                # 简化的Intel GPU检测
                gpu_info = GPUInfo(
                    id=0,
                    name="Intel GPU",
                    gpu_type=GPUType.INTEL,
                    memory_total=0,
                    memory_free=0,
                    memory_used=0,
                    utilization=0.0
                )
                gpus.append(gpu_info)
        
        except FileNotFoundError:
            logger.debug("intel_gpu_top 未找到，跳过Intel GPU检测")
        except Exception as e:
            logger.debug(f"Intel GPU检测失败: {e}")
        
        return gpus
    
    async def _detect_apple_gpus(self) -> List[GPUInfo]:
        """检测Apple GPU (M1/M2)"""
        gpus = []
        
        try:
            # 检查是否是Apple Silicon
            cmd = ["sysctl", "-n", "machdep.cpu.brand_string"]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                cpu_info = stdout.decode().strip()
                if "Apple" in cpu_info:
                    # 检测Apple GPU
                    cmd = ["system_profiler", "SPDisplaysDataType"]
                    
                    result = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await result.communicate()
                    
                    if result.returncode == 0:
                        output = stdout.decode()
                        if "Apple" in output and ("M1" in output or "M2" in output or "M3" in output):
                            gpu_info = GPUInfo(
                                id=0,
                                name="Apple GPU",
                                gpu_type=GPUType.APPLE,
                                memory_total=0,  # Apple使用统一内存
                                memory_free=0,
                                memory_used=0,
                                utilization=0.0
                            )
                            gpus.append(gpu_info)
        
        except Exception as e:
            logger.debug(f"Apple GPU检测失败: {e}")
        
        return gpus
    
    async def _auto_configure(self):
        """自动配置GPU参数"""
        if not self.gpus:
            # 没有GPU，使用CPU配置
            self.config.enabled = False
            self.config.gpu_layers = 0
            logger.info("未检测到GPU，禁用GPU加速")
            return
        
        # 启用GPU加速
        self.config.enabled = True
        self.config.gpu_ids = [gpu.id for gpu in self.gpus]
        self.config.main_gpu = 0
        
        # 根据GPU类型和内存自动配置
        if self.gpu_type == GPUType.NVIDIA:
            await self._configure_nvidia()
        elif self.gpu_type == GPUType.AMD:
            await self._configure_amd()
        elif self.gpu_type == GPUType.INTEL:
            await self._configure_intel()
        elif self.gpu_type == GPUType.APPLE:
            await self._configure_apple()
        
        logger.info(f"GPU配置完成: {len(self.gpus)} 个 {self.gpu_type.value} GPU, {self.config.gpu_layers} 层")
    
    async def _configure_nvidia(self):
        """配置NVIDIA GPU"""
        main_gpu = self.gpus[0]
        
        # 根据显存大小配置层数
        memory_gb = main_gpu.memory_total / 1024
        
        if memory_gb >= 24:  # 24GB+ 显存
            self.config.gpu_layers = -1  # 全部层
            self.config.batch_size = 1024
        elif memory_gb >= 12:  # 12GB+ 显存
            self.config.gpu_layers = 35
            self.config.batch_size = 768
        elif memory_gb >= 8:  # 8GB+ 显存
            self.config.gpu_layers = 28
            self.config.batch_size = 512
        elif memory_gb >= 6:  # 6GB+ 显存
            self.config.gpu_layers = 20
            self.config.batch_size = 256
            self.config.low_vram = True
        elif memory_gb >= 4:  # 4GB+ 显存
            self.config.gpu_layers = 15
            self.config.batch_size = 128
            self.config.low_vram = True
        else:  # 小于4GB显存
            self.config.gpu_layers = 10
            self.config.batch_size = 64
            self.config.low_vram = True
        
        # 多GPU配置
        if len(self.gpus) > 1:
            total_memory = sum(gpu.memory_total for gpu in self.gpus)
            self.config.tensor_split = [gpu.memory_total / total_memory for gpu in self.gpus]
    
    async def _configure_amd(self):
        """配置AMD GPU"""
        # AMD GPU配置（ROCm）
        self.config.gpu_layers = 25
        self.config.batch_size = 512
    
    async def _configure_intel(self):
        """配置Intel GPU"""
        # Intel GPU配置
        self.config.gpu_layers = 20
        self.config.batch_size = 256
    
    async def _configure_apple(self):
        """配置Apple GPU"""
        # Apple GPU配置（Metal）
        self.config.gpu_layers = 35
        self.config.batch_size = 512
    
    async def get_gpu_info(self) -> List[GPUInfo]:
        """获取GPU信息"""
        if not self.initialized:
            await self.initialize()
        
        # 更新实时信息
        if self.gpu_type == GPUType.NVIDIA:
            await self._update_nvidia_info()
        
        return self.gpus.copy()
    
    async def _update_nvidia_info(self):
        """更新NVIDIA GPU实时信息"""
        try:
            cmd = [
                "nvidia-smi", 
                "--query-gpu=index,memory.free,memory.used,utilization.gpu,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits"
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                lines = stdout.decode().strip().split('\n')
                
                for i, line in enumerate(lines):
                    if i < len(self.gpus):
                        parts = [part.strip() for part in line.split(',')]
                        if len(parts) >= 6:
                            self.gpus[i].memory_free = int(parts[1])
                            self.gpus[i].memory_used = int(parts[2])
                            self.gpus[i].utilization = float(parts[3])
                            self.gpus[i].temperature = int(parts[4]) if parts[4] != '[N/A]' else None
                            self.gpus[i].power_usage = float(parts[5]) if parts[5] != '[N/A]' else None
        
        except Exception as e:
            logger.debug(f"更新NVIDIA GPU信息失败: {e}")
    
    def get_gpu_config(self) -> GPUConfig:
        """获取GPU配置"""
        return self.config
    
    def update_gpu_config(self, **kwargs) -> bool:
        """更新GPU配置"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            logger.info(f"GPU配置已更新: {kwargs}")
            return True
            
        except Exception as e:
            logger.error(f"更新GPU配置失败: {e}")
            return False
    
    def get_recommended_config(self, model_size: str = "7b") -> Dict[str, Any]:
        """获取推荐配置"""
        if not self.gpus:
            return {
                "gpu_layers": 0,
                "batch_size": 64,
                "threads": 8,
                "use_gpu": False
            }
        
        main_gpu = self.gpus[0]
        memory_gb = main_gpu.memory_total / 1024
        
        # 根据模型大小调整配置
        size_multiplier = {
            "4b": 0.7,
            "7b": 1.0,
            "13b": 1.5,
            "30b": 3.0,
            "70b": 8.0
        }.get(model_size, 1.0)
        
        base_layers = self.config.gpu_layers
        adjusted_layers = max(0, int(base_layers / size_multiplier))
        
        return {
            "gpu_layers": adjusted_layers,
            "main_gpu": self.config.main_gpu,
            "gpu_ids": self.config.gpu_ids,
            "tensor_split": self.config.tensor_split,
            "batch_size": self.config.batch_size,
            "low_vram": self.config.low_vram or memory_gb < 8,
            "use_gpu": self.config.enabled,
            "gpu_type": self.gpu_type.value,
            "memory_limit": self.config.memory_limit
        }
    
    def is_gpu_available(self) -> bool:
        """检查GPU是否可用"""
        return self.initialized and len(self.gpus) > 0 and self.config.enabled