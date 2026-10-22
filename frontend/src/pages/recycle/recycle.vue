<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="回收站" subtitle="删掉的东西，还能捞回来" /><!-- #endif -->

    <view class="tip-card">
      <text class="tip-title">删掉的东西会在这里躺 {{ retainDays }} 天。</text>
      <text class="tip-sub">超过期限就真的烧掉了，连照片一起。</text>
    </view>

    <view v-if="loading && !groups.length" class="loading-text">牛马拉磨中…</view>

    <view v-else-if="!groups.length" class="empty">
      <text class="empty-title">回收站是空的。</text>
      <text class="empty-sub">挺好，说明你没手滑。</text>
    </view>

    <view v-else>
      <view v-for="g in groups" :key="g.type" class="group">
        <view class="section-title">
          <text>{{ g.label }}</text>
          <text class="section-extra">{{ g.count }} 条</text>
        </view>
        <view v-for="it in g.items" :key="it.type + '-' + it.id" class="rc-item">
          <view class="rc-main">
            <text class="rc-title">{{ it.title }}</text>
            <text class="rc-sub">{{ it.occurred_at }} · 删除于 {{ String(it.deleted_at).slice(0, 16) }}</text>
          </view>
          <view class="rc-right">
            <text class="rc-days">剩 {{ it.days_left }} 天</text>
            <view class="rc-btn" @click="restore(it)">恢复</view>
          </view>
        </view>
      </view>
    </view>

    <view style="height: 60rpx"></view>
    <BackTop :scroll-top="pageScroll" bare />
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow, onPullDownRefresh, onPageScroll } from '@dcloudio/uni-app'
import { apiRecycleBin, apiRestoreRecycle } from '@/api'
import WebLayout from '@/components/WebLayout.vue'
import BackTop from '@/components/BackTop.vue'

const groups = ref([])
const pageScroll = ref(0)
const retainDays = ref(30)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await apiRecycleBin()
    groups.value = data.groups || []
    retainDays.value = data.retain_days || 30
  } finally {
    loading.value = false
  }
}

async function restore(it) {
  try {
    await apiRestoreRecycle(it.type, it.id)
    uni.showToast({ title: '捞回来了', icon: 'none' })
    load()
  } catch (e) { /* toast 已统一 */ }
}

onShow(load)
onPullDownRefresh(async () => {
  const guard = setTimeout(() => uni.stopPullDownRefresh(), 8000)
  try {
    await load()
  } finally {
    clearTimeout(guard)
    uni.stopPullDownRefresh()
  }
})
onPageScroll((e) => { pageScroll.value = e.scrollTop })
</script>

<style scoped>
.page { padding: 24rpx; }

.tip-card {
  background: var(--warn-l); border: 1rpx solid #F0DCB4; border-radius: 20rpx;
  padding: 24rpx; margin-bottom: 24rpx;
}
.tip-title { display: block; font-size: 26rpx; font-weight: 600; color: var(--warn); }
.tip-sub { display: block; font-size: 21rpx; color: var(--ink3); margin-top: 8rpx; line-height: 1.6; }

.group { margin-bottom: 28rpx; }
.rc-item {
  display: flex; align-items: center; gap: 16rpx; background: #fff;
  border: 1rpx solid var(--line2); border-radius: 18rpx; padding: 22rpx; margin-bottom: 12rpx;
}
.rc-main { flex: 1; display: flex; flex-direction: column; gap: 6rpx; min-width: 0; }
.rc-title { font-size: 27rpx; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rc-sub { font-size: 19rpx; color: var(--ink3); }
.rc-right { display: flex; flex-direction: column; align-items: flex-end; gap: 10rpx; flex-shrink: 0; }
.rc-days { font-size: 19rpx; color: var(--warn); }
.rc-btn {
  padding: 8rpx 22rpx; border-radius: 9999rpx; font-size: 22rpx;
  background: var(--brand-l); color: var(--brand-d); font-weight: 600;
}

@media (min-width: 768px) {
  .page { max-width: 720px; margin: 0 auto; }
}
</style>
