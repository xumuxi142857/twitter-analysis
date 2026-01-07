import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layout/MainLayout.vue'
import TopicAnalysis from '@/views/TopicAnalysis/index.vue'
import AccountRec from '@/views/AccountRec/index.vue'
import TweetGuide from '@/views/TweetGuide/index.vue'
import TargetDetect from '@/views/TargetDetect/index.vue'
// 引入登录页
import Login from '@/views/Login/index.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // 1. 登录路由 (在 MainLayout 之外)
    {
      path: '/login',
      name: 'Login',
      component: Login
    },
    // 2. 主业务路由 (被 MainLayout 包裹)
    {
      path: '/',
      component: MainLayout,
      redirect: '/topic',
      children: [
        { path: 'topic', component: TopicAnalysis },
        { path: 'account', component: AccountRec },
        { path: 'guide', component: TweetGuide },
        { path: 'detect', component: TargetDetect }
      ]
    }
  ]
})

// 3. 全局前置守卫 (关键逻辑)
router.beforeEach((to, from, next) => {
  // 获取登录状态
  const isAuthenticated = localStorage.getItem('isLoggedIn') === 'true';
  
  if (to.path !== '/login' && !isAuthenticated) {
    // 如果去的不是登录页，且没登录 -> 强制跳到登录页
    next('/login');
  } else if (to.path === '/login' && isAuthenticated) {
    // 如果已登录还想去登录页 -> 踢回主页
    next('/');
  } else {
    // 放行
    next();
  }
});

export default router