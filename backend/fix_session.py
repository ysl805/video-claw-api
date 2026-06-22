import json

path = r"C:\ProgramData\WorkBuddy\users\5c9ee87b\WorkBuddy\Claw\VideoClaw\video-claw\video-claw\backend\code\data\sessions\1781928003456.json"
with open(path, 'r', encoding='utf-8') as f:
    d = json.load(f)

d['status']['reference_generation'] = 'pending'
d['status']['video_generation'] = 'pending'
d['stage'] = None

with open(path, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print('session 状态已修复')
print('status:', d['status'])
