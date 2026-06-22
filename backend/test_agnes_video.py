"""
直接测试 AgnesVideoClient，看确切报错
"""
import sys
import os
import logging

# 添加 backend 到 path
sys.path.insert(0, os.getcwd())

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from config import Config
Config.OPENAI_API_KEY = Config.OPENAI_API_KEY or os.environ.get('OPENAI_API_KEY', '')
Config.OPENAI_BASE_URL = Config.OPENAI_BASE_URL or 'https://apihub.agnes-ai.com/v1'

from models.video_agnes import AgnesVideoClient

client = AgnesVideoClient(
    api_key=Config.OPENAI_API_KEY,
    base_url=Config.OPENAI_BASE_URL,
)

print(f"[测试] base_url: {client.base_url}")
print(f"[测试] 开始生成测试视频...")

try:
    result = client.generate_video(
        prompt='A cat walking on the beach, cinematic, high quality',
        image_path=None,
        save_path='/tmp/test_agnes_video.mp4',
        model='agnes-video-v2.0',
        duration=5,
    )
    print(f"[成功] 视频已生成: {result}")
except Exception as e:
    print(f"[失败] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
