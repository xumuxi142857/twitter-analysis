import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layout/MainLayout.vue'
import TopicAnalysis from '../views/TopicAnalysis/index.vue'
import AccountRec from '../views/AccountRec/index.vue'
import TweetGuide from '@/views/TweetGuide/index.vue'
import TargetDetect from '@/views/TargetDetect/index.vue'

// routes...

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      redirect: '/topic', // 默认跳到话题页
      children: [
        {
          path: 'topic',
          component: TopicAnalysis
        },
        {
            path: 'account', 
            component: AccountRec
        },
        {
            path: 'guide', 
            component: TweetGuide
        },
        { 
            path: 'detect', 
            component: TargetDetect 
        }
        // 未来在这里添加 'account', 'guide' 等路由
      ]
    }
  ]
})

export default router