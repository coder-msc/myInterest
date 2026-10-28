<template>
  <view class="th">
    <!-- 说明 -->
    <view class="th-hero">
      <text class="th-hero-title">说出来，就好了。</text>
      <text class="th-hero-sub">写完就存进你自己的账号，不会公开给其他人看到</text>
      <text class="th-hero-code">{{ anonCode }} · 仅你自己可见</text>
    </view>

    <!-- 发布 -->
    <view class="th-post">
      <textarea v-model="content" class="th-input" maxlength="200"
                placeholder="今天有什么事想说出来？不超过 200 字"
                placeholder-class="th-ph" :disabled="posting" @focus="guardGuest" />
      <view class="th-post-foot">
        <text class="th-count">{{ content.length }}/200</text>
        <text class="th-quota">今天还能发 {{ quota.remaining }} 条</text>
        <view :class="['th-btn', posting || !canPost ? 'disabled' : '']" @click="submit">
          {{ posting ? '提交中…' : '提交审核' }}
        </view>
      </view>
    </view>

    <!-- 我的发言（树洞只对自己可见，不提供公开信息流） -->
    <view class="th-mine-title">我的发言</view>
    <block>
      <view v-if="!mine.length" class="th-empty">
        <text class="th-empty-emoji">📝</text>
        <text class="th-empty-text">你还没在树洞里说过话。</text>
      </view>
      <view v-for="p in mine" :key="p.id" class="th-card">
        <view class="th-card-head">
          <text class="th-status st-approved">仅自己可见</text>
          <text class="th-time">{{ p.created_at.slice(5, 16) }}</text>
        </view>
        <text class="th-content">{{ p.content }}</text>
        <view class="th-card-foot">
          <text v-if="p.reason" class="th-reason">审核说明：{{ p.reason }}</text>
          <text class="th-report" @click="remove(p)">删除</text>
        </view>
      </view>
    </block>

    <view class="th-notice">
      <text class="th-notice-title">✳️ 发言前请知悉</text>
      <text class="th-notice-text">树洞只接受纯文字，不支持图片与评论。内容只保存在你的账号里，不会公开。请勿发布违法内容。</text>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  apiTreeholeMine, apiTreeholeQuota,
  apiCreateTreeholePost, apiDeleteTreeholePost,
} from '@/api'
import { isLoggedIn, requireLogin } from '@/utils/auth'

const content = ref('')
const posting = ref(false)
const mine = ref([])
const quota = ref({ used: 0, limit: 3, remaining: 3 })
const anonCode = ref('')

const canPost = computed(() => content.value.trim().length >= 2 && quota.value.remaining > 0)

/** 访客点输入框就提示登录，不必等写完 200 字再提交被拦 */
function guardGuest() {
  if (isLoggedIn()) return
  requireLogin('登录后才能匿名发言')
}

async function loadMine() {
  try {
    const d = await apiTreeholeMine()
    mine.value = d.items || []
    if (d.anon_code) anonCode.value = d.anon_code
  } catch (e) { /* 统一 toast */ }
}

async function loadQuota() {
  try {
    quota.value = await apiTreeholeQuota()
  } catch (e) { /* 统一 toast */ }
}

async function submit() {
  if (posting.value) return
  if (!canPost.value) {
    if (quota.value.remaining <= 0) uni.showToast({ title: '今天的 3 条已经发完了', icon: 'none' })
    else uni.showToast({ title: '至少写 2 个字', icon: 'none' })
    return
  }
  posting.value = true
  try {
    await apiCreateTreeholePost(content.value.trim())
    content.value = ''
    uni.showToast({ title: '已保存，仅自己可见', icon: 'none' })
    await Promise.all([loadQuota(), loadMine()])
  } catch (e) { /* 统一 toast */ } finally {
    posting.value = false
  }
}

function remove(p) {
  uni.showModal({
    title: '删除这条发言？',
    content: '删除后不会再出现在任何列表里。',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await apiDeleteTreeholePost(p.id)
        mine.value = mine.value.filter(x => x.id !== p.id)
        uni.showToast({ title: '已删除', icon: 'none' })
      } catch (e) { /* 统一 toast */ }
    },
  })
}

onMounted(() => {
  loadMine()
  loadQuota()
})
</script>

<style scoped>
.th { padding-top: 8rpx; }

.th-hero {
  padding: 26rpx 24rpx; border-radius: 24rpx; margin-bottom: 22rpx;
  background: linear-gradient(135deg, #EAE4F5, #F6F2FB);
  border: 1rpx solid #D8CDEB;
}
.th-hero-title { display: block; font-size: 30rpx; font-weight: 700; color: var(--ink); }
.th-hero-sub { display: block; font-size: 20rpx; color: var(--ink3); margin-top: 8rpx; line-height: 1.6; }
.th-hero-code { display: block; font-size: 20rpx; color: #6C5B8E; margin-top: 10rpx; }
.th-mine-title { display: block; font-size: 26rpx; font-weight: 700; color: var(--ink); margin: 4rpx 0 14rpx; }

.th-post { background: #fff; border: 1rpx solid var(--line2); border-radius: 22rpx; padding: 22rpx; margin-bottom: 22rpx; }
.th-input {
  width: 100%; min-height: 150rpx; font-size: 26rpx; color: var(--ink); line-height: 1.7;
  background: var(--bg); border-radius: 14rpx; padding: 16rpx;
}
.th-ph { color: var(--ink3); font-size: 24rpx; }
.th-post-foot { display: flex; align-items: center; gap: 16rpx; margin-top: 16rpx; }
.th-count { font-size: 20rpx; color: var(--ink3); }
.th-quota { flex: 1; font-size: 20rpx; color: var(--ink3); text-align: right; }
.th-btn {
  padding: 12rpx 26rpx; border-radius: 999rpx; font-size: 23rpx; font-weight: 600;
  color: #fff; background: linear-gradient(135deg, #7A6BA8, #5F5189);
}
.th-btn.disabled { opacity: 0.45; }

.th-tabs { display: flex; gap: 12rpx; margin-bottom: 18rpx; }
.th-tab {
  flex: 1; text-align: center; padding: 14rpx 0; border-radius: 14rpx;
  font-size: 24rpx; color: var(--ink2); background: var(--line2);
}
.th-tab.on { background: var(--brand-sel); border-color: var(--brand-bd); color: var(--brand-d); font-weight: 600; }
.th-badge { font-size: 18rpx; margin-left: 6rpx; }

.th-empty { padding: 60rpx 20rpx; text-align: center; }
.th-empty-emoji { display: block; font-size: 56rpx; }
.th-empty-text { display: block; font-size: 22rpx; color: var(--ink3); margin-top: 12rpx; }

.th-card { background: #fff; border: 1rpx solid var(--line2); border-radius: 20rpx; padding: 22rpx; margin-bottom: 14rpx; }
.th-card-head { display: flex; align-items: center; justify-content: space-between; }
.th-code { font-size: 21rpx; color: #6C5B8E; font-weight: 600; }
.th-time { font-size: 19rpx; color: var(--ink3); }
.th-content { display: block; font-size: 26rpx; color: var(--ink); line-height: 1.75; margin-top: 12rpx; word-break: break-word; }
.th-card-foot { display: flex; align-items: center; justify-content: flex-end; gap: 16rpx; margin-top: 14rpx; }
.th-report { font-size: 19rpx; color: var(--ink3); }
.th-reason { flex: 1; font-size: 19rpx; color: #B0703A; }

.th-status { font-size: 19rpx; padding: 4rpx 12rpx; border-radius: 8rpx; }
.st-pending { background: #FFF4E2; color: #B07714; }
.st-approved { background: #E8F5EC; color: #3F8F6D; }
.st-rejected { background: #FBEBEC; color: #C0555F; }
.st-hidden { background: #EEEDF2; color: #6B625A; }

.th-more { text-align: center; padding: 22rpx; font-size: 22rpx; color: var(--ink3); }

.th-notice { padding: 22rpx; border-radius: 18rpx; background: var(--line2); margin-top: 8rpx; }
.th-notice-title { display: block; font-size: 21rpx; font-weight: 600; color: var(--ink2); }
.th-notice-text { display: block; font-size: 19rpx; color: var(--ink3); line-height: 1.7; margin-top: 8rpx; }
</style>
