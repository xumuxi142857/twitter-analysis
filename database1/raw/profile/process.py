import os
import json
import re

# ================= 配置区域 =================
# 你可以在这里指定新条目的属性
NEW_REGION = "US"
NEW_CATEGORY = "media"
# ===========================================

def process_files():
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    targets_path = os.path.join(current_dir, "targets.json")

    # 1. 读取原始 targets.json
    if os.path.exists(targets_path):
        with open(targets_path, 'r', encoding='utf-8') as f:
            try:
                targets = json.load(f)
            except json.JSONDecodeError:
                targets = []
    else:
        targets = []

    # 记录已有的文件名，防止重复添加
    existing_filenames = {item['filename'] for item in targets}
    
    # 2. 扫描当前目录下的所有文件
    # 匹配模式：search_ (文件名部分) _ (8位日期) _ (6位时间).json
    pattern = re.compile(r"search_(.+?)_\d{8}_\d{6}\.json")

    changed_count = 0

    for filename in os.listdir(current_dir):
        match = pattern.match(filename)
        if match:
            # 提取出的中间名称部分 (如 Yomiuri_Online)
            raw_name = match.group(1)
            new_filename = f"profile_{raw_name}.json"
            
            old_file_path = os.path.join(current_dir, filename)
            new_file_path = os.path.join(current_dir, new_filename)

            # A. 执行重命名
            try:
                if not os.path.exists(new_file_path):
                    os.rename(old_file_path, new_file_path)
                    print(f"✅ 重命名: {filename} -> {new_filename}")
                else:
                    print(f"⚠️ 跳过: {new_filename} 已存在，仅尝试更新列表")
            except Exception as e:
                print(f"❌ 重命名失败 {filename}: {e}")
                continue

            # B. 更新 targets 列表
            if new_filename not in existing_filenames:
                new_entry = {
                    "filename": new_filename,
                    "name": raw_name,
                    "region": NEW_REGION,
                    "category": NEW_CATEGORY
                }
                targets.append(new_entry)
                existing_filenames.add(new_filename)
                changed_count += 1
                print(f"➕ 已加入列表: {raw_name}")

    # 3. 保存更新后的 targets.json
    if changed_count > 0:
        with open(targets_path, 'w', encoding='utf-8') as f:
            json.dump(targets, f, indent=2, ensure_ascii=False)
        print(f"\n✨ 处理完成！共新增 {changed_count} 个条目到 targets.json")
    else:
        print("\n保持不变：没有发现新文件需要添加。")

if __name__ == "__main__":
    process_files()