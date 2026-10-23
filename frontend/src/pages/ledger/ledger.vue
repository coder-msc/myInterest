<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="账本" subtitle="钱花在哪了，心里有点数" /><!-- #endif -->

    <!-- 月份切换 -->
    <view class="month-nav">
      <text class="mn-arrow" @click="shiftMonth(-1)">‹</text>
      <text class="mn-label">{{ monthLabel }}</text>
      <text class="mn-arrow" :class="isCurrentMonth ? 'disabled' : ''" @click="shiftMonth(1)">›</text>
      <view class="mn-add" @click="openSheet()">＋ 记一笔</view>
    </view>

    <!-- segment -->
    <view class="segment">
      <view :class="['seg-item', tab === 'list' ? 'on' : '']" @click="tab = 'list'">
        <text>📋</text><text>流水</text>
      </view>
      <view :class="['seg-item', tab === 'stats' ? 'on' : '']" @click="tab = 'stats'">
        <text>📊</text><text>统计</text>
      </view>
    </view>

    <!-- ===== 月汇总 ===== -->
    <view class="sum-card">
      <view class="sc-main">
        <text class="sc-label">本月支出<text v-if="summary.count" class="sc-count"> · {{ summary.count }} 笔</text></text>
        <text class="sc-expense">¥{{ money(summary.expense) }}</text>
        <text v-if="summary.has_prev" class="sc-delta">
          {{ summary.expense_delta > 0 ? '比上月多花' : '比上月少花' }}
          ¥{{ money(Math.abs(summary.expense_delta)) }}
        </text>
      </view>
      <view class="sc-side">
        <view class="sc-row"><text class="scr-label">收入</text><text class="scr-val ok">¥{{ money(summary.income) }}</text></view>
        <view class="sc-row"><text class="scr-label">结余</text><text class="scr-val" :class="summary.balance >= 0 ? 'ok' : 'danger'">¥{{ money(summary.balance) }}</text></view>
      </view>
    </view>

    <!-- 分类构成条 -->
    <view v-if="tab === 'list' && catStats.length" class="bar-card">
      <view class="comp-bar">
        <view v-for="(c, i) in catStats" :key="c.name" class="comp-seg"
              :style="{ width: c.percent + '%', background: barColors[i % barColors.length] }"></view>
      </view>
      <view class="comp-legend">
        <view v-for="(c, i) in catStats.slice(0, 4)" :key="c.name" class="legend-item">
          <view class="legend-dot" :style="{ background: barColors[i % barColors.length] }"></view>
          <text class="legend-name">{{ c.emoji }} {{ c.name }}</text>
          <text class="legend-pct">{{ c.percent }}%</text>
        </view>
      </view>
    </view>

    <!-- ===== 流水 ===== -->
    <block v-if="tab === 'list'">
      <view v-if="loading && !days.length" class="loading-text">牛马拉磨中…</view>

      <view v-else-if="!days.length" class="empty">
        <text class="empty-title">{{ monthLabel }}还没记过账。</text>
        <text class="empty-sub">你这个月还没花过钱 —— 除非你是在装。</text>
        <view class="empty-btn" @click="openSheet()">记第一笔</view>
      </view>

      <view v-else class="day-list">
        <view v-for="d in days" :key="d.date" class="day-block">
          <view class="day-head">
            <text class="dh-date">{{ dayLabel(d.date) }}</text>
            <view class="dh-sum-wrap">
              <text v-if="dayExpense(d) > 0" class="dh-sum">支出 ¥{{ money(dayExpense(d)) }}</text>
              <text v-if="dayIncome(d) > 0" class="dh-sum income">收入 ¥{{ money(dayIncome(d)) }}</text>
            </view>
          </view>
          <view class="rec-list">
            <view v-for="r in d.items" :key="r.id" class="rec"
                  @click="openSheet(r)" @longpress="confirmDelete(r)">
              <text class="rec-emoji">{{ catEmoji(r.category) }}</text>
              <view class="rec-main">
                <text class="rec-title">{{ r.note || r.category }}</text>
                <text class="rec-sub">{{ r.category }}{{ r.account ? ' · ' + r.account : '' }}</text>
              </view>
              <text :class="['rec-amount', r.direction === 'income' ? 'ok' : '']">
                {{ r.direction === 'income' ? '+' : '-' }}{{ money(r.amount) }}
              </text>
            </view>
          </view>
        </view>
      </view>

      <view v-if="truncated" class="list-note">本月记录超过 500 笔，这里只显示最近 500 笔。</view>
    </block>

    <!-- ===== 统计 ===== -->
    <block v-else>
      <view v-if="!catStats.length" class="empty">
        <text class="empty-title">这个月还没有支出。</text>
        <text class="empty-sub">没有数据也是一种数据。</text>
      </view>
      <view v-else class="card">
        <view class="section-title"><text>分类构成</text><text class="section-extra">共 ¥{{ money(summary.expense) }}</text></view>
        <view v-for="c in catStats" :key="c.name" class="stat-row">
          <text class="sr-emoji">{{ c.emoji }}</text>
          <text class="sr-name">{{ c.name }}</text>
          <view class="sr-bar"><view class="sr-fill" :style="{ width: c.percent + '%' }"></view></view>
          <text class="sr-pct">{{ c.percent }}%</text>
          <text class="sr-amount">¥{{ money(c.amount) }}</text>
        </view>
      </view>

      <view class="card">
        <view class="section-title"><text>近 6 个月</text><text class="section-extra">支出趋势</text></view>
        <view class="trend">
          <view v-for="t in trend" :key="t.month" class="trend-col">
            <view class="trend-bar-wrap">
              <view class="trend-bar" :style="{ height: barH(t.expense) + 'rpx' }"></view>
            </view>
            <text class="trend-label">{{ t.month.slice(5) }}月</text>
            <text class="trend-val">{{ t.expense ? shortMoney(t.expense) : '0' }}</text>
          </view>
        </view>
      </view>
    </block>

    <view style="height: 160rpx"></view>

    <!-- ===== 记一笔弹层 ===== -->
    <view v-if="sheetVisible" class="sheet-mask" @click="sheetVisible = false">
      <view class="sheet" @click.stop>
        <view class="sheet-head">
          <text class="sheet-title">{{ editingId ? '改一笔' : '记一笔' }}</text>
          <text class="sheet-close" @click="sheetVisible = false">✕</text>
        </view>

        <!-- 收/支 -->
        <view class="dir-tabs">
          <view :class="['dir', form.direction === 'expense' ? 'on-expense' : '']" @click="form.direction = 'expense'">支出</view>
          <view :class="['dir', form.direction === 'income' ? 'on-income' : '']" @click="form.direction = 'income'">收入</view>
        </view>

        <!-- 金额 -->
        <view class="amount-row">
          <text class="amount-sym">¥</text>
          <input class="amount-input" type="digit" v-model="form.amount" placeholder="0.00" focus @confirm="save" />
        </view>

        <!-- 分类 -->
        <view class="cat-grid">
          <view v-for="c in categories" :key="c.id"
                :class="['cat-cell', form.category === c.name ? 'on' : '']"
                @click="form.category = c.name">
            <text class="cc-emoji">{{ c.emoji }}</text>
            <text class="cc-name">{{ c.name }}</text>
          </view>
          <view class="cat-cell add" :class="addingCat ? 'on' : ''" @click="toggleAddCategory">
            <text class="cc-emoji">{{ addingCat ? '×' : '＋' }}</text>
            <text class="cc-name">{{ addingCat ? '收起' : '新增' }}</text>
          </view>
        </view>

        <!-- 新增分类：用内嵌面板代替 showModal，避免和弹层抢层级、也方便选图标 -->
        <view v-if="addingCat" class="cat-add">
          <scroll-view class="emoji-row" scroll-x :show-scrollbar="false">
            <view class="emoji-inner">
              <text v-for="e in emojiChoices" :key="e"
                    :class="['emoji-opt', newCatEmoji === e ? 'on' : '']"
                    @click="newCatEmoji = e">{{ e }}</text>
            </view>
          </scroll-view>
          <view class="ca-row">
            <input class="ca-input" v-model="newCatName" maxlength="10"
                   placeholder="分类名，最多 10 字" confirm-type="done" @confirm="confirmAddCategory" />
            <view :class="['ca-ok', addingCatBusy ? 'loading' : '']" @click="confirmAddCategory">
              {{ addingCatBusy ? '添加中' : '添加' }}
            </view>
          </view>
        </view>

        <!-- 日期 / 备注 / 账户 -->
        <view class="field">
          <text class="f-label">日期</text>
          <picker mode="date" :value="form.occurred_on" :end="today" @change="onDate">
            <view class="f-input">{{ form.occurred_on }}</view>
          </picker>
        </view>
        <view class="field">
          <text class="f-label">备注</text>
          <input class="f-input" v-model="form.note" maxlength="50" placeholder="写点什么（可不填）" />
        </view>
        <view class="field">
          <text class="f-label">账户</text>
          <input class="f-input" v-model="form.account" maxlength="20" placeholder="现金 / 工资卡（可不填）" />
        </view>

        <button class="btn-primary submit" :loading="saving" @click="save">{{ editingId ? '保存修改' : '记下了' }}</button>
        <view v-if="editingId" class="del-link" @click="removeCurrent">删除这笔</view>
      </view>
    </view>

    <view style="height: 40rpx"></view>
    <BackTop :scroll-top="pageScroll" />
    <!-- #ifdef H5 --><CustomTab current="/pages/ledger/ledger" /><!-- #endif -->
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow, onPullDownRefresh, onPageScroll } from '@dcloudio/uni-app'
import {
  apiLedger, apiLedgerStats, apiCreateLedger, apiUpdateLedger,
  apiDeleteLedger, apiAddLedgerCategory,
} from '@/api'
import WebLayout from '@/components/WebLayout.vue'
import CustomTab from '@/components/CustomTab.vue'
import BackTop from '@/components/BackTop.vue'

const tab = ref('list')
const pageScroll = ref(0)
const loading = ref(false)
const saving = ref(false)
const sheetVisible = ref(false)
const editingId = ref(null)
const reqSeq = ref(0)
const truncated = ref(false)

const month = ref(currentMonth())
const summary = reactive({ expense: 0, income: 0, balance: 0, count: 0, has_prev: false, expense_delta: 0 })
const days = ref([])
const categories = ref([])
const catStats = ref([])
const trend = ref([])

const barColors = ['#D97742', '#E8A33D', '#3F8F6D', '#5B7FA6', '#C0555F', '#B08BC0', '#C9A227']

/** 本地日期：不用 toISOString，东八区凌晨会算成前一天 */
function localDate(offset = 0) {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

/** 常驻 tab 页跨零点后仍要能选到「今天」 */
const today = ref(localDate())
const form = reactive({
  direction: 'expense', amount: '', category: '其他', account: '',
  occurred_on: localDate(), note: '',
})

/** 新增分类：内嵌面板状态（不用 showModal：H5 弹窗 z-index 低于记一笔弹层，会藏在后面） */
const addingCat = ref(false)
const addingCatBusy = ref(false)
const newCatName = ref('')
const newCatEmoji = ref('📦')
const emojiChoices = ['📦', '🍜', '🚇', '🏠', '🛒', '🎁', '🎮', '💊', '📚', '🐱', '✈️', '🎬']

const monthLabel = computed(() => {
  const [y, m] = month.value.split('-')
  return `${y} 年 ${Number(m)} 月`
})
const isCurrentMonth = computed(() => month.value === currentMonth())
const maxTrend = computed(() => Math.max(1, ...trend.value.map(t => t.expense)))

function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}
function money(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
/** 图表里用短数字：1.2万，避免 6 列挤在一起 */
function shortMoney(n) {
  const v = Number(n || 0)
  if (v < 10000) return money(v)
  const w = v / 10000
  return w.toFixed(w >= 100 ? 0 : 1).replace(/\.0$/, '') + '万'
}
function catEmoji(name) {
  const c = categories.value.find(x => x.name === name)
  return c ? c.emoji : '📦'
}
function dayLabel(d) {
  if (d === localDate()) return '今天 · ' + d.slice(5)
  if (d === localDate(-1)) return '昨天 · ' + d.slice(5)
  return d.slice(5).replace('-', '月') + '日'
}
function dayExpense(d) {
  return d.items.filter(r => r.direction === 'expense').reduce((a, r) => a + r.amount, 0)
}
function dayIncome(d) {
  return d.items.filter(r => r.direction === 'income').reduce((a, r) => a + r.amount, 0)
}
function barH(v) { return Math.max(4, (v / maxTrend.value) * 180) }

function shiftMonth(delta) {
  if (delta > 0 && isCurrentMonth.value) return
  const [y, m] = month.value.split('-').map(Number)
  const idx = y * 12 + (m - 1) + delta
  month.value = `${Math.floor(idx / 12)}-${String(idx % 12 + 1).padStart(2, '0')}`
  load()
}

/** 流水与统计一起取：分类构成条不再依赖先点一次「统计」 */
async function load() {
  const seq = ++reqSeq.value
  const m = month.value
  loading.value = true
  try {
    const [data, stats] = await Promise.all([
      apiLedger({ month: m, limit: 500 }),
      apiLedgerStats({ month: m }),
    ])
    // 连点月份时丢弃过期响应，避免旧月份覆盖新月份
    if (seq !== reqSeq.value) return
    Object.assign(summary, stats.summary || data.summary || {})
    days.value = data.days || []
    truncated.value = (data.items || []).length >= 500
    categories.value = data.categories || []
    catStats.value = stats.categories || []
    trend.value = stats.trend || []
    // 只在没在编辑时同步「上次使用的分类」，避免刷新打断正在填的表单
    if (data.last_category && !sheetVisible.value && !editingId.value) form.category = data.last_category.name
  } finally {
    if (seq === reqSeq.value) loading.value = false
  }
}

function openSheet(r) {
  // 每次打开都收起「新增分类」面板，避免残留上次输入
  addingCat.value = false
  newCatName.value = ''
  if (r) {
    editingId.value = r.id
    form.direction = r.direction
    form.amount = String(r.amount)
    form.category = r.category
    form.account = r.account || ''
    form.occurred_on = r.occurred_on
    form.note = r.note || ''
    sheetVisible.value = true
    return
  }
  editingId.value = null
  form.direction = 'expense'
  form.amount = ''
  form.account = ''
  form.occurred_on = today.value
  form.note = ''
  const last = categories.value.find(c => c.name === form.category)
  if (!last) form.category = categories.value[0]?.name || '其他'
  sheetVisible.value = true
}

function onDate(e) { form.occurred_on = e.detail.value }

async function save() {
  if (saving.value) return
  const amount = Number(form.amount)
  if (!Number.isFinite(amount) || amount <= 0) {
    return uni.showToast({ title: '金额得大于 0', icon: 'none' })
  }
  if (!form.category) {
    return uni.showToast({ title: '选个分类吧', icon: 'none' })
  }
  saving.value = true
  const payload = {
    direction: form.direction, amount, category: form.category,
    account: form.account || null, occurred_on: form.occurred_on,
    note: form.note || null,
  }
  try {
    if (editingId.value) await apiUpdateLedger(editingId.value, payload)
    else await apiCreateLedger(payload)
    sheetVisible.value = false
    uni.showToast({ title: editingId.value ? '改好了' : '又活过一天 +1', icon: 'none' })
    await load()
  } catch (e) { /* toast 已统一 */ } finally {
    saving.value = false
  }
}

function confirmDelete(r) {
  uni.showModal({
    title: '真的删？',
    content: '它不会记仇。',
    confirmText: '删掉',
    confirmColor: '#C0555F',
    success: async (res) => {
      if (!res.confirm) return
      await apiDeleteLedger(r.id)
      load()
    },
  })
}

function removeCurrent() {
  if (!editingId.value) return
  const id = editingId.value
  uni.showModal({
    title: '真的删？',
    content: '它不会记仇。',
    confirmText: '删掉',
    confirmColor: '#C0555F',
    success: async (res) => {
      if (!res.confirm) return
      await apiDeleteLedger(id)
      sheetVisible.value = false
      load()
    },
  })
}

function toggleAddCategory() {
  addingCat.value = !addingCat.value
  if (addingCat.value) {
    newCatName.value = ''
    newCatEmoji.value = '📦'
  }
}

async function confirmAddCategory() {
  if (addingCatBusy.value) return
  const name = newCatName.value.trim()
  if (!name) return uni.showToast({ title: '给分类起个名', icon: 'none' })
  addingCatBusy.value = true
  try {
    const c = await apiAddLedgerCategory(name, newCatEmoji.value)
    categories.value.push(c)
    form.category = c.name
    addingCat.value = false
    newCatName.value = ''
    uni.showToast({ title: '分类加好了', icon: 'none' })
  } catch (e) { /* toast 已统一 */ } finally {
    addingCatBusy.value = false
  }
}

onPageScroll((e) => { pageScroll.value = e.scrollTop })
onShow(() => {
  // 常驻 tab 页：跨零点后把「今天」和表单默认日期推到新的一天
  const d = localDate()
  if (d !== today.value) {
    today.value = d
    if (!sheetVisible.value) form.occurred_on = d
  }
  load()
})
onPullDownRefresh(async () => {
  // 兜底：任何请求卡死也要在 8 秒内把小程序原生转圈收掉
  const guard = setTimeout(() => uni.stopPullDownRefresh(), 8000)
  try {
    await load()
  } finally {
    clearTimeout(guard)
    uni.stopPullDownRefresh()
  }
})
</script>

<style scoped>
.page { padding: 24rpx; }

.month-nav { display: flex; align-items: center; gap: 12rpx; margin-bottom: 20rpx; }
.mn-arrow { font-size: 40rpx; color: var(--ink2); padding: 0 10rpx; line-height: 60rpx; }
.mn-arrow.disabled { color: #D9CFC4; }
.mn-label { font-size: 30rpx; font-weight: 700; color: var(--ink); }
.mn-add {
  margin-left: auto; padding: 12rpx 26rpx; border-radius: 9999rpx;
  background: var(--brand); color: #fff; font-size: 24rpx;
  box-shadow: 0 6rpx 14rpx rgba(185, 92, 46, 0.22);
}
.mn-add:active { opacity: 0.86; }

/* 汇总 */
.sum-card {
  display: flex; background: #fff; border: 1rpx solid var(--line2);
  border-radius: 24rpx; padding: 30rpx; margin-bottom: 20rpx;
}
.sc-main { flex: 1.3; display: flex; flex-direction: column; gap: 6rpx; }
.sc-label { font-size: 22rpx; color: var(--ink3); }
.sc-count { color: var(--ink3); }
.sc-expense { font-size: 52rpx; font-weight: 700; color: var(--ink); letter-spacing: 0.5rpx;
  font-variant-numeric: tabular-nums; }
.sc-delta { font-size: 22rpx; color: var(--warn); }
.sc-side { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 18rpx;
  border-left: 1rpx dashed var(--line); padding-left: 24rpx; }
.sc-row { display: flex; align-items: center; justify-content: space-between; }
.scr-label { font-size: 22rpx; color: var(--ink3); }
.scr-val { font-size: 26rpx; font-weight: 600; color: var(--ink); }
.scr-val.ok { color: var(--ok); }
.scr-val.danger { color: var(--danger); }

/* 构成条 */
.bar-card { background: #fff; border: 1rpx solid var(--line2); border-radius: 24rpx; padding: 24rpx; margin-bottom: 20rpx; }
.comp-bar { display: flex; height: 18rpx; border-radius: 9999rpx; overflow: hidden; background: var(--line2); }
.comp-seg { height: 100%; }
.comp-legend { display: flex; flex-wrap: wrap; gap: 8rpx 24rpx; margin-top: 18rpx; }
.legend-item { display: flex; align-items: center; gap: 8rpx; }
.legend-dot { width: 14rpx; height: 14rpx; border-radius: 50%; }
.legend-name { font-size: 21rpx; color: var(--ink2); }
.legend-pct { font-size: 20rpx; color: var(--ink3); }

/* 流水 */
.day-block { margin-bottom: 26rpx; }
.day-head { display: flex; align-items: center; justify-content: space-between; padding: 0 6rpx 12rpx; gap: 12rpx; }
.dh-date { font-size: 24rpx; font-weight: 600; color: var(--ink2); }
.dh-sum-wrap { display: flex; align-items: center; gap: 14rpx; flex-shrink: 0; }
.dh-sum { font-size: 21rpx; color: var(--ink3); font-variant-numeric: tabular-nums; }
.dh-sum.income { color: var(--ok); }
.rec-list { background: #fff; border: 1rpx solid var(--line2); border-radius: 22rpx; overflow: hidden; }
.rec { display: flex; align-items: center; gap: 18rpx; padding: 22rpx 24rpx; border-bottom: 1rpx solid var(--line2); }
.rec:active { background: var(--bg); }
.rec:last-child { border-bottom: none; }
.rec-emoji { font-size: 34rpx; width: 48rpx; text-align: center; }
.rec-main { flex: 1; display: flex; flex-direction: column; gap: 4rpx; min-width: 0; }
.rec-title { font-size: 27rpx; color: var(--ink); }
.rec-sub { font-size: 20rpx; color: var(--ink3); }
.rec-amount { font-size: 28rpx; font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums; }
.rec-amount.ok { color: var(--ok); }

.list-note {
  text-align: center; font-size: 20rpx; color: var(--ink3);
  padding: 20rpx 0 0;
}

.empty-btn {
  display: inline-block; margin-top: 28rpx; padding: 16rpx 40rpx;
  background: var(--brand); color: #fff; border-radius: 9999rpx; font-size: 26rpx;
}

/* 统计 */
.stat-row { display: flex; align-items: center; gap: 12rpx; padding: 14rpx 0; }
.sr-emoji { font-size: 28rpx; }
.sr-name { width: 110rpx; font-size: 24rpx; color: var(--ink2); }
.sr-bar { flex: 1; height: 12rpx; background: var(--line2); border-radius: 9999rpx; overflow: hidden; }
.sr-fill { height: 100%; background: var(--brand); border-radius: 9999rpx; }
.sr-pct { width: 76rpx; text-align: right; font-size: 20rpx; color: var(--ink3); }
.sr-amount { width: 150rpx; text-align: right; font-size: 22rpx; color: var(--ink); font-variant-numeric: tabular-nums; }

.trend { display: flex; align-items: flex-end; justify-content: space-between; height: 280rpx; padding-top: 20rpx; }
.trend-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8rpx; }
.trend-bar-wrap { height: 180rpx; display: flex; align-items: flex-end; }
.trend-bar { width: 34rpx; background: linear-gradient(180deg, #E8A33D, #D97742); border-radius: 8rpx 8rpx 0 0; }
.trend-label { font-size: 20rpx; color: var(--ink3); }
.trend-val { font-size: 18rpx; color: var(--ink3); }

/* 弹层表单 */
.dir-tabs { display: flex; gap: 16rpx; margin-bottom: 16rpx; }
.dir {
  flex: 1; height: 68rpx; line-height: 68rpx; text-align: center;
  background: var(--line2); color: var(--ink2); border-radius: 14rpx; font-size: 26rpx;
}
.dir.on-expense { background: var(--danger-l); color: var(--danger); font-weight: 600; }
.dir.on-income { background: var(--ok-l); color: var(--ok); font-weight: 600; }

.amount-row { display: flex; align-items: center; gap: 12rpx; padding: 20rpx 0 26rpx; border-bottom: 1rpx solid var(--line2); }
.amount-sym { font-size: 42rpx; color: var(--ink2); }
.amount-input { flex: 1; font-size: 62rpx; font-weight: 700; color: var(--ink); height: 80rpx; }

.cat-grid { display: flex; flex-wrap: wrap; gap: 14rpx; margin: 22rpx 0 10rpx; }
.cat-cell {
  width: calc(20% - 12rpx); box-sizing: border-box; padding: 14rpx 0;
  display: flex; flex-direction: column; align-items: center; gap: 6rpx;
  background: var(--bg); border: 1rpx solid var(--line2); border-radius: 16rpx;
}
.cat-cell.on { background: var(--brand-sel); border-color: var(--brand-bd); }
.cat-cell.on .cc-name { color: var(--brand-d); font-weight: 600; }
.cat-cell.add { border-style: dashed; }
.cat-cell.add.on { border-style: solid; background: var(--bg); border-color: var(--line); }
.cc-emoji { font-size: 34rpx; }
.cc-name { font-size: 20rpx; color: var(--ink2); }

/* 内嵌新增分类面板 */
.cat-add {
  margin: 2rpx 0 14rpx; padding: 16rpx;
  background: var(--bg); border: 1rpx solid var(--line2); border-radius: 16rpx;
}
.emoji-row { width: 100%; white-space: nowrap; }
.emoji-inner { display: inline-flex; gap: 10rpx; padding: 2rpx; }
.emoji-opt {
  width: 64rpx; height: 64rpx; line-height: 64rpx; text-align: center;
  font-size: 32rpx; background: #fff; border: 1rpx solid var(--line2); border-radius: 14rpx;
}
.emoji-opt.on { border-color: var(--brand-bd); background: var(--brand-sel); box-shadow: inset 0 0 0 2rpx var(--brand-bd); }
.ca-row { display: flex; align-items: center; gap: 12rpx; margin-top: 14rpx; }
.ca-input {
  flex: 1; height: 68rpx; padding: 0 20rpx; background: #fff;
  border: 1rpx solid var(--line2); border-radius: 14rpx; font-size: 25rpx; color: var(--ink);
}
.ca-ok {
  padding: 0 28rpx; height: 68rpx; line-height: 68rpx; border-radius: 14rpx;
  background: var(--brand); color: #fff; font-size: 25rpx;
}
.ca-ok.loading { opacity: 0.6; }

.submit { margin-top: 32rpx; }
.del-link { text-align: center; color: var(--danger); font-size: 24rpx; padding: 24rpx 0 0; }

@media (min-width: 768px) {
  .page { max-width: 720px; margin: 0 auto; }
}
</style>
