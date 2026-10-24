<!-- CustomTab.vue —— H5 端自定义底部导航（emoji 图标 + 文字）
  用法：tab 页模板末尾 <CustomTab current="/pages/xxx/xxx" />（仅 H5 条件编译引入）
-->
<template>
  <view class="tabbar">
    <view
      v-for="t in tabs"
      :key="t.path"
      :class="['tab-item', t.path === current ? 'on' : '']"
      @click="go(t.path)"
    >
      <text class="tab-emoji">{{ t.emoji }}</text>
      <text class="tab-label">{{ t.label }}</text>
    </view>
  </view>
</template>

<script setup>
import TABS from '@/custom-tab-bar/tabs.json'

const props = defineProps({
  current: { type: String, default: '' },
})

const tabs = TABS

function go(path) {
  if (path === props.current) return
  uni.switchTab({ url: path, fail: () => uni.reLaunch({ url: path }) })
}
</script>

<style scoped>
.tabbar {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: 112rpx;
  padding-bottom: env(safe-area-inset-bottom);
  background: #FFFFFF;
  border-top: 1rpx solid #F6EFE7;
  display: flex;
  z-index: 999;
}
.tab-item {
  flex: 1;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 4rpx;
  color: #9C9187;
}
.tab-item.on { color: #D97742; }
.tab-emoji { font-size: 38rpx; line-height: 1; }
.tab-label { font-size: 22rpx; }
.tab-item.on .tab-label { font-weight: 600; }
/* PC 宽屏走 WebLayout 顶部导航，隐藏底部栏 */
@media (min-width: 768px) {
  .tabbar { display: none; }
}
</style>
