<template>
  <div class="upload-container">
    <div class="header">
      <h1>📂 数据入库 (Raw Data)</h1>
      <p>上传爬虫生成的原始 JSON 文件，系统将自动识别地区并归档</p>
    </div>

    <div class="upload-card">
      <el-upload
        class="upload-area"
        drag
        action="/api/upload_raw"
        multiple
        :on-success="handleSuccess"
        :on-error="handleError"
        :before-upload="beforeUpload"
        accept=".json"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处，或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            ⚠️ 命名规范：<code>search_{地区}_{时间}.json</code> (例如: search_China_JP_20260203.json)
          </div>
        </template>
      </el-upload>

      <div class="log-list" v-if="uploadLogs.length > 0">
        <h3>上传记录</h3>
        <div v-for="(log, idx) in uploadLogs" :key="idx" class="log-item" :class="log.status">
          <span class="time">[{{ log.time }}]</span>
          <span class="msg">{{ log.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { UploadFilled } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import dayjs from 'dayjs';

interface Log { time: string; message: string; status: 'success' | 'error' }
const uploadLogs = ref<Log[]>([]);

const beforeUpload = (rawFile: any) => {
  if (rawFile.type !== 'application/json' && !rawFile.name.endsWith('.json')) {
    ElMessage.error('仅支持 JSON 格式文件');
    return false;
  }
  return true;
};

const handleSuccess = (response: any, uploadFile: any) => {
  uploadLogs.value.unshift({
    time: dayjs().format('HH:mm:ss'),
    message: `✅ ${uploadFile.name} -> ${response.message}`,
    status: 'success'
  });
  ElMessage.success(`上传成功: ${uploadFile.name}`);
};

const handleError = (error: any, uploadFile: any) => {
  let msg = '上传失败';
  try {
    const res = JSON.parse(error.message);
    msg = res.error || '服务器内部错误';
  } catch (e) {}
  
  uploadLogs.value.unshift({
    time: dayjs().format('HH:mm:ss'),
    message: `❌ ${uploadFile.name}: ${msg}`,
    status: 'error'
  });
  ElMessage.error(msg);
};
</script>

<style scoped lang="scss">
.upload-container { max-width: 800px; margin: 40px auto; padding: 0 20px; }
.header { text-align: center; margin-bottom: 30px; h1 { margin-bottom: 10px; } p { color: #666; } }

.upload-card {
  background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.upload-area {
  :deep(.el-upload-dragger) { padding: 40px; }
  .el-upload__text { font-size: 16px; margin-top: 10px; }
  code { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; color: #d63384; font-family: monospace; }
}

.log-list {
  margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;
  h3 { font-size: 15px; margin-bottom: 15px; }
}

.log-item {
  font-size: 13px; margin-bottom: 8px; font-family: monospace;
  &.success { color: #10b981; }
  &.error { color: #ef4444; }
  .time { color: #999; margin-right: 10px; }
}
</style>