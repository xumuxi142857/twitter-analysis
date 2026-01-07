<template>
  <div class="common-layout">
    <el-container>
      <el-aside width="240px" class="app-aside">
        <div class="logo-area">
          <div class="logo-icon">
            <el-icon><Monitor /></el-icon>
          </div>
          <span class="logo-text">舆情情报分析</span>
        </div>

        <el-menu
          :default-active="activePath"
          class="el-menu-vertical"
          router
        >
          <el-menu-item index="/topic">
            <el-icon><DataAnalysis /></el-icon>
            <span>舆情话题溯源</span>
          </el-menu-item>
          
          <el-menu-item index="/account">
            <el-icon><User /></el-icon>
            <span>重点账号画像</span>
          </el-menu-item>

          <el-menu-item index="/guide">
            <el-icon><Compass /></el-icon>
            <span>智能推文引导</span>
          </el-menu-item>

          <el-menu-item index="/detect">
            <el-icon><Aim /></el-icon>
            <span>重点目标监测</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-container>
        <el-header class="app-header">
          <div class="breadcrumb">
            <span class="curr-path">Dashboard</span> / <span class="active-path">{{ currentRouteName }}</span>
          </div>
          
          <div class="user-info">
            <el-dropdown @command="handleCommand">
              <div class="user-trigger">
                <el-avatar :size="32" class="user-avatar" style="background:#409eff">AD</el-avatar>
                <span class="username">Admin</span>
                <el-icon><CaretBottom /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout" style="color: #f56c6c;">
                    <el-icon><SwitchButton /></el-icon> 退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <el-main class="app-main">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
// ⚠️ 关键修正：这里合并了所有图标的引用，确保 Monitor 只出现一次
import { 
  Monitor, 
  DataAnalysis, 
  User, 
  Compass, 
  Aim, 
  CaretBottom, 
  SwitchButton 
} from '@element-plus/icons-vue';

const route = useRoute();
const router = useRouter();

// 计算当前激活的菜单项
const activePath = computed(() => route.path);

// 计算面包屑显示的名称
const currentRouteName = computed(() => {
  const map: Record<string, string> = {
    '/topic': 'Topic Analysis (话题溯源)',
    '/account': 'Account Recommendation (账号画像)',
    '/guide': 'Tweet Guidance (推文引导)',
    '/detect': 'Target Detection (目标监测)'
  };
  // 简单匹配，如果路径包含key则返回
  for (const key in map) {
    if (route.path.startsWith(key)) return map[key];
  }
  return 'Dashboard';
});

// 处理登出逻辑
const handleCommand = (command: string) => {
  if (command === 'logout') {
    // 1. 清除本地存储
    localStorage.removeItem('isLoggedIn');
    localStorage.removeItem('username');
    // 2. 跳转回登录页
    router.push('/login');
  }
};
</script>

<style scoped lang="scss">
.common-layout {
  height: 100vh;
  width: 100vw;
  background-color: #f0f4f8;
  display: flex;
}

.el-container {
  height: 100%;
  width: 100%;
}

/* 侧边栏样式 */
.app-aside {
  background-color: #ffffff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
}

.logo-area {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid #f3f4f6;
  
  .logo-icon {
    width: 32px;
    height: 32px;
    background: #2563eb;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 12px;
    color: white;
    font-size: 20px;
  }
  
  .logo-text {
    font-size: 16px;
    font-weight: 700;
    color: #1f2937;
  }
}

.el-menu-vertical {
  border-right: none;
  padding-top: 10px;
}

:deep(.el-menu-item) {
  margin: 4px 12px;
  border-radius: 8px;
  height: 48px;
  color: #6b7280;
  
  &.is-active {
    background-color: #eff6ff;
    color: #2563eb;
    font-weight: 600;
  }
  
  &:hover:not(.is-active) {
    background-color: #f9fafb;
  }
  
  .el-icon {
    font-size: 18px;
  }
}

/* 头部样式 */
.app-header {
  background-color: #ffffff;
  height: 64px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 30px;
}

.breadcrumb {
  font-size: 14px;
  color: #9ca3af;
  
  .active-path {
    color: #1f2937;
    font-weight: 600;
  }
}

.user-info {
  display: flex;
  align-items: center;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 20px;
  transition: background 0.2s;
  
  &:hover {
    background: #f3f4f6;
  }
  
  .username {
    font-size: 14px;
    font-weight: 600;
    color: #374151;
  }
}

/* 内容区域 */
.app-main {
  padding: 0;
  overflow-y: auto;
}

/* 路由切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>