<template>
  <view class="page">
    <view v-if="loading" class="loading-text">牛马拉磨中…</view>

    <block v-else-if="trip">
      <!-- 封面 -->
      <view class="hero">
        <image v-if="trip.cover_url" class="hero-img" :src="mediaUrl(trip.cover_url)" mode="aspectFill" />
        <view v-else class="hero-img hero-empty"><text>🧳</text></view>
        <view class="hero-mask"></view>
        <view class="hero-text">
          <text class="hero-title">{{ trip.title }}</text>
          <text class="hero-dest">{{ trip.destinations.join(' · ') }}</text>
          <text class="hero-date">{{ trip.start_date }} → {{ trip.end_date }}</text>
        </view>
      </view>

      <!-- 信息 -->
      <view class="card info">
        <view class="info-row" v-if="trip.companions">
          <text class="ir-label">同行</text><text class="ir-val">{{ trip.companions }}</text>
        </view>
        <view class="info-row" v-if="trip.cost">
          <text class="ir-label">花费</text><text class="ir-val">¥{{ money(trip.cost) }}</text>
        </view>
        <view class="info-row">
          <text class="ir-label">照片</text><text class="ir-val">{{ trip.photos.length }} 张</text>
        </view>
      </view>

      <!-- 文字 -->
      <view v-if="trip.content" class="card">
        <text class="note">{{ trip.content }}</text>
      </view>

      <!-- 相册 -->
      <view v-if="trip.photos.length" class="card">
        <view class="section-title"><text>照片</text><text class="section-extra">{{ trip.photos.length }} 张</text></view>
        <view class="gallery">
          <image v-for="p in trip.photos" :key="p.id" class="g-img"
                 :src="mediaUrl(p.thumb_url || p.url)" mode="aspectFill"
                 @click="preview(p)" />
        </view>
      </view>

      <view class="actions">
        <button class="btn-ghost" @click="remove">删除这趟</button>
      </view>
    </block>

    <view v-else class="empty">
      <text class="empty-title">这趟行程不见了。</text>
      <text class="empty-sub">可能被删了，也可能是链接不对。</text>
    </view>

    <view style="height: 60rpx"></view>
    <BackTop :scroll-top="pageScroll" bare />
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad, onShow, onPageScroll } from '@dcloudio/uni-app'
import { apiTrip, apiDeleteTrip } from '@/api'
import { mediaUrl } from '@/utils/config'
import BackTop from '@/components/BackTop.vue'

const trip = ref(null)
const pageScroll = ref(0)
const loading = ref(true)
let tripId = 0

function money(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function load() {
  loading.value = true
  try {
    trip.value = await apiTrip(tripId)
  } catch (e) {
    trip.value = null
  } finally {
    loading.value = false
  }
}

function preview(p) {
  const urls = trip.value.photos.map(x => mediaUrl(x.url))
  uni.previewImage({ urls, current: mediaUrl(p.url) })
}

function remove() {
  uni.showModal({
    title: '真的删？',
    content: '它不会记仇。',
    confirmText: '删掉',
    confirmColor: '#C0555F',
    success: async (res) => {
      if (!res.confirm) return
      await apiDeleteTrip(tripId)
      uni.navigateBack()
    },
  })
}

onLoad((query) => {
  tripId = Number(query?.id || 0)
})
onShow(() => {
  if (tripId) load()
})
onPageScroll((e) => { pageScroll.value = e.scrollTop })
</script>

<style scoped>
.page { padding: 0 0 24rpx; }

.hero { position: relative; height: 460rpx; }
.hero-img { width: 100%; height: 100%; }
.hero-empty {
  display: flex; align-items: center; justify-content: center;
  font-size: 90rpx; background: linear-gradient(135deg, #FDF1E7, #F3E3D4);
}
.hero-mask {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(47,42,38,0.05) 30%, rgba(47,42,38,0.72) 100%);
}
.hero-text { position: absolute; left: 32rpx; right: 32rpx; bottom: 32rpx; display: flex; flex-direction: column; gap: 8rpx; }
.hero-title { font-size: 40rpx; font-weight: 700; color: #fff; }
.hero-dest { font-size: 26rpx; color: rgba(255,255,255,0.92); }
.hero-date { font-size: 22rpx; color: rgba(255,255,255,0.8); }

.card { margin: 24rpx 24rpx 0; }
.info { padding: 8rpx 28rpx; }
.info-row { display: flex; align-items: center; justify-content: space-between; padding: 20rpx 0; border-bottom: 1rpx solid var(--line2); }
.info-row:last-child { border-bottom: none; }
.ir-label { font-size: 24rpx; color: var(--ink3); }
.ir-val { font-size: 26rpx; color: var(--ink); font-weight: 500; }

.note { font-size: 27rpx; color: var(--ink2); line-height: 1.8; white-space: pre-wrap; }

.gallery { display: flex; flex-wrap: wrap; gap: 12rpx; }
.g-img { width: calc(33.33% - 8rpx); height: 200rpx; border-radius: 14rpx; background: var(--line2); }

.actions { padding: 40rpx 24rpx 0; }

@media (min-width: 768px) {
  .page { max-width: 720px; margin: 0 auto; }
  .hero { border-radius: 0 0 24rpx 24rpx; overflow: hidden; }
}
</style>
