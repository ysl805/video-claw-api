"""
触发 reference_generation 并持续监控 SSE 进度
"""
import sys
import time
import requests
import json

SESSION_ID = "1781928003456"
API_BASE = "http://localhost:8002"

def main():
    url = f"{API_BASE}/api/project/{SESSION_ID}/execute/reference_generation"
    print(f"[启动] 触发参考图生成: {url}")
    
    try:
        with requests.post(url, json={}, stream=True, timeout=(10, 600)) as r:
            print(f"[响应] status={r.status_code}")
            if r.status_code != 200:
                print(f"[错误] {r.text}")
                return
            
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                # SSE 格式: "data: {...}"
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    try:
                        data = json.loads(data_str)
                        msg_type = data.get("type", "")
                        msg = data.get("message", "")
                        percent = data.get("percent", "")
                        stage = data.get("stage", "")
                        
                        ts = time.strftime("%H:%M:%S")
                        print(f"[{ts}] {msg_type} | {msg} | {percent}% | stage={stage}")
                        
                        if msg_type == "complete":
                            print(f"[完成] 参考图生成完成!")
                            break
                        if msg_type == "error":
                            print(f"[错误] {data.get('detail', data)}")
                            break
                    except json.JSONDecodeError:
                        print(f"[原始] {line}")
                else:
                    print(f"[原始] {line}")
    
    except requests.exceptions.Timeout:
        print("[超时] 请求超时")
    except Exception as e:
        print(f"[异常] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
