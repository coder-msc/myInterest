<template>
  <!-- 仅 H5 端 ≥768px 渲染顶部导航；移动端保持自定义 TabBar -->
  <!-- #ifdef H5 -->
  <!-- 占位块：顶栏是 fixed，靠它在文档流里让出 60px，避免遮住页面顶部内容 -->
  <view v-if="showDesktop" class="web-spacer"></view>
  <view v-if="showDesktop" class="web-topbar">
    <view class="topbar-left">
      <view class="brand" @click="go('/pages/journal/journal')">
        <view class="logo">牛</view>
        <view class="brand-text">
          <view class="brand-name">纯牛马人生手札</view>
          <view class="brand-sub">认真活着，随手记着</view>
        </view>
      </view>
      <nav class="nav">
        <view v-for="item in menus" :key="item.path"
              :class="['nav-item', current === item.path ? 'active' : '']"
              @click="go(item.path)">
          <SvgIcon :name="item.icon" :size="30" :stroke="2" />
          <text>{{ item.label }}</text>
        </view>
      </nav>
    </view>
    <view class="topbar-right">
      <slot name="actions" />
      <view class="user-box" @click="goMine">
        <view class="avatar">{{ avatarText }}</view>
        <view class="user-name">{{ nickname }}</view>
      </view>
    </view>
  </view>
  <!-- #endif -->
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { userStore } from '@/store/user'
import SvgIcon from './SvgIcon.vue'

defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
})

const showDesktop = ref(false)
const current = ref('')
const menus = [
  { path: '/pages/journal/journal', label: '手札', icon: 'home' },
  { path: '/pages/ledger/ledger', label: '账本', icon: 'record' },
  { path: '/pages/worth/worth', label: '值得记', icon: 'calendar' },
  { path: '/pages/discover/discover', label: '发现', icon: 'stats' },
  { path: '/pages/mine/mine', label: '我的', icon: 'mine' },
]

const user = computed(() => userStore.user || {})
const nickname = computed(() => user.value.nickname || user.value.username || '用户')
const avatarText = computed(() => user.value.avatar || (nickname.value || 'U').charAt(0).toUpperCase())

function checkWidth() {
  // #ifdef H5
  showDesktop.value = window.innerWidth >= 768
  // #endif
}

function go(path) {
  if (current.value === path) return
  uni.switchTab({ url: path, fail: () => uni.reLaunch({ url: path }) })
}
function goMine() { go('/pages/mine/mine') }

onMounted(() => {
  checkWidth()
  // #ifdef H5
  window.addEventListener('resize', checkWidth)
  // #endif
})
onUnmounted(() => {
  // #ifdef H5
  window.removeEventListener('resize', checkWidth)
  // #endif
})
onShow(() => {
  // #ifdef H5
  const pages = getCurrentPages()
  if (pages.length) {
    current.value = '/' + pages[pages.length - 1].route
  }
  checkWidth()
  // #endif
})
</script>

<style>
/* #ifdef H5 */
.web-spacer { height: 60px; }
.web-topbar {
  position: fixed; top: 0; left: 0; right: 0; height: 60px; z-index: 999;
  background: rgba(255, 255, 255, 0.94); backdrop-filter: blur(8px);
  border-bottom: 1px solid #EDE3D8;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px;
}
.topbar-left { display: flex; align-items: center; gap: 32px; }
.brand { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.logo {
  width: 34px; height: 34px; border-radius: 10px;
  background: linear-gradient(135deg, #D97742, #B85C2E);
  color: #fff; font-weight: 700; font-size: 17px;
  display: flex; align-items: center; justify-content: center;
}
.brand-text { line-height: 1.2; }
.brand-name { font-weight: 700; font-size: 15px; color: #2F2A26; letter-spacing: 0.5px; }
.brand-sub { font-size: 11px; color: #9C9187; }
.nav { display: flex; align-items: center; gap: 4px; }
.nav-item {
  display: flex; align-items: center; gap: 6px; padding: 8px 14px;
  border-radius: 10px; color: #6B625A; font-size: 14px; cursor: pointer;
  transition: all 0.15s; white-space: nowrap;
}
.nav-item:hover { background: #F6EFE7; color: #B85C2E; }
.nav-item.active { background: #FDF1E7; color: #B85C2E; font-weight: 600; }
.topbar-right { display: flex; align-items: center; gap: 16px; }
.user-box { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.avatar {
  width: 34px; height: 34px; border-radius: 50%; background: #FDF1E7;
  color: #B85C2E; font-weight: 600; display: flex; align-items: center; justify-content: center;
}
.user-name { font-size: 14px; font-weight: 500; color: #2F2A26; }

@media (min-width: 768px) {
  uni-tabbar, .uni-tabbar, uni-tabbar + view { display: none !important; }
}
/* #endif */
</style>
