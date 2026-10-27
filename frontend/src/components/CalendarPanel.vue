<template>
  <view class="cal-card">
    <!-- 卡片头：标题 + 收起/展开（手札首页内容多，允许折起来只看摘要） -->
    <view class="cc-head" @click="toggle">
      <text class="cc-title">📅 日历</text>
      <view class="cc-head-right">
        <text v-if="collapsed" class="cc-sum">{{ calYear }} 年 {{ calMonth }} 月 · {{ monthSummary }}</text>
        <text class="cc-toggle">{{ collapsed ? '展开 ⌄' : '收起 ⌃' }}</text>
      </view>
    </view>

    <block v-if="!collapsed">
      <!-- 月份切换 -->
      <view class="cal-nav">
        <text class="cn-arrow" @click.stop="shiftMonth(-1)">‹</text>
        <view class="cn-center">
          <text class="cn-label">{{ calYear }} 年 {{ calMonth }} 月</text>
          <text class="cn-sub">{{ monthSummary }}</text>
        </view>
        <text class="cn-arrow" @click.stop="shiftMonth(1)">›</text>
      </view>

      <view class="calendar">
        <view class="week-head">
          <text v-for="w in weeks" :key="w" class="wh-item">{{ w }}</text>
        </view>
        <view class="cal-grid">
          <view v-for="(cell, i) in cells" :key="i"
                :class="['cal-cell', !cell.day ? 'blank' : '', cell.isToday ? 'today' : '',
                         cell.items.length ? 'has' : '', selectedDay === cell.day ? 'sel' : '']"
                @click="cell.day && select(cell.day)">
            <text v-if="cell.day" class="cc-day">{{ cell.day }}</text>
            <view v-if="cell.items.length" class="cc-dots">
              <view v-for="(it, j) in cell.items.slice(0, 3)" :key="j"
                    :class="['cc-dot', 'dot-' + it.kind]"></view>
            </view>
          </view>
        </view>
      </view>

      <!-- 图例 -->
      <view class="legend">
        <view class="lg-item"><view class="cc-dot dot-countdown"></view><text class="lg-text">日子</text></view>
        <view class="lg-item"><view class="cc-dot dot-trip"></view><text class="lg-text">行程</text></view>
        <view class="lg-item"><view class="cc-dot dot-event"></view><text class="lg-text">大事件</text></view>
      </view>

      <!-- 当天安排 -->
      <view class="day-block">
        <view class="day-head">
          <text class="day-title">{{ calMonth }} 月 {{ selectedDay }} 日 · {{ weekdayText }}</text>
          <view class="st-right">
            <text class="day-count">{{ dayItems.length }} 项安排</text>
          </view>
        </view>

        <view v-if="!dayItems.length" class="cal-empty">这天没有安排，安心摸鱼。</view>

        <view v-for="(it, i) in dayItems" :key="it.kind + '-' + it.id + '-' + i"
              class="cal-item" @click.stop="openItem(it)">
          <text class="ci-emoji">{{ it.emoji }}</text>
          <view class="ci-main">
            <text class="ci-name">{{ it.title }}</text>
            <text class="ci-sub">{{ it.sub }}</text>
          </view>
          <text :class="['ci-kind', 'kind-' + it.kind]">{{ kindLabel(it.kind) }}</text>
        </view>
      </view>
    </block>

    <CountdownSheet :visible="sheetVisible" :item="editingItem"
                    @close="sheetVisible = false" @saved="onSaved" @deleted="onSaved" />
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { apiCountdowns, apiTrips, apiEvents } from '@/api'
import CountdownSheet from '@/components/CountdownSheet.vue'
import { requireLogin } from '@/utils/auth'

const emit = defineEmits(['changed'])

const weeks = ['一', '二', '三', '四', '五', '六', '日']
const now = new Date()
const calYear = ref(now.getFullYear())
const calMonth = ref(now.getMonth() + 1)
const selectedDay = ref(now.getDate())
// 折叠状态记在本地：收起后手札首页更短，下次进来保持上次的选择
const collapsed = ref(uni.getStorageSync('journal_cal_collapsed') === 1)

const countdowns = ref([])
const trips = ref([])
const events = ref([])
const sheetVisible = ref(false)
const editingItem = ref(null)

const monthKey = computed(() => `${calYear.value}-${String(calMonth.value).padStart(2, '0')}`)

/** 把三类记录摊平成「某天的安排」，日期统一用 YYYY-MM-DD */
const byDate = computed(() => {
  const map = {}
  const push = (date, item) => {
    if (!date) return
    const key = String(date).slice(0, 10)
    if (!map[key]) map[key] = []
    map[key].push(item)
  }

  for (const cd of countdowns.value) {
    push(cd.next_date, {
      kind: 'countdown', id: cd.id, emoji: cd.emoji || '🎯', raw: cd,
      title: cd.name, sub: `${ruleLabel(cd.repeat_rule)} · ${cd.state_label || ''}`,
    })
  }

  for (const t of trips.value) {
    const start = String(t.start_date || '').slice(0, 10)
    const end = String(t.end_date || '').slice(0, 10)
    if (!start) continue
    // 行程按天铺开，跨天行程在每一天都留一个点
    let cursor = new Date(start)
    const last = end ? new Date(end) : new Date(start)
    let guard = 0
    while (cursor <= last && guard < 90) {
      push(toDate(cursor), {
        kind: 'trip', id: t.id, emoji: '🧳', raw: t,
        title: t.title || (t.destinations || []).join(' · '),
        sub: `${start} → ${end}`,
      })
      cursor.setDate(cursor.getDate() + 1)
      guard += 1
    }
  }

  for (const e of events.value) {
    push(e.event_date, {
      kind: 'event', id: e.id, emoji: e.emoji || '🎉', raw: e,
      title: e.title, sub: `${e.category || '大事件'}`,
    })
  }
  return map
})

const cells = computed(() => {
  const first = new Date(calYear.value, calMonth.value - 1, 1)
  const offset = (first.getDay() + 6) % 7 // 周一为第一列
  const total = new Date(calYear.value, calMonth.value, 0).getDate()
  const todayStr = toDate(new Date())
  const out = []
  for (let i = 0; i < offset; i++) out.push({ day: 0, items: [] })
  for (let d = 1; d <= total; d++) {
    const ds = `${monthKey.value}-${String(d).padStart(2, '0')}`
    out.push({ day: d, isToday: ds === todayStr, items: byDate.value[ds] || [] })
  }
  return out
})

const dayItems = computed(() => {
  const ds = `${monthKey.value}-${String(selectedDay.value).padStart(2, '0')}`
  return byDate.value[ds] || []
})

const monthSummary = computed(() => {
  const days = cells.value.filter(c => c.day && c.items.length).length
  return days ? `本月 ${days} 天有安排` : '本月还没有安排'
})

const weekdayText = computed(() => {
  const d = new Date(calYear.value, calMonth.value - 1, selectedDay.value)
  return '周' + weeks[(d.getDay() + 6) % 7]
})

function toDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function ruleLabel(r) {
  return {
    once: '只一次', yearly: '每年', monthly: '每月',
    yearly_lunar: '每年农历', anniversary: '纪念日',
  }[r] || ''
}

function kindLabel(k) {
  return { countdown: '日子', trip: '行程', event: '事件' }[k] || ''
}

function toggle() {
  collapsed.value = !collapsed.value
  uni.setStorageSync('journal_cal_collapsed', collapsed.value ? 1 : 0)
}

function shiftMonth(delta) {
  const idx = calYear.value * 12 + (calMonth.value - 1) + delta
  calYear.value = Math.floor(idx / 12)
  calMonth.value = (idx % 12) + 1
  selectedDay.value = 1
  loadMonth()
}

function select(d) { selectedDay.value = d }

function openSheet(cd) {
  // 新增/编辑日子先确认登录，避免填完表单提交时才被拦
  if (!requireLogin(cd ? '登录后才能修改这个日子' : '登录后才能记日子')) return
  editingItem.value = cd || null
  sheetVisible.value = true
}

function openItem(it) {
  if (it.kind === 'countdown') return openSheet(it.raw)
  if (it.kind === 'trip') return uni.navigateTo({ url: `/pages/trips/detail?id=${it.id}` })
  // 大事件没有独立详情页，去值得记的大事件分段看
  uni.setStorageSync('worth_tab', 'event')
  uni.switchTab({ url: '/pages/worth/worth' })
}

function onSaved() {
  sheetVisible.value = false
  loadMonth()
  emit('changed')
}

async function loadMonth() {
  const reqMonth = monthKey.value
  try {
    const d = await apiCountdowns({ month: reqMonth })
    // 快速翻月时丢弃过期响应，避免上个月的数据盖掉当月
    if (reqMonth !== monthKey.value) return
    countdowns.value = d.items || []
  } catch (e) { /* toast 已统一 */ }
}

async function loadTripsAndEvents() {
  try {
    const [t, e] = await Promise.all([fetchAllTrips(), fetchAllEvents()])
    trips.value = t
    events.value = e
  } catch (e) { /* toast 已统一 */ }
}

/** 日历要看全年，行程/大事件接口是分页的，这里逐页取完（最多 500 条） */
async function fetchAllTrips() {
  let page = 1
  let out = []
  while (page <= 10) {
    const d = await apiTrips({ page, page_size: 50 })
    out = out.concat(d.items || [])
    if (!d.has_more) break
    page += 1
  }
  return out
}

async function fetchAllEvents() {
  let page = 1
  let out = []
  while (page <= 10) {
    const d = await apiEvents({ page, page_size: 50 })
    out = out.concat((d.groups || []).reduce((all, g) => all.concat(g.items || []), []))
    if (!d.has_more) break
    page += 1
  }
  return out
}

async function reload() {
  await Promise.all([loadMonth(), loadTripsAndEvents()])
}

onMounted(reload)

defineExpose({ reload })
</script>

<style scoped>
.cal-card {
  background: #fff; border: 1rpx solid var(--line2); border-radius: 24rpx;
  padding: 22rpx 20rpx; margin-bottom: 24rpx;
}
.cc-head { display: flex; align-items: center; justify-content: space-between; padding: 0 4rpx 4rpx; }
.cc-title { font-size: 27rpx; font-weight: 700; color: var(--ink); }
.cc-head-right { display: flex; align-items: center; gap: 16rpx; }
.cc-sum { font-size: 20rpx; color: var(--ink3); }
.cc-toggle { font-size: 21rpx; color: var(--brand-d); }

.cal-nav { display: flex; align-items: center; justify-content: space-between; padding: 8rpx 2rpx 14rpx; }
.cn-arrow { font-size: 40rpx; color: var(--ink2); padding: 0 20rpx; line-height: 1; }
.cn-center { display: flex; flex-direction: column; align-items: center; gap: 4rpx; }
.cn-label { font-size: 28rpx; font-weight: 700; color: var(--ink); }
.cn-sub { font-size: 19rpx; color: var(--ink3); }

.calendar { border-radius: 20rpx; }
.week-head { display: flex; }
.wh-item { flex: 1; text-align: center; font-size: 20rpx; color: var(--ink3); padding-bottom: 10rpx; }
.cal-grid { display: flex; flex-wrap: wrap; }
.cal-cell {
  width: 14.28%; height: 84rpx; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 5rpx; border-radius: 14rpx;
  margin-bottom: 4rpx;
}
.cal-cell.blank { visibility: hidden; }
.cc-day { font-size: 25rpx; color: var(--ink); }
.cal-cell.today .cc-day { color: var(--brand-d); font-weight: 700; }
.cal-cell.has { background: var(--brand-l); }
.cal-cell.sel { background: var(--brand); }
.cal-cell.sel .cc-day { color: #fff; }
.cc-dots { display: flex; gap: 4rpx; }
.cc-dot { width: 8rpx; height: 8rpx; border-radius: 50%; }
.dot-countdown { background: var(--brand); }
.dot-trip { background: #5B8FA6; }
.dot-event { background: #8E7AB5; }
.cal-cell.sel .cc-dot { background: #fff; }

.legend { display: flex; gap: 26rpx; padding: 14rpx 6rpx 2rpx; }
.lg-item { display: flex; align-items: center; gap: 8rpx; }
.lg-text { font-size: 19rpx; color: var(--ink3); }

.day-block { margin-top: 20rpx; border-top: 1rpx solid var(--line2); padding-top: 18rpx; }
.day-head { display: flex; align-items: center; justify-content: space-between; padding: 0 4rpx 12rpx; }
.day-title { font-size: 25rpx; font-weight: 700; color: var(--ink); }
.st-right { display: flex; align-items: center; gap: 12rpx; }
.day-count { font-size: 20rpx; color: var(--ink3); }
.cal-empty { text-align: center; font-size: 22rpx; color: var(--ink3); padding: 26rpx 0 12rpx; }

.cal-item {
  display: flex; align-items: center; gap: 14rpx; background: var(--bg);
  border-radius: 16rpx; padding: 16rpx 18rpx; margin-bottom: 10rpx;
}
.ci-emoji { font-size: 30rpx; }
.ci-main { flex: 1; display: flex; flex-direction: column; gap: 3rpx; min-width: 0; }
.ci-name { font-size: 25rpx; font-weight: 600; color: var(--ink); }
.ci-sub { font-size: 19rpx; color: var(--ink3); }
.ci-kind { font-size: 18rpx; padding: 3rpx 10rpx; border-radius: 8rpx; }
.kind-countdown { background: var(--brand-l); color: var(--brand-d); }
.kind-trip { background: #EAF2F7; color: #426E82; }
.kind-event { background: #F1ECF9; color: #6C5B8E; }
</style>
