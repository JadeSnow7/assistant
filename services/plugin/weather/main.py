"""
天气查询插件
"""
import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from interfaces.sdk.plugin_base import PluginBase


class WeatherPlugin(PluginBase):
    """天气查询插件实现"""
    
    def __init__(self):
        super().__init__()
        self.api_key: Optional[str] = None
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.units = "metric"
        self.cache_duration = 300  # 5分钟缓存
        self._cache: Dict[str, Any] = {}
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            self.api_key = config.get("api_key")
            if not self.api_key:
                self.logger.error("缺少API密钥")
                return False
            
            self.units = config.get("default_units", "metric")
            self.cache_duration = config.get("cache_duration", 300)
            
            # 测试API连接
            test_result = await self._test_api_connection()
            if not test_result:
                self.logger.error("API连接测试失败")
                return False
            
            self.logger.info("天气插件初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"插件初始化失败: {e}")
            return False
    
    async def execute(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行插件命令"""
        try:
            if command == "get_weather":
                return await self._get_current_weather(params)
            elif command == "get_forecast":
                return await self._get_weather_forecast(params)
            elif command == "search_city":
                return await self._search_city(params)
            else:
                return {
                    "success": False,
                    "error": f"未知命令: {command}",
                    "available_commands": [
                        "get_weather", "get_forecast", "search_city"
                    ]
                }
                
        except Exception as e:
            self.logger.error(f"执行命令失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_current_weather(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取当前天气"""
        city = params.get("city", "").strip()
        if not city:
            return {
                "success": False,
                "error": "请提供城市名称"
            }
        
        # 检查缓存
        cache_key = f"weather:{city}:{self.units}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return {
                "success": True,
                "data": cached_data,
                "from_cache": True
            }
        
        # 调用API
        url = f"{self.base_url}/weather"
        params_dict = {
            "q": city,
            "appid": self.api_key,
            "units": self.units,
            "lang": "zh_cn"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params_dict) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 格式化结果
                    result = self._format_weather_data(data)
                    
                    # 缓存结果
                    self._save_to_cache(cache_key, result)
                    
                    return {
                        "success": True,
                        "data": result,
                        "from_cache": False
                    }
                elif response.status == 404:
                    return {
                        "success": False,
                        "error": f"未找到城市: {city}"
                    }
                else:
                    error_data = await response.json()
                    return {
                        "success": False,
                        "error": f"API错误: {error_data.get('message', '未知错误')}"
                    }
    
    async def _get_weather_forecast(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取天气预报"""
        city = params.get("city", "").strip()
        days = min(params.get("days", 5), 5)  # 最多5天
        
        if not city:
            return {
                "success": False,
                "error": "请提供城市名称"
            }
        
        # 检查缓存
        cache_key = f"forecast:{city}:{days}:{self.units}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return {
                "success": True,
                "data": cached_data,
                "from_cache": True
            }
        
        # 调用API
        url = f"{self.base_url}/forecast"
        params_dict = {
            "q": city,
            "appid": self.api_key,
            "units": self.units,
            "lang": "zh_cn"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params_dict) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 格式化预报数据
                    result = self._format_forecast_data(data, days)
                    
                    # 缓存结果
                    self._save_to_cache(cache_key, result)
                    
                    return {
                        "success": True,
                        "data": result,
                        "from_cache": False
                    }
                else:
                    error_data = await response.json()
                    return {
                        "success": False,
                        "error": f"API错误: {error_data.get('message', '未知错误')}"
                    }
    
    async def _search_city(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜索城市"""
        query = params.get("query", "").strip()
        limit = min(params.get("limit", 5), 10)
        
        if not query:
            return {
                "success": False,
                "error": "请提供搜索关键词"
            }
        
        # 使用地理编码API搜索城市
        url = "http://api.openweathermap.org/geo/1.0/direct"
        params_dict = {
            "q": query,
            "limit": limit,
            "appid": self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params_dict) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    cities = []
                    for item in data:
                        cities.append({
                            "name": item.get("name"),
                            "country": item.get("country"),
                            "state": item.get("state"),
                            "lat": item.get("lat"),
                            "lon": item.get("lon"),
                            "full_name": f"{item.get('name')}, {item.get('state', '')}, {item.get('country')}"
                        })
                    
                    return {
                        "success": True,
                        "data": {
                            "query": query,
                            "cities": cities,
                            "total": len(cities)
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "搜索失败"
                    }
    
    def _format_weather_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化天气数据"""
        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        wind = data.get("wind", {})
        
        temp_unit = "°C" if self.units == "metric" else "°F"
        speed_unit = "m/s" if self.units == "metric" else "mph"
        
        return {
            "city": data.get("name"),
            "country": data.get("sys", {}).get("country"),
            "temperature": {
                "current": main.get("temp"),
                "feels_like": main.get("feels_like"),
                "min": main.get("temp_min"),
                "max": main.get("temp_max"),
                "unit": temp_unit
            },
            "humidity": main.get("humidity"),
            "pressure": main.get("pressure"),
            "weather": {
                "main": weather.get("main"),
                "description": weather.get("description"),
                "icon": weather.get("icon")
            },
            "wind": {
                "speed": wind.get("speed"),
                "direction": wind.get("deg"),
                "unit": speed_unit
            },
            "visibility": data.get("visibility"),
            "timestamp": datetime.now().isoformat()
        }
    
    def _format_forecast_data(self, data: Dict[str, Any], days: int) -> Dict[str, Any]:
        """格式化预报数据"""
        forecast_list = data.get("list", [])
        city_info = data.get("city", {})
        
        # 按天分组
        daily_forecasts = []
        current_date = None
        daily_data = []
        
        for item in forecast_list[:days * 8]:  # 每天8个时间点(3小时间隔)
            dt = datetime.fromtimestamp(item.get("dt", 0))
            date = dt.date()
            
            if current_date != date:
                if daily_data:
                    daily_forecasts.append(self._process_daily_data(current_date, daily_data))
                current_date = date
                daily_data = [item]
            else:
                daily_data.append(item)
        
        # 处理最后一天
        if daily_data:
            daily_forecasts.append(self._process_daily_data(current_date, daily_data))
        
        return {
            "city": city_info.get("name"),
            "country": city_info.get("country"),
            "forecasts": daily_forecasts[:days],
            "total_days": len(daily_forecasts[:days])
        }
    
    def _process_daily_data(self, date, hourly_data):
        """处理每日数据"""
        temps = [item["main"]["temp"] for item in hourly_data]
        humidity_values = [item["main"]["humidity"] for item in hourly_data]
        
        # 获取主要天气状况(出现最多的)
        weather_counts = {}
        for item in hourly_data:
            weather_main = item["weather"][0]["main"]
            weather_counts[weather_main] = weather_counts.get(weather_main, 0) + 1
        
        main_weather = max(weather_counts, key=weather_counts.get)
        
        temp_unit = "°C" if self.units == "metric" else "°F"
        
        return {
            "date": date.isoformat(),
            "temperature": {
                "min": min(temps),
                "max": max(temps),
                "avg": sum(temps) / len(temps),
                "unit": temp_unit
            },
            "humidity": {
                "avg": sum(humidity_values) / len(humidity_values)
            },
            "weather": {
                "main": main_weather,
                "description": hourly_data[0]["weather"][0]["description"]
            },
            "hourly_count": len(hourly_data)
        }
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取数据"""
        if key in self._cache:
            cached_item = self._cache[key]
            if datetime.now() - cached_item["timestamp"] < timedelta(seconds=self.cache_duration):
                return cached_item["data"]
            else:
                del self._cache[key]
        return None
    
    def _save_to_cache(self, key: str, data: Dict[str, Any]):
        """保存到缓存"""
        self._cache[key] = {
            "data": data,
            "timestamp": datetime.now()
        }
    
    async def _test_api_connection(self) -> bool:
        """测试API连接"""
        try:
            url = f"{self.base_url}/weather"
            params = {
                "q": "London",
                "appid": self.api_key,
                "units": self.units
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url, params=params) as response:
                    return response.status == 200
        except:
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        return {
            "name": "weather_plugin",
            "version": "1.0.0",
            "description": "天气查询插件，支持查询全球城市天气信息",
            "author": "AI Assistant Team",
            "capabilities": [
                "weather_query",
                "weather_forecast", 
                "weather_alerts"
            ],
            "commands": {
                "get_weather": {
                    "description": "获取当前天气",
                    "parameters": {
                        "city": {"type": "string", "required": True, "description": "城市名称"}
                    }
                },
                "get_forecast": {
                    "description": "获取天气预报",
                    "parameters": {
                        "city": {"type": "string", "required": True, "description": "城市名称"},
                        "days": {"type": "integer", "required": False, "description": "预报天数(1-5)", "default": 5}
                    }
                },
                "search_city": {
                    "description": "搜索城市",
                    "parameters": {
                        "query": {"type": "string", "required": True, "description": "搜索关键词"},
                        "limit": {"type": "integer", "required": False, "description": "结果数量限制", "default": 5}
                    }
                }
            }
        }
    
    async def cleanup(self):
        """清理资源"""
        self._cache.clear()
        self.logger.info("天气插件清理完成")
    
    def is_healthy(self) -> bool:
        """健康检查"""
        return self.api_key is not None


# 插件实例
plugin_instance = WeatherPlugin()