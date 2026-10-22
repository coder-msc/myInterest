<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="家庭资产" subtitle="家底盘点，一年看几次就够" /><!-- #endif -->
    <AssetsPanel ref="panelRef" />
    <view style="height: 60rpx"></view>
    <BackTop :scroll-top="pageScroll" bare />
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow, onPullDownRefresh, onPageScroll } from '@dcloudio/uni-app'
import WebLayout from '@/components/WebLayout.vue'
import AssetsPanel from '@/components/AssetsPanel.vue'
import BackTop from '@/components/BackTop.vue'

const panelRef = ref(null)
const pageScroll = ref(0)

// 面板挂载时自己会取一次；再次回到页面（金额被其他页改过）才重新拉
let shownOnce = false
onShow(() => {
  if (shownOnce && panelRef.value) panelRef.value.reload()
  shownOnce = true
})

onPullDownRefresh(async () => {
  const guard = setTimeout(() => uni.stopPullDownRefresh(), 8000)
  try {
    if (panelRef.value) await panelRef.value.reload()
  } finally {
    clearTimeout(guard)
    uni.stopPullDownRefresh()
  }
})
onPageScroll((e) => { pageScroll.value = e.scrollTop })
</script>

<style scoped>
.page { padding: 24rpx; }
@media (min-width: 768px) {
  .page { max-width: 720px; margin: 0 auto; }
}
</style>
