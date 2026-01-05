import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'  // 1. 引入 path 模块

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  
  // 2. 添加 resolve 配置
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src') 
    }
  }
})