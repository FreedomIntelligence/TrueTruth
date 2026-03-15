import requests

# 配置
api_key = "sk-"
base_url = "https://api.huatuogpt.cn" # 你的 API 域名

# 拼接端点
url = f"{base_url}/v1/models"
# 如果你的 base_url 结尾已经有了 /v1，请去掉上面的 /v1

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("可用模型列表：")
        # 大多数兼容接口返回的数据在 'data' 字段中
        if 'data' in data:
            for item in data['data']:
                print(f"- {item['id']}")
        else:
            print(data) # 打印原始数据以防结构不同
    else:
        print(f"请求失败，状态码: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"发生错误: {e}")