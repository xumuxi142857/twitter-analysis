<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-banner">
        <div class="banner-content">
          <div class="logo-circle">
            <el-icon><Monitor /></el-icon>
          </div>
          <h2>社交媒体分析系统</h2>
          
          <ul class="feature-list">
            <li><el-icon><DataLine /></el-icon> 多维情报溯源</li>
            <li><el-icon><Cpu /></el-icon> 大模型认知博弈</li>
            <li><el-icon><Aim /></el-icon> 重点目标监测</li>
          </ul>
        </div>
      </div>

      <div class="login-form">
        <h3>登录</h3>
        
        
        <el-form 
          ref="formRef"
          :model="loginForm" 
          :rules="rules" 
          label-position="top"
          size="large"
        >
          <el-form-item label="账号" prop="username">
            <el-input 
              v-model="loginForm.username" 
              placeholder="请输入管理员账号" 
              :prefix-icon="User"
            />
          </el-form-item>
          
          <el-form-item label="密码" prop="password">
            <el-input 
              v-model="loginForm.password" 
              type="password" 
              placeholder="请输入密码" 
              :prefix-icon="Lock"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-button 
            type="primary" 
            class="login-btn" 
            :loading="loading" 
            @click="handleLogin"
          >
            立即登录
          </el-button>
        </el-form>

        <div class="footer-text">
          <span>v1.0.0 Research Edition</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { User, Lock, Monitor, DataLine, Cpu, Aim } from '@element-plus/icons-vue';

const router = useRouter();
const loading = ref(false);
const formRef = ref();

const loginForm = reactive({
  username: 'admin',
  password: ''
});

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
};

const handleLogin = async () => {
  if (!formRef.value) return;
  
  await formRef.value.validate((valid: boolean) => {
    if (valid) {
      loading.value = true;
      
      // 模拟登录请求延迟
      setTimeout(() => {
        // --- 硬编码验证逻辑 ---
        if (loginForm.username === 'admin' && loginForm.password === '123456') {
          // 1. 存储 Token (这里用简单的标志位)
          localStorage.setItem('isLoggedIn', 'true');
          localStorage.setItem('username', loginForm.username);
          
          ElMessage.success('登录成功');
          
          // 2. 跳转到主页
          router.push('/');
        } else {
          ElMessage.error('账号或密码错误 (默认: admin / 123456)');
        }
        loading.value = false;
      }, 800);
    }
  });
};
</script>

<style scoped lang="scss">
.login-container {
  height: 100vh;
  width: 100vw;
  background: linear-gradient(135deg, #f0f4f8 0%, #dbeafe 100%);
  display: flex;
  justify-content: center;
  align-items: center;
}

.login-box {
  width: 900px;
  height: 550px;
  background: white;
  border-radius: 20px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  display: flex;
  overflow: hidden;
}

/* 左侧 Banner */
.login-banner {
  width: 50%;
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  padding: 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: white;
  position: relative;
  
  &::after {
    content: '';
    position: absolute;
    top: -50px; left: -50px;
    width: 200px; height: 200px;
    background: rgba(255,255,255,0.1);
    border-radius: 50%;
  }

  .logo-circle {
    width: 60px; height: 60px;
    background: rgba(255,255,255,0.2);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 32px; margin-bottom: 20px;
  }

  h2 { font-size: 28px; margin: 0 0 10px 0; font-weight: 700; }
  p { opacity: 0.8; margin-bottom: 40px; font-size: 14px; letter-spacing: 1px; }
  
  .feature-list {
    list-style: none; padding: 0; margin: 0;
    li {
      display: flex; align-items: center; gap: 10px;
      margin-bottom: 15px; font-size: 16px; font-weight: 500;
      opacity: 0.9;
    }
  }
}

/* 右侧 Form */
.login-form {
  width: 50%;
  padding: 60px 50px;
  display: flex;
  flex-direction: column;
  justify-content: center;

  h3 { font-size: 24px; color: #1f2937; margin: 0 0 8px 0; }
  .welcome-text { color: #6b7280; font-size: 14px; margin-bottom: 30px; }

  .login-btn {
    width: 100%;
    margin-top: 10px;
    height: 44px;
    font-size: 16px;
    font-weight: 600;
    border-radius: 8px;
  }

  .footer-text {
    margin-top: auto;
    text-align: center;
    font-size: 12px;
    color: #9ca3af;
  }
}
</style>