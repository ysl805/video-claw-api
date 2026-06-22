"""
修复 session 1781928003456 的视频生成配置
"""
import json
import os

session_path = r"C:\ProgramData\WorkBuddy\users\5c9ee87b\WorkBuddy\Claw\VideoClaw\video-claw\video-claw\backend\code\data\sessions\1781928003456.json"

with open(session_path, 'r', encoding='utf-8') as f:
    session = json.load(f)

# 1. 设置视频模型
session['video_model'] = 'agnes-video-v2.0'
session['video_reference_model'] = 'agnes-video-v2.0'

# 2. 更新 reference_clips（从磁盘扫描）
ref_dir = r"C:\ProgramData\WorkBuddy\users\5c9ee87b\WorkBuddy\Claw\VideoClaw\video-claw\video-claw\backend\code\result\image\1781928003456\Scenes"
ref_clips = []

if os.path.exists(ref_dir):
    for fname in sorted(os.listdir(ref_dir)):
        if fname.endswith(('.png', '.jpg', '.jpeg')):
            fpath = os.path.join(ref_dir, fname)
            clip_id = fname.rsplit('.', 1)[0]
            ref_clips.append({
                'id': clip_id,
                'path': fpath,
                'url': '',
                'status': 'completed'
            })
    
    print(f'找到 {len(ref_clips)} 个参考图')

# 3. 更新 artifacts
if 'reference_generation' not in session['artifacts']:
    session['artifacts']['reference_generation'] = {}
session['artifacts']['reference_generation']['reference_clips'] = ref_clips
session['artifacts']['reference_generation']['status'] = 'completed'

# 4. 重置 video_generation 状态
session['status']['reference_generation'] = 'completed'
session['status']['video_generation'] = 'pending'

for clip in session['artifacts'].get('video_generation', {}).get('clips', []):
    clip['status'] = 'pending'
    clip['versions'] = []

# 5. 保存
with open(session_path, 'w', encoding='utf-8') as f:
    json.dump(session, f, indent=2, ensure_ascii=False)

print('Session 修复完成')
print(f'video_model: {session["video_model"]}')
print(f'reference_clips: {len(ref_clips)}')
print(f'status.video_generation: {session["status"]["video_generation"]}')
