#!/usr/bin/env python3
"""
Gemini API 安全测试脚本
"""
import google.generativeai as genai
import os
from dotenv import load_dotenv

def test_gemini_api():
    """安全测试Gemini API"""
    # 加载环境变量
    load_dotenv()
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ 错误: 请在.env文件中设置GEMINI_API_KEY")
        print("💡 提示: 复制.env.example为.env并填入真实API Key")
        return
    
    if api_key == "your_gemini_api_key_here":
        print("❌ 错误: 请使用真实的API Key替换模板值")
        return
        
    print("🔧 配置Gemini API...")
    genai.configure(api_key=api_key)
    
    # 测试不同的模型名称
    model_names = [
        "gemini-pro",
        "gemini-1.5-pro", 
        "gemini-1.5-flash",
        "models/gemini-pro",
        "models/gemini-1.5-pro"
    ]
    
    for model_name in model_names:
        print(f"\n🧪 测试模型: {model_name}")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Hello, world!")
            
            if response.parts:
                print(f"✅ 成功! 响应: {response.text[:100]}...")
                print(f"🎯 正确的模型名称: {model_name}")
                break
            else:
                print(f"❌ 失败: 无响应内容")
                
        except Exception as e:
            print(f"❌ 失败: {e}")
    
    # 列出可用模型
    print(f"\n📋 列出可用模型:")
    try:
        models = genai.list_models()
        for model in models:
            print(f"  - {model.name}")
            if hasattr(model, 'supported_generation_methods'):
                print(f"    支持方法: {model.supported_generation_methods}")
    except Exception as e:
        print(f"❌ 获取模型列表失败: {e}")

if __name__ == "__main__":
    test_gemini_api()