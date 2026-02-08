# ... 之前的 import 保持不变
from werkzeug.utils import secure_filename # <--- 新增引入这个
import shutil

# ... (配置区域保持不变) ...

# ================= 功能 C: 原始文件上传与分拣 =================

# 定义允许的文件后缀
ALLOWED_EXTENSIONS = {'json'}

# 定义文件名关键词与文件夹的映射关系
# 逻辑：文件名包含 "China_JP" -> 存入 database/raw/Japan/
REGION_MAPPING = {
    "Japan": "Japan", "JP": "Japan", "China-Japan": "Japan",
    "US": "US", "China_US": "US", "China-US": "US",
    "Taiwan": "Taiwan", "TW": "Taiwan",
    "Philippines": "Philippines", "PH": "Philippines"
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload_raw', methods=['POST'])
def upload_raw_file():
    if 'file' not in request.files:
        return jsonify({"error": "没有文件被上传"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "文件名不能为空"}), 400
        
    if file and allowed_file(file.filename):
        # 1. 安全处理文件名 (防止 ../../etc/passwd 这种攻击)
        # 注意：secure_filename 可能会把中文变空，如果文件名全是中文，建议用 uuid 重命名或自己清洗
        # 针对你的格式 "search_China_Japan_..." 它是英文的，没问题
        filename = secure_filename(file.filename)
        
        # 2. 自动识别地区
        target_subfolder = "Uncategorized" # 默认文件夹
        for key, region in REGION_MAPPING.items():
            if key.lower() in filename.lower():
                target_subfolder = region
                break
        
        # 3. 构造保存路径: database/raw/{Region}/
        # BASE_DIR 是 server 的上一级 (demo/)，所以是 demo/database/raw/Japan
        save_dir = os.path.join(os.path.dirname(BASE_DIR), 'database', 'raw', target_subfolder)
        
        # 自动创建文件夹
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        save_path = os.path.join(save_dir, filename)
        
        try:
            file.save(save_path)
            return jsonify({
                "status": "success", 
                "message": f"文件已归档至 [{target_subfolder}]",
                "path": save_path
            })
        except Exception as e:
            return jsonify({"error": f"保存失败: {str(e)}"}), 500

    return jsonify({"error": "不支持的文件格式，仅支持 JSON"}), 400

# ... (后面的 submit_task 等代码保持不变) ...