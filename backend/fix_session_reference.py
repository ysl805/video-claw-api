"""
根据磁盘现有参考图修复 session 文件
"""
import json
import os
import glob

sid = "1781928003456"
base_dir = os.getcwd()
scenes_dir = os.path.join(base_dir, "code", "result", "image", sid, "Scenes")
session_path = os.path.join(base_dir, "code", "data", "sessions", f"{sid}.json")

# 扫描现有参考图
reference_clips = []
seen_ids = set()

for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
    for fp in glob.glob(os.path.join(scenes_dir, ext)):
        basename = os.path.splitext(os.path.basename(fp))[0]
        # 去掉 _v2, _v3 等版本后缀
        shot_id = basename.split("_v")[0]
        if shot_id in seen_ids:
            continue
        seen_ids.add(shot_id)
        
        # 找该 shot 的所有版本
        versions = []
        for vext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            for vfp in glob.glob(os.path.join(scenes_dir, f"{shot_id}*{vext}")):
                versions.append(vfp.replace("/", "\\"))
        versions = sorted(set(versions))
        
        reference_clips.append({
            "id": shot_id,
            "path": fp.replace("/", "\\"),
            "status": "done",
            "versions": versions
        })

print(f"扫描到 {len(reference_clips)} 个参考图")

# 更新 session 文件
with open(session_path, "r", encoding="utf-8") as f:
    d = json.load(f)

d["reference_clips"] = reference_clips
d["status"]["reference_generation"] = "completed"
d["stage"] = None

with open(session_path, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print(f"session 已修复: reference_clips={len(reference_clips)}, status.reference_generation=completed")
