import requests
import json

def test_openrouter_api():
    """测试OpenRouter API调用"""
    api_key = "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"
    api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    # 尝试不同的模型
    models_to_test = [
        "meta-llama/llama-3.1-8b-instruct:free",
        "google/gemma-2-9b-it:free", 
        "mistralai/mistral-7b-instruct:free",
        "deepseek/deepseek-chat"
    ]
    
    for model in models_to_test:
        print(f"\n🔄 测试模型: {model}")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://feishu-analyzer.com",
            "X-Title": "Feishu Daily ToDoList Generator"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello"
                }
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                print(f"✅ AI响应: {ai_response}")
                return True  # 找到可用的模型就停止
            else:
                print(f"❌ API调用失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")
    
    return False

def test_api_key_info():
    """检查API密钥信息"""
    api_key = "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"
    credits_url = "https://openrouter.ai/api/v1/auth/credits"
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        print("\n🔍 检查API密钥状态...")
        response = requests.get(credits_url, headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 账户余额: ${data.get('credits', 'N/A')}")
        else:
            print(f"❌ 无法获取账户信息")
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")

if __name__ == "__main__":
    test_api_key_info()
    test_openrouter_api() 