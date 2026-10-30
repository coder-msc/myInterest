<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="手札" subtitle="你的人生，随手记一点" /><!-- #endif -->

    <!-- ===== 顶部问候 + 提醒入口 ===== -->
    <view class="hello">
      <view class="hello-main">
        <text class="hello-greet">{{ greeting }}</text>
        <text class="hello-date">{{ todayText }}</text>
      </view>
      <view class="bell" @click="goNotifications">
        <text class="bell-ic">🔔</text>
        <text v-if="home.unread" class="bell-dot">{{ home.unread > 99 ? '99+' : home.unread }}</text>
      </view>
    </view>

    <!-- ===== 月小结卡 ===== -->
    <view class="summary-card">
      <view class="sc-top">
        <text class="sc-month">{{ monthLabel }} · 小结</text>
        <text class="sc-count">{{ home.counts ? totalCount : 0 }} 条记录</text>
      </view>
      <view class="sc-nums">
        <view class="sc-cell">
          <text class="sc-label">本月支出</text>
          <text class="sc-value">¥{{ money(summary.expense) }}</text>
        </view>
        <view class="sc-cell">
          <text class="sc-label">本月收入</text>
          <text class="sc-value ok">¥{{ money(summary.income) }}</text>
        </view>
        <view class="sc-cell">
          <text class="sc-label">结余</text>
          <text class="sc-value" :class="summary.balance >= 0 ? 'ok' : 'danger'">¥{{ money(summary.balance) }}</text>
        </view>
      </view>
      <view v-if="summary.has_prev" class="sc-delta">
        <text :class="summary.expense_delta > 0 ? 'delta-up' : 'delta-down'">
          {{ summary.expense_delta > 0 ? '比上月多花' : '比上月少花' }} ¥{{ money(Math.abs(summary.expense_delta)) }}
        </text>
      </view>
      <view class="sc-actions">
        <view class="sc-btn primary" @click="openQuick('ledger')">💰 记一笔</view>
        <view class="sc-btn" @click="goLedger">看账本 ›</view>
      </view>
    </view>

    <!-- ===== 家庭资产总览（浓缩版，明细在值得记 · 盘点） ===== -->
    <view v-if="home.asset_card" class="asset-ov">
      <view class="ao-head">
        <text class="ao-label">家庭净值</text>
        <text class="ao-go" @click.stop="goAssets">明细 ›</text>
      </view>

      <view class="ao-body">
        <view class="ao-main">
          <text class="ao-value">¥{{ money(home.asset_card.net_worth) }}</text>
          <view class="ao-cols">
            <view class="ao-col">
              <text class="ao-col-label">总资产</text>
              <text class="ao-col-val">¥{{ shortMoney(home.asset_card.total_assets) }}</text>
            </view>
            <view class="ao-col">
              <text class="ao-col-label">总负债</text>
              <text class="ao-col-val debt">¥{{ shortMoney(home.asset_card.total_liabilities) }}</text>
            </view>
          </view>
        </view>

        <!-- 近 6 次盘点迷你柱 -->
        <view v-if="home.asset_card.trend.length > 1" class="ao-spark">
          <view v-for="t in home.asset_card.trend" :key="t.date" class="ao-bar-wrap">
            <view class="ao-bar" :style="{ height: assetBarH(t.net_worth) + 'rpx' }"></view>
          </view>
        </view>
      </view>

      <view class="ao-foot">
        <text class="ao-date">
          {{ home.asset_card.last_snapshot ? '上次盘点 ' + home.asset_card.last_snapshot.snapshot_date : '还没盘点过' }}
        </text>
        <text v-if="home.asset_card.delta !== null" :class="['ao-delta', home.asset_card.delta >= 0 ? 'up' : 'down']">
          {{ home.asset_card.delta >= 0 ? '比上次 +' : '比上次 ' }}¥{{ shortMoney(Math.abs(home.asset_card.delta)) }}
        </text>
      </view>

      <!-- 就地操作：盘点当前家底 / 去看投资持仓，不用先跳页 -->
      <view class="ao-actions">
        <view class="ao-btn" :class="taking ? 'loading' : ''" @click.stop="takeSnapshot">
          {{ taking ? '盘点中…' : '📸 现在盘点' }}
        </view>
        <view class="ao-btn ghost" @click.stop="goInvest">📈 投资持仓</view>
      </view>
    </view>

    <!-- ===== 日历：日子 / 行程 / 大事件 一览（原「发现 · 日历」移入手札） ===== -->
    <CalendarPanel ref="calRef" @changed="onCalendarChanged" />

    <!-- ===== 类型筛选 ===== -->
    <scroll-view class="filters" scroll-x>
      <view
        v-for="f in filters" :key="f.value"
        :class="['filter', filterType === f.value ? 'on' : '']"
        @click="pickFilter(f.value)"
      >
        {{ f.label }}
      </view>
    </scroll-view>

    <!-- ===== 时间线 ===== -->
    <view v-if="loading && !feed.length" class="loading-text">牛马拉磨中…</view>

    <view v-else-if="!feed.length" class="empty">
      <text class="empty-title">{{ isGuest ? '登录后，这里就是你的手札。' : (filterType ? '这类还没有记录。' : '这里比你的钱包还干净。') }}</text>
      <text class="empty-sub">{{ isGuest ? '记录只保存在你自己的账号里。' : (filterType ? '换个分类看看，或者去记一条。' : '去记第一笔吧。') }}</text>
      <view class="empty-btn" @click="isGuest ? goLogin() : openQuick('ledger')">{{ isGuest ? '登录 / 注册' : '开始记一笔' }}</view>
    </view>

    <view v-else class="feed">
      <view v-for="(e, i) in feed" :key="e.entry_type + '-' + e.ref_id" class="feed-row">
        <!-- 左侧日期刻度 -->
        <view class="rail">
          <text class="rail-day">{{ dayOf(e.occurred_at) }}</text>
          <text class="rail-mon">{{ monOf(e.occurred_at) }}</text>
          <view v-if="i !== feed.length - 1" class="rail-line"></view>
        </view>

        <!-- 右侧卡片 -->
        <view class="entry" @click="openEntry(e)">
          <view class="entry-top">
            <text :class="['chip', chipClass(e.entry_type)]">{{ e.type_label }}</text>
            <text class="entry-time">{{ agoText(e.occurred_at) }}</text>
          </view>
          <view class="entry-body">
            <view class="entry-main">
              <text class="entry-title">{{ e.title }}</text>
              <text v-if="e.summary" class="entry-sub">{{ e.summary }}</text>
              <text v-if="e.extra && e.extra.lunar_text" class="entry-lunar">农历 {{ e.extra.lunar_text }}</text>
            </view>
            <image v-if="e.cover_url" class="entry-cover" :src="mediaUrl(e.cover_url)" mode="aspectFill" />
            <view v-else-if="e.entry_type === 'ledger' && e.extra && e.extra.amount_text" class="entry-amount"
                  :class="e.extra.direction === 'income' ? 'ok' : ''">
              {{ e.extra.amount_text }}
            </view>
          </view>
          <view v-if="e.entry_type === 'trip' && e.extra && e.extra.photo_count" class="entry-foot">
            📷 {{ e.extra.photo_count }} 张照片
          </view>
        </view>
      </view>

      <view class="list-foot">
        <text v-if="loadingMore">牛马拉磨中…</text>
        <text v-else-if="hasMore" @click="loadMore">上拉或点击加载更多</text>
        <text v-else>到底了，日子还长。</text>
      </view>
    </view>

    <view style="height: 180rpx"></view>

    <!-- ===== 新增 FAB ===== -->
    <view class="fab" @click="quickVisible = true">
      <text class="fab-plus">＋</text>
    </view>

    <!-- 快捷新增弹层 -->
    <view v-if="quickVisible" class="sheet-mask" @click="quickVisible = false">
      <view class="sheet" @click.stop>
        <view class="sheet-head">
          <text class="sheet-title">记点什么</text>
          <text class="sheet-close" @click="quickVisible = false">✕</text>
        </view>
        <view class="quick-grid">
          <view v-for="q in quickItems" :key="q.key" class="quick-cell" @click="openQuick(q.key)">
            <text class="qc-emoji">{{ q.emoji }}</text>
            <text class="qc-label">{{ q.label }}</text>
            <text class="qc-sub">{{ q.sub }}</text>
          </view>
        </view>
      </view>
    </view>

    <view style="height: 40rpx"></view>
    <BackTop :scroll-top="pageScroll" :lift="130" />
    <!-- #ifdef H5 --><CustomTab current="/pages/journal/journal" /><!-- #endif -->
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow, onLoad, onPullDownRefresh, onReachBottom, onPageScroll } from '@dcloudio/uni-app'
import { apiJournalHome, apiJournalFeed, apiTakeAssetSnapshot } from '@/api'
import { mediaUrl } from '@/utils/config'
import { isLoggedIn, goLogin, requireLogin } from '@/utils/auth'
import { userStore } from '@/store/user'
import { watchMask } from '@/utils/tabbar'
import WebLayout from '@/components/WebLayout.vue'
import CustomTab from '@/components/CustomTab.vue'
import BackTop from '@/components/BackTop.vue'
import CalendarPanel from '@/components/CalendarPanel.vue'

const home = reactive({
  counts: {}, unread: 0, asset_card: null, month_footprints: 0,
  month_summary: { expense: 0, income: 0, balance: 0, has_prev: false, expense_delta: 0 },
})
const feed = ref([])
// 访客态：未登录也能翻看，空态文案改为引导登录（微信审核要求不强制登录）
const isGuest = ref(!isLoggedIn())
const pageScroll = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const hasMore = ref(false)
const page = ref(1)
const filterType = ref('')
const quickVisible = ref(false)
const taking = ref(false)
const calRef = ref(null)
// 打开「记点什么」弹层时收起小程序自定义 tabBar，否则弹层底部被 tabBar 压住
watchMask(() => quickVisible.value)

const filters = [
  { value: '', label: '全部' },
  { value: 'ledger', label: '💰 账本' },
  { value: 'trip', label: '📸 旅游' },
  { value: 'event', label: '🎉 大事件' },
  { value: 'countdown', label: '🎯 日子' },
  { value: 'asset_snapshot', label: '📊 盘点' },
]

const quickItems = [
  { key: 'ledger', emoji: '💰', label: '记一笔', sub: '花了还是赚了' },
  { key: 'trip', emoji: '📸', label: '记足迹', sub: '去哪玩了' },
  { key: 'event', emoji: '🎉', label: '记大事件', sub: '人生节点' },
  { key: 'countdown', emoji: '🎯', label: '记日子', sub: '别再忘了' },
  { key: 'assets', emoji: '🏦', label: '记资产', sub: '家底盘点' },
]

const summary = computed(() => home.month_summary || {})
const totalCount = computed(() => Object.values(home.counts || {}).reduce((a, b) => a + b, 0))
const monthLabel = computed(() => {
  const d = new Date()
  return `${d.getMonth() + 1} 月`
})

const greeting = computed(() => {
  const h = new Date().getHours()
  const name = userStore.user?.nickname || userStore.user?.username || '牛马'
  if (h < 6) return `还没睡啊，${name}`
  if (h < 11) return `早，${name}`
  if (h < 14) return `中午好，${name}`
  if (h < 18) return `下午好，${name}`
  return `今天也辛苦了，${name}`
})

const todayText = computed(() => {
  const d = new Date()
  const w = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日 · 周${w}`
})

function money(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
/** 总资产/总负债用万元收短，避免一行塞两串长数字把卡撑爆 */
function shortMoney(n) {
  const v = Number(n || 0)
  if (Math.abs(v) >= 10000) return (v / 10000).toFixed(1) + ' 万'
  return money(v)
}
/** 迷你趋势柱：以近几次盘点的最大值取满格，避免金额小时柱子看不见 */
function assetBarH(v) {
  const list = home.asset_card?.trend || []
  const max = Math.max(1, ...list.map(t => t.net_worth))
  return Math.max(8, (Number(v || 0) / max) * 72)
}
function dayOf(s) { return s ? String(s).slice(8, 10) : '' }
function monOf(s) { return s ? String(s).slice(5, 7) + '月' : '' }
function chipClass(t) {
  return { ledger: 'chip-ledger', trip: 'chip-trip', event: 'chip-event',
    countdown: 'chip-countdown', asset_snapshot: 'chip-asset' }[t] || ''
}
function agoText(s) {
  if (!s) return ''
  const d = new Date(String(s).slice(0, 10) + 'T00:00:00')
  const diff = Math.floor((Date.now() - d.getTime()) / 86400000)
  if (diff <= 0) return '今天'
  if (diff === 1) return '昨天'
  if (diff < 7) return `${diff} 天前`
  return String(s).slice(0, 10)
}

async function loadHome() {
  try {
    const data = await apiJournalHome()
    Object.assign(home, data)
    feed.value = data.feed?.items || []
    hasMore.value = !!data.feed?.has_more
    page.value = 1
  } catch (e) { /* toast 已统一 */ }
}

async function loadFeed(reset = false) {
  loading.value = true
  try {
    const data = await apiJournalFeed({
      page: reset ? 1 : page.value,
      page_size: 20,
      ...(filterType.value ? { entry_type: filterType.value } : {}),
    })
    const items = data.items || []
    feed.value = reset ? items : feed.value.concat(items)
    hasMore.value = !!data.has_more
    page.value = (data.page || 1) + 1
  } finally {
    loading.value = false
  }
}

function pickFilter(v) {
  filterType.value = v
  page.value = 1
  loadFeed(true)
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  try {
    const data = await apiJournalFeed({
      page: page.value, page_size: 20,
      ...(filterType.value ? { entry_type: filterType.value } : {}),
    })
    feed.value = feed.value.concat(data.items || [])
    hasMore.value = !!data.has_more
    page.value = (data.page || page.value) + 1
  } finally {
    loadingMore.value = false
  }
}

function openQuick(key) {
  // 新增类入口先确认登录，避免填完表单提交时才被拦
  if (!requireLogin()) return
  quickVisible.value = false
  if (key === 'ledger') return uni.switchTab({ url: '/pages/ledger/ledger' })
  if (key === 'trip') return goWorth('trip')
  if (key === 'event') return goWorth('event')
  if (key === 'countdown') return goWorth('countdown')
  if (key === 'assets') return uni.navigateTo({ url: '/pages/assets/assets' })
}

function openEntry(e) {
  if (e.entry_type === 'ledger') return uni.switchTab({ url: '/pages/ledger/ledger' })
  if (e.entry_type === 'trip') return uni.navigateTo({ url: `/pages/trips/detail?id=${e.ref_id}` })
  if (e.entry_type === 'event') return goWorth('event')
  if (e.entry_type === 'countdown') return goWorth('countdown')
  if (e.entry_type === 'asset_snapshot') return goWorth('assets')
}

/** 值得记是 tab 页，switchTab 不能带参数，用 storage 传递要打开的分段 */
function goWorth(key) {
  uni.setStorageSync('worth_tab', key)
  uni.switchTab({ url: '/pages/worth/worth' })
}
function goLedger() { uni.switchTab({ url: '/pages/ledger/ledger' }) }
function goAssets() { goWorth('assets') }
function goInvest() { uni.navigateTo({ url: '/pages/holdings/holdings' }) }
function goNotifications() { uni.navigateTo({ url: '/pages/notifications/notifications' }) }

/** 首页就地盘点：固化当日净值后重拉首页，净值卡与迷你趋势一起更新 */
async function takeSnapshot() {
  if (taking.value) return
  if (!requireLogin('登录后才能记录今天的资产盘点')) return
  taking.value = true
  try {
    await apiTakeAssetSnapshot()
    uni.showToast({ title: '盘点完成，净值已记录', icon: 'none' })
    await loadHome()
  } catch (e) { /* toast 已统一 */ } finally {
    taking.value = false
  }
}

/** 日历里改了日子，首页置顶条与时间线要跟着变 */
function onCalendarChanged() {
  loadHome()
}

onLoad(() => {})
onShow(() => {
  isGuest.value = !isLoggedIn()
  loadHome()
  loadFeed(true)
  // 从值得记改完日子回来时刷新日历，避免还是旧数据
  calRef.value?.reload()
})
onPullDownRefresh(async () => {
  // 兜底：任何请求卡死也要在 8 秒内把小程序原生转圈收掉
  const guard = setTimeout(() => uni.stopPullDownRefresh(), 8000)
  try {
    await Promise.all([loadHome(), loadFeed(true), calRef.value?.reload()])
  } finally {
    clearTimeout(guard)
    uni.stopPullDownRefresh()
  }
})
onReachBottom(loadMore)
onPageScroll((e) => { pageScroll.value = e.scrollTop })
</script>

<style scoped>
.page { padding: 24rpx; padding-bottom: calc(120rpx + env(safe-area-inset-bottom)); }

/* 问候 */
.hello { display: flex; align-items: center; justify-content: space-between; padding: 8rpx 4rpx 24rpx; }
.hello-main { display: flex; flex-direction: column; gap: 6rpx; }
.hello-greet { font-size: 36rpx; font-weight: 700; color: var(--ink); }
.hello-date { font-size: 22rpx; color: var(--ink3); }
.bell { position: relative; width: 72rpx; height: 72rpx; border-radius: 50%; background: #fff;
  border: 1rpx solid var(--line2); display: flex; align-items: center; justify-content: center; }
.bell-ic { font-size: 32rpx; }
.bell-dot {
  position: absolute; top: -6rpx; right: -6rpx; min-width: 30rpx; height: 30rpx;
  padding: 0 6rpx; border-radius: 9999rpx; background: var(--danger); color: #fff;
  font-size: 18rpx; line-height: 30rpx; text-align: center;
}

/* 月小结卡 */
.summary-card {
  background: linear-gradient(135deg, #D97742 0%, #C96736 100%);
  border-radius: 28rpx; padding: 30rpx 30rpx 26rpx; color: #fff;
  box-shadow: 0 10rpx 26rpx rgba(185, 92, 46, 0.24); margin-bottom: 24rpx;
}
.sc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20rpx; }
.sc-month { font-size: 24rpx; opacity: 0.9; }
.sc-count { font-size: 22rpx; opacity: 0.75; }
.sc-nums { display: flex; }
.sc-cell { flex: 1; display: flex; flex-direction: column; gap: 8rpx; }
.sc-label { font-size: 21rpx; opacity: 0.8; }
.sc-value { font-size: 34rpx; font-weight: 700; letter-spacing: 0.5rpx; }
.sc-value.ok { color: #E8F7EF; }
.sc-value.danger { color: #FFE3E6; }
.sc-delta { margin-top: 16rpx; font-size: 22rpx; opacity: 0.92; }
.delta-up { color: #FFE9D8; }
.delta-down { color: #E8F7EF; }
.sc-actions { display: flex; gap: 16rpx; margin-top: 24rpx; }
.sc-btn {
  flex: 1; height: 68rpx; line-height: 68rpx; text-align: center;
  border-radius: 9999rpx; font-size: 26rpx;
  background: rgba(255, 255, 255, 0.18); color: #fff;
}
.sc-btn.primary { background: #fff; color: var(--brand-d); font-weight: 600; flex: 1.2; }

/* 筛选 */
.filters { white-space: nowrap; margin-bottom: 20rpx; }
.filter {
  display: inline-block; padding: 12rpx 24rpx; margin-right: 14rpx;
  background: #fff; border: 1rpx solid var(--line2); border-radius: 9999rpx;
  font-size: 24rpx; color: var(--ink2);
}
.filter.on { background: var(--brand-sel); border-color: var(--brand-bd); color: var(--brand-d); font-weight: 600; }

/* 时间线 */
.feed { display: flex; flex-direction: column; }
.feed-row { display: flex; gap: 18rpx; }
.rail { width: 66rpx; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; padding-top: 8rpx; }
.rail-day { font-size: 30rpx; font-weight: 700; color: var(--ink); line-height: 1.1; }
.rail-mon { font-size: 19rpx; color: var(--ink3); }
.rail-line { flex: 1; width: 2rpx; background: var(--line); margin: 10rpx 0 0; }
.entry {
  flex: 1; background: #fff; border-radius: 22rpx; padding: 22rpx 24rpx;
  border: 1rpx solid var(--line2); margin-bottom: 18rpx;
}
.entry-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12rpx; }
.entry-time { font-size: 20rpx; color: var(--ink3); }
.entry-body { display: flex; align-items: center; gap: 16rpx; }
.entry-main { flex: 1; display: flex; flex-direction: column; gap: 6rpx; min-width: 0; }
.entry-title {
  font-size: 28rpx; font-weight: 600; color: var(--ink); line-height: 1.45;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.entry-sub { font-size: 22rpx; color: var(--ink3); line-height: 1.5; }
.entry-lunar { font-size: 20rpx; color: var(--warn); }
.entry-cover { width: 108rpx; height: 108rpx; border-radius: 16rpx; flex-shrink: 0; background: var(--line2); }
.entry-amount { font-size: 30rpx; font-weight: 700; color: var(--danger); flex-shrink: 0; }
.entry-amount.ok { color: var(--ok); }
.entry-foot { margin-top: 14rpx; font-size: 20rpx; color: var(--ink3); }

.list-foot { text-align: center; color: var(--ink3); font-size: 22rpx; padding: 20rpx 0 30rpx; }

/* 空态按钮 */
.empty-btn {
  display: inline-block; margin-top: 28rpx; padding: 16rpx 40rpx;
  background: var(--brand); color: #fff; border-radius: 9999rpx; font-size: 26rpx;
}

/* 资产总览 · 克制专业蓝（与月小结的暖橙区分） */
.asset-ov {
  background: linear-gradient(135deg, #5B7FA6 0%, #456B92 100%);
  border-radius: 26rpx; padding: 26rpx 28rpx 22rpx; color: #fff;
  margin-bottom: 24rpx; box-shadow: 0 8rpx 20rpx rgba(69, 107, 146, 0.2);
}
.ao-head { display: flex; align-items: center; justify-content: space-between; }
.ao-label { font-size: 22rpx; opacity: 0.85; }
.ao-go { font-size: 21rpx; opacity: 0.9; }
.ao-body { display: flex; align-items: flex-end; justify-content: space-between; gap: 20rpx; margin-top: 8rpx; }
.ao-main { flex: 1; min-width: 0; }
.ao-value { display: block; font-size: 46rpx; font-weight: 700; letter-spacing: 0.5rpx; line-height: 1.25; }
.ao-cols { display: flex; gap: 36rpx; margin-top: 12rpx; }
.ao-col { display: flex; flex-direction: column; gap: 2rpx; }
.ao-col-label { font-size: 19rpx; opacity: 0.75; }
.ao-col-val { font-size: 24rpx; font-weight: 600; }
.ao-col-val.debt { color: #FFE3E6; }

/* 迷你趋势柱：只做形状参考，不标数值 */
.ao-spark { display: flex; align-items: flex-end; gap: 7rpx; height: 72rpx; flex-shrink: 0; }
.ao-bar-wrap { display: flex; align-items: flex-end; height: 100%; }
.ao-bar { width: 12rpx; border-radius: 5rpx 5rpx 0 0; background: rgba(255, 255, 255, 0.62); }

.ao-foot {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 18rpx; padding-top: 14rpx;
  border-top: 1rpx solid rgba(255, 255, 255, 0.2);
}
.ao-date { font-size: 19rpx; opacity: 0.78; }
.ao-delta { font-size: 19rpx; font-weight: 600; }
.ao-delta.up { color: #E8F7EF; }
.ao-delta.down { color: #FFE3E6; }

/* 卡内操作按钮：与盘点页同款，就地就能盘点/看持仓 */
.ao-actions { display: flex; gap: 16rpx; margin-top: 20rpx; }
.ao-btn {
  flex: 1; height: 68rpx; line-height: 68rpx; text-align: center;
  background: #fff; color: #456B92; border-radius: 9999rpx;
  font-size: 24rpx; font-weight: 600;
}
.ao-btn.ghost { background: rgba(255, 255, 255, 0.18); color: #fff; font-weight: 400; }
.ao-btn.loading { opacity: 0.7; }

/* FAB */
.fab {
  position: fixed; right: 32rpx; bottom: calc(140rpx + env(safe-area-inset-bottom));
  width: 108rpx; height: 108rpx; border-radius: 50%;
  background: linear-gradient(135deg, #D97742, #B85C2E);
  color: #fff; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 10rpx 24rpx rgba(185, 92, 46, 0.36); z-index: 900;
}
.fab-plus { font-size: 54rpx; line-height: 1; margin-top: -4rpx; }

/* 快捷新增 */
/* 小程序 rpx 取整会让「两列刚好 100%」溢出换行，故留 3% 余量并交给 space-between 分配间隙 */
.quick-grid { display: flex; flex-wrap: wrap; justify-content: space-between; row-gap: 18rpx; }
.quick-cell {
  width: 48.5%; box-sizing: border-box;
  background: var(--bg); border: 1rpx solid var(--line2); border-radius: 20rpx;
  padding: 26rpx 22rpx; display: flex; flex-direction: column; gap: 6rpx;
}
.qc-emoji { font-size: 40rpx; }
.qc-label { font-size: 28rpx; font-weight: 600; color: var(--ink); }
.qc-sub { font-size: 21rpx; color: var(--ink3); }

@media (min-width: 768px) {
  .page { max-width: 720px; margin: 0 auto; }
  .fab { right: calc(50% - 360px + 24px); }
}
</style>
