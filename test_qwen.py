import requests, os

headers = {'Authorization': f'Bearer {os.environ.get("QWENCLOUD_API_KEY")}'}
url = f'{os.environ.get("QWEN_BASE_URL")}/models'
print('URL:', url)
try:
    r = requests.get(url, headers=headers, timeout=30)
    print('Status:', r.status_code)
    print('Response:', r.text[:500])
except Exception as e:
    print('Error:', e)