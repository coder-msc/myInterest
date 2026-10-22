<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="提醒中心" subtitle="站内消息，是最稳的那条通道" /><!-- #endif -->

    <view class="head">
      <text class="head-count">{{ unread ? `${unread} 条未读` : '都看过了' }}</text>
      <text v-if="unread" class="head-action" @click="readAll">全部已读</text>
    </view>

    <view v-if="loading && !items.length" class="loading-text">牛马拉磨中…</view>

    <view v-else-if="!items.length" class="empty">
      <text class="empty-title">没有新消息。</text>
      <text class="empty-sub">重要的日子临近时，这里会有提醒。</text>
    </view>

    <view v-else class="msg-list">
      <view v-for="m in items" :key="m.id"
            :class="['msg', m.is_read ? 'read' : '']"
            @click="openMsg(m)" @longpress="removeMsg(m)">
        <view class="msg-dot" v-if="!m.is_read"></view>
        <view class="msg-main">
          <view class="msg-top">
            <text class="msg-title">{{ m.title }}</text>
            <text class="msg-time">{{ shortTime(m.created_at) }}</text>
          </view>
          <text v-if="m.content" class="msg-content">{{ m.content }}</text>
        </view>
      </view>

      <view class="list-foot">
        <text v-if="loadingMore">加载中…</text>
        <text v-else-if="hasMore" @click="loadMore">加载更多</text>
        <text v-else>没有更多了</text>
      </view>
    </view>

    <view class="notice">
      <text class="notice-text">
        提醒只在 App 内以站内消息展示。受系统限制，无法保证在其他渠道准时送达；
        建议每天打开手札看一眼。
      </text>
    </view>

    <view style="height: 60rpx"></view>
    <BackTop :scroll-top="pageScroll" />
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow, onPullDownRefresh, onReachBottom, onPageScroll } from '@dcloudio/uni-app'
import {
  apiNotifications, apiReadNotification, apiReadAllNotifications, apiDeleteNotification,
} from '@/api'
import WebLayout from '@/components/WebLayout.vue'
import BackTop from '@/components/BackTop.vue'

const items = ref([])
const unread = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const hasMore = ref(false)
const page = ref(1)
const pageScroll = ref(0)

function shortTime(s) {
  if (!s) return ''
  return String(s).slice(5, 16)
}

async function load(reset = true) {
  loading.value = true
  try {
    const data = await apiNotifications({ page: reset ? 1 : page.value, page_size: 20 })
    items.value = reset ? (data.items || []) : items.value.concat(data.items || [])
    unread.value = data.unread || 0
    hasMore.value = !!data.has_more
    page.value = (data.page || 1) + 1
  } finally {
    loading.value = false
    // #ifdef MP-WEIXIN || MP-ALIPAY
    uni.stopPullDownRefresh()
    // #endif
  }
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  try {
    await load(false)
  } finally {
    loadingMore.value = false
  }
}

async function openMsg(m) {
  if (!m.is_read) {
    await apiReadNotification(m.id)
    m.is_read = true
    unread.value = Math.max(0, unread.value - 1)
  }
  if (m.ref_type === 'countdown') {
    uni.setStorageSync('worth_tab', 'countdown')
    uni.switchTab({ url: '/pages/worth/worth' })
  }
}

async function readAll() {
  await apiReadAllNotifications()
  items.value.forEach(m => { m.is_read = true })
  unread.value = 0
  uni.showToast({ title: '都标成看过了', icon: 'none' })
}

function removeMsg(m) {
  uni.showModal({
    title: '真的删？',
    content: '它不会记仇。',
    confirmText: '删掉',
    confirmColor: '#C0555F',
    success: async (res) => {
      if (!res.confirm) return
      await apiDeleteNotification(m.id)
      items.value = items.value.filter(x => x.id !== m.id)
      if (!m.is_read) unread.value = Math.max(0, unread.value - 1)
    },
  })
}

onShow(() => load(true))
onPullDownRefresh(() => load(true))
onReachBottom(loadMore)
onPageScroll((e) => { pageScroll.value = e.scrollTop })
</script>

<style scoped>
.page { padding: 24rpx; }

.head { display: flex; align-items: center; justify-content: space-between; padding: 4rpx 6rpx 20rpx; }
.head-count { font-size: 24rpx; color: var(--ink3); }
.head-action { font-size: 24rpx; color: var(--brand-d); font-weight: 600; }

.msg-list { display: flex; flex-direction: column; gap: 14rpx; }
.msg {
  display: flex; gap: 14rpx; background: #fff; border: 1rpx solid var(--line2);
  border-radius: 20rpx; padding: 24rpx;
}
.msg.read { opacity: 0.62; }
.msg-dot { width: 14rpx; height: 14rpx; border-radius: 50%; background: var(--brand); margin-top: 12rpx; flex-shrink: 0; }
.msg-main { flex: 1; display: flex; flex-direction: column; gap: 8rpx; min-width: 0; }
.msg-top { display: flex; align-items: baseline; justify-content: space-between; gap: 16rpx; }
.msg-title { font-size: 28rpx; font-weight: 600; color: var(--ink); flex: 1; }
.msg-time { font-size: 19rpx; color: var(--ink3); flex-shrink: 0; }
.msg-content { font-size: 23rpx; color: var(--ink2); line-height: 1.65; }

.list-foot { text-align: center; font-size: 22rpx; color: var(--ink3); padding: 20rpx 0; }

.notice { margin-top: 26rpx; padding: 22rpx 24rpx; background: var(--line2); border-radius: 16rpx; }
.notice-text { font-size: 20rpx; color: var(--ink3); line-height: 1.7; }

@media (min-width: 768px) {
  .page { max-width: 720px; margin: 0 auto; }
}
</style>
