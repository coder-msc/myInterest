<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="发现" subtitle="给打工人用的几个小工具" /><!-- #endif -->

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

    <view style="height: 180rpx"></view>

    <!-- #ifdef H5 --><CustomTab current="/pages/discover/discover" /><!-- #endif -->
  </view>
</template>

<script setup>
import { computed } from 'vue'
import { groupedTools } from '@/utils/tools'
import WebLayout from '@/components/WebLayout.vue'
import CustomTab from '@/components/CustomTab.vue'

const groups = computed(() => groupedTools())

function openTool(key) {
  uni.navigateTo({ url: `/pages/tools/tool?key=${key}` })
}
</script>

<style scoped>
.page { padding: 24rpx; }

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
