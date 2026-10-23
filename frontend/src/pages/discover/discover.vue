<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="发现" subtitle="工具与树洞，都是给打工人用的" /><!-- #endif -->

    <!-- 可滑动分段：工具 / 树洞，预留继续扩展的位置 -->
    <view class="seg-wrap">
      <scroll-view class="seg-scroll" scroll-x :show-scrollbar="false" :scroll-into-view="'seg-' + tab">
        <view class="seg-row">
          <view v-for="s in segments" :key="s.key" :id="'seg-' + s.key"
                :class="['seg-pill', tab === s.key ? 'on' : '']"
                @click="switchTab(s.key)">
            <text>{{ s.emoji }} {{ s.label }}</text>
          </view>
        </view>
      </scroll-view>
    </view>

    <view :class="['seg-body', slideClass]" @touchstart="onTouchStart" @touchend="onTouchEnd" @touchcancel="onTouchCancel">
      <!-- 工具 -->
      <block v-if="tab === 'tools'">
        <view class="hero">
          <text class="hero-title">算清楚，再决定。</text>
          <text class="hero-sub">所有计算只在你手机上完成，不上传、不留存。</text>
        </view>

        <view v-for="g in groups" :key="g.key" class="group">
          <view class="group-head">
            <text class="group-title">{{ g.emoji }} {{ g.label }}</text>
            <text class="group-desc">{{ g.desc }}</text>
          </view>

          <view class="tool-list">
            <view v-for="t in g.tools" :key="t.key" class="tool-card" @click="openTool(t.key)">
              <text class="tool-emoji">{{ t.emoji }}</text>
              <view class="tool-main">
                <text class="tool-name">{{ t.name }}</text>
                <text class="tool-desc">{{ t.desc }}</text>
              </view>
              <text class="tool-arrow">›</text>
            </view>
          </view>
        </view>

        <view class="notice">
          <text class="notice-title">✳️ 计算结果仅供参考</text>
          <text class="notice-text">税费、社保、利率随城市与政策变化，实际以官方或合同为准。这里不构成任何投资、购房建议。</text>
        </view>
      </block>

      <!-- 树洞：首次进入才加载，避免无谓请求 -->
      <TreeholePanel v-else-if="treeholeReady" />
    </view>

    <view style="height: 180rpx"></view>
    <BackTop :scroll-top="pageScroll" />

    <!-- #ifdef H5 --><CustomTab current="/pages/discover/discover" /><!-- #endif -->
  </view>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { onPageScroll } from '@dcloudio/uni-app'
import { groupedTools } from '@/utils/tools'
import WebLayout from '@/components/WebLayout.vue'
import CustomTab from '@/components/CustomTab.vue'
import TreeholePanel from '@/components/TreeholePanel.vue'
import BackTop from '@/components/BackTop.vue'

const segments = [
  { key: 'tools', label: '工具', emoji: '🔧' },
  { key: 'treehole', label: '树洞', emoji: '🌳' },
]

const tab = ref('tools')
const pageScroll = ref(0)
const treeholeReady = ref(false)
const slideClass = ref('')

const groups = computed(() => groupedTools())

onPageScroll((e) => { pageScroll.value = e.scrollTop })

function playSlide(dir) {
  slideClass.value = ''
  nextTick(() => {
    slideClass.value = dir > 0 ? 'slide-in-right' : 'slide-in-left'
    setTimeout(() => { slideClass.value = '' }, 280)
  })
}

function switchTab(key) {
  if (key === tab.value) return
  const prevIdx = segments.findIndex(s => s.key === tab.value)
  const nextIdx = segments.findIndex(s => s.key === key)
  tab.value = key
  if (key === 'treehole') treeholeReady.value = true
  playSlide(nextIdx >= prevIdx ? 1 : -1)
  uni.pageScrollTo({ scrollTop: 0, duration: 0 })
}

function openTool(key) {
  uni.navigateTo({ url: `/pages/tools/tool?key=${key}` })
}

// 左右滑动切段：横向位移够大且明显大于纵向，避免和页面滚动打架
const touch = { x: 0, y: 0, at: 0, ok: false }

function onTouchStart(e) {
  const t = e.touches && e.touches[0]
  if (!t) { touch.ok = false; return }
  touch.x = t.clientX
  touch.y = t.clientY
  touch.at = Date.now()
  touch.ok = true
}

function onTouchCancel() { touch.ok = false }

function onTouchEnd(e) {
  if (!touch.ok) return
  touch.ok = false
  const t = e.changedTouches && e.changedTouches[0]
  if (!t || Date.now() - touch.at > 700) return
  const dx = t.clientX - touch.x
  const dy = t.clientY - touch.y
  if (Math.abs(dx) < 70 || Math.abs(dx) < Math.abs(dy) * 1.6) return
  const idx = segments.findIndex(s => s.key === tab.value)
  const next = dx < 0 ? idx + 1 : idx - 1
  if (next < 0 || next >= segments.length) return
  switchTab(segments[next].key)
}
</script>

<style scoped>
.page { padding: 24rpx; }

.seg-wrap { margin-bottom: 22rpx; }
.seg-scroll { width: 100%; white-space: nowrap; }
.seg-row { display: inline-flex; gap: 12rpx; padding: 2rpx; }
.seg-pill {
  padding: 12rpx 28rpx; border-radius: 999rpx; font-size: 24rpx;
  color: var(--ink2); background: #fff; border: 1rpx solid var(--line2);
  transition: all 0.18s;
}
.seg-pill.on { background: var(--brand-sel); color: var(--brand-d); border-color: var(--brand-bd); font-weight: 600; }

.seg-body { animation: none; }
.slide-in-right { animation: slideInRight 0.26s cubic-bezier(0.22, 0.61, 0.36, 1); }
.slide-in-left { animation: slideInLeft 0.26s cubic-bezier(0.22, 0.61, 0.36, 1); }
@keyframes slideInRight {
  from { transform: translateX(36rpx); opacity: 0.4; }
  to { transform: translateX(0); opacity: 1; }
}
@keyframes slideInLeft {
  from { transform: translateX(-36rpx); opacity: 0.4; }
  to { transform: translateX(0); opacity: 1; }
}

.hero {
  padding: 28rpx 26rpx; border-radius: 24rpx; margin-bottom: 28rpx;
  background: linear-gradient(135deg, #FDF1E7, #FFF9F4);
  border: 1rpx solid #F3CDB3;
}
.hero-title { display: block; font-size: 32rpx; font-weight: 700; color: var(--ink); }
.hero-sub { display: block; font-size: 21rpx; color: var(--ink3); margin-top: 8rpx; line-height: 1.6; }

.group { margin-bottom: 32rpx; }
.group-head { padding: 0 6rpx 16rpx; }
.group-title { display: block; font-size: 28rpx; font-weight: 700; color: var(--ink); }
.group-desc { display: block; font-size: 20rpx; color: var(--ink3); margin-top: 6rpx; }

.tool-list { display: flex; flex-direction: column; gap: 14rpx; }
.tool-card {
  display: flex; align-items: center; gap: 18rpx; background: #fff;
  border: 1rpx solid var(--line2); border-radius: 20rpx; padding: 24rpx 22rpx;
}
.tool-card:active { background: var(--bg); }
.tool-emoji { font-size: 40rpx; width: 56rpx; text-align: center; flex-shrink: 0; }
.tool-main { flex: 1; display: flex; flex-direction: column; gap: 6rpx; min-width: 0; }
.tool-name { font-size: 28rpx; font-weight: 600; color: var(--ink); }
.tool-desc { font-size: 21rpx; color: var(--ink3); line-height: 1.5; }
.tool-arrow { font-size: 32rpx; color: var(--ink3); }

.notice {
  padding: 24rpx; border-radius: 18rpx; background: var(--line2);
}
.notice-title { display: block; font-size: 22rpx; font-weight: 600; color: var(--ink2); }
.notice-text { display: block; font-size: 20rpx; color: var(--ink3); line-height: 1.7; margin-top: 8rpx; }

@media (min-width: 768px) {
  .page { max-width: 720px; margin: 0 auto; }
}
</style>
