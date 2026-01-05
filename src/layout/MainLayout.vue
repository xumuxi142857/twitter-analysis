<template>
  <div class="common-layout">
    <el-container class="app-container">
      
      <el-aside width="240px" class="aside-menu">
        <div class="logo-area">
          <div class="logo-icon">
            <el-icon><Monitor /></el-icon>
          </div>
          <span class="system-title">舆情洞察系统</span>
        </div>

        <el-menu
          default-active="/topic"
          router
          class="custom-menu"
        >
          <el-menu-item index="/topic">
            <el-icon><DataAnalysis /></el-icon>
            <span>话题分析 (Topic)</span>
          </el-menu-item>
          
          <el-menu-item index="/account" >
            <el-icon><User /></el-icon>
            <span>账号推荐 (Account)</span>
          </el-menu-item>
          
          <el-menu-item index="/guide" >
            <el-icon><Compass /></el-icon>
            <span>推文引导 (Guide)</span>
          </el-menu-item>
          
          <el-menu-item index="/detect" >
            <el-icon><Aim /></el-icon>
            <span>目标监测 (Detect)</span>
          </el-menu-item>
        </el-menu>
        
        <div class="aside-footer">
          <span class="version">v1.0.0 Research Edition</span>
        </div>
      </el-aside>

      <el-container>
        <el-header class="app-header">
          <div class="breadcrumb">
            <span class="curr-path">Dashboard</span> / <span class="active-path">Analysis</span>
          </div>
          <div class="user-info">
            <el-avatar :size="32" class="user-avatar">Admin</el-avatar>
          </div>
        </el-header>

        <el-main class="app-main">
          <router-view v-slot="{ Component }">
            <transition name="fade-transform" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
      
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { Monitor, DataAnalysis, User, Compass, Aim } from '@element-plus/icons-vue';
</script>

<style scoped lang="scss">
/* 全局容器 */
.common-layout, .app-container {
  height: 100vh;
  background-color: #f0f4f8; /* 与子页面背景融合 */
  overflow: hidden;
}

/* --- 侧边栏样式 --- */
.aside-menu {
  background-color: #ffffff;
  border-right: 1px solid rgba(0, 0, 0, 0.03); /* 极淡的边框 */
  box-shadow: 4px 0 16px rgba(0, 0, 0, 0.03); /* 柔和的右侧阴影 */
  display: flex;
  flex-direction: column;
  z-index: 10; /* 保证阴影在内容之上 */
}

/* Logo 区域 */
.logo-area {
  height: 70px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  border-bottom: 1px solid #f3f4f6;
  
  .logo-icon {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
    border-radius: 8px;
    display: flex;
    justify-content: center;
    align-items: center;
    color: white;
    margin-right: 12px;
    box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.3);
  }

  .system-title {
    font-size: 18px;
    font-weight: 700;
    color: #1f2937;
    letter-spacing: -0.5px;
  }
}

/* 菜单列表核心样式 */
.custom-menu {
  border-right: none;
  padding: 16px 12px;
  flex: 1;

  /* 菜单项基础样式 */
  :deep(.el-menu-item) {
    height: 50px;
    line-height: 50px;
    margin-bottom: 8px;
    border-radius: 12px; /* 胶囊圆角 */
    color: #6b7280;
    font-weight: 500;
    font-size: 15px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border: none;

    /* 图标距离 */
    .el-icon {
      margin-right: 12px;
      font-size: 18px;
    }

    &:hover {
      background-color: #f9fafb; /* 极淡的灰 */
      color: #111827;
      transform: translateX(4px); /* 悬浮微动 */
    }

    /* 选中状态：重点！胶囊样式 */
    &.is-active {
      background-color: #eff6ff; /* 淡蓝背景 */
      color: #2563eb; /* 皇家蓝文字 */
      font-weight: 600;
      box-shadow: 0 2px 4px rgba(37, 99, 235, 0.05);
      
      /* 可以加一个小蓝条指示器 */
      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 15%;
        height: 70%;
        width: 4px;
        background: #2563eb;
        border-radius: 0 4px 4px 0;
        opacity: 0; /* 如果想要更简洁，可以把这个 opacity 设为 0，去掉左侧蓝条 */
      }
    }
    
    /* 禁用状态 */
    &.is-disabled {
      opacity: 0.5;
      background: transparent;
      cursor: not-allowed;
    }
  }
}

/* 底部版本号 */
.aside-footer {
  padding: 20px;
  text-align: center;
  
  .version {
    font-size: 12px;
    color: #9ca3af;
    background: #f3f4f6;
    padding: 4px 10px;
    border-radius: 20px;
  }
}

/* --- 顶部 Header --- */
.app-header {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px); /* 毛玻璃效果 */
  border-bottom: 1px solid rgba(0,0,0,0.03);
  height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 30px;
  
  .breadcrumb {
    font-size: 14px;
    color: #9ca3af;
    .active-path {
      color: #1f2937;
      font-weight: 600;
    }
  }

  .user-avatar {
    background: #2563eb;
    font-size: 12px;
    font-weight: bold;
    cursor: pointer;
  }
}

/* --- 主内容区 --- */
.app-main {
  padding: 0; /* 内部页面自己控制 padding */
  overflow-y: auto;
}

/* 页面切换动画 */
.fade-transform-leave-active,
.fade-transform-enter-active {
  transition: all 0.4s;
}
.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}
.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>