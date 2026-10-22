<template>
  <view v-if="visible" class="back-top" :style="{ '--lift': lift + 'rpx' }" @click="toTop">
    <text class="bt-arrow">↑</text>
  </view>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  scrollTop: { type: Number, default: 0 },
  // 滚过这个距离才出现，太短就没必要打断阅读
  threshold: { type: Number, default: 640 },
  // 页面右下角已经有悬浮按钮（如手札的「＋」）时，用它把回顶按钮往上抬
  lift: { type: Number, default: 0 },
})

// H5 下页面实际滚动容器不一定是 window（有些端会滚在 uni-page-body 上），
// 这里用捕获监听把所有滚动都算进来；小程序端没有 document，走页面传入的 scrollTop
const localTop = ref(0)
const visible = computed(() => Math.max(props.scrollTop, localTop.value) > props.threshold)

function readTop() {
  localTop.value = Math.max(
    window.scrollY || 0,
    document.scrollingElement ? document.scrollingElement.scrollTop : 0,
    document.documentElement ? document.documentElement.scrollTop : 0,
  )
}

let onScroll = null
onMounted(() => {
  // #ifdef H5
  onScroll = readTop
  window.addEventListener('scroll', onScroll, { passive: true })
  document.addEventListener('scroll', onScroll, true)
  readTop()
  // #endif
})
onUnmounted(() => {
  // #ifdef H5
  if (onScroll) {
    window.removeEventListener('scroll', onScroll)
    document.removeEventListener('scroll', onScroll, true)
  }
  // #endif
})

function toTop() {
  uni.pageScrollTo({ scrollTop: 0, duration: 280 })
  localTop.value = 0
}
</script>

<style scoped>
.back-top {
  position: fixed; right: 32rpx;
  /* 让开底部 tabbar（112rpx）与安全区，lift 用于避让页面自己的悬浮按钮 */
  bottom: calc(150rpx + var(--lift, 0rpx) + env(safe-area-inset-bottom));
  width: 84rpx; height: 84rpx; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255, 255, 255, .96);
  border: 1rpx solid var(--line2, #EFE6DC);
  box-shadow: 0 6rpx 22rpx rgba(90, 60, 40, .14);
  z-index: 900;
  animation: bt-in .18s ease-out;
}
.bt-arrow { font-size: 36rpx; line-height: 1; font-weight: 600; color: var(--ink2, #6B5F55); }
.back-top:active { transform: scale(.94); background: #fff; }

@keyframes bt-in {
  from { opacity: 0; transform: translateY(12rpx); }
  to { opacity: 1; transform: translateY(0); }
}

/* PC 宽屏没有底部栏，按钮往右下角收一点 */
@media (min-width: 768px) {
  .back-top { right: 56rpx; bottom: 64rpx; }
}
</style>
