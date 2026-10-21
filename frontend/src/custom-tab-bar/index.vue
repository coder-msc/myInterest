<template>
  <view class="tabbar">
    <view
      v-for="item in list"
      :key="item.pagePath"
      :class="['tab-item', current === item.pagePath ? 'active' : '']"
      @click="switchTab(item.pagePath)"
    >
      <text class="tab-emoji">{{ item.emoji }}</text>
      <text class="tab-text">{{ item.text }}</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'

const list = [
  { pagePath: '/pages/journal/journal', text: '手札', emoji: '🏠' },
  { pagePath: '/pages/ledger/ledger', text: '账本', emoji: '💰' },
  { pagePath: '/pages/worth/worth', text: '值得记', emoji: '🎯' },
  { pagePath: '/pages/discover/discover', text: '发现', emoji: '🔍' },
  { pagePath: '/pages/mine/mine', text: '我的', emoji: '👤' },
]

const current = ref('/pages/journal/journal')

function switchTab(path) {
  if (current.value === path) return
  current.value = path
  uni.switchTab({ url: path })
}

// 监听页面切换，更新高亮
const pages = getCurrentPages()
if (pages.length) {
  current.value = '/' + pages[pages.length - 1].route
}
</script>

<style scoped>
.tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 112rpx;
  background: #FFFFFF;
  border-top: 1rpx solid #F6EFE7;
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding-bottom: env(safe-area-inset-bottom);
  z-index: 999;
}
.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4rpx;
  color: #9C9187;
}
.tab-item.active { color: #D97742; }
.tab-emoji { font-size: 38rpx; line-height: 1; }
.tab-text { font-size: 22rpx; }
.tab-item.active .tab-text { font-weight: 600; }
</style>
