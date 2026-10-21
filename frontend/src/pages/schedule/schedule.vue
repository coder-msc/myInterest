<template>
  <view class="page">
    <!-- 月份切换 -->
    <view class="cal-nav">
      <text class="cn-arrow" @click="shiftMonth(-1)">‹</text>
      <view class="cn-center">
        <text class="cn-label">{{ calYear }} 年 {{ calMonth }} 月</text>
        <text class="cn-sub">{{ monthSummary }}</text>
      </view>
      <text class="cn-arrow" @click="shiftMonth(1)">›</text>
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
      <view class="section-title">
        <text>{{ calMonth }} 月 {{ selectedDay }} 日 · {{ weekdayText }}</text>
        <view class="st-right">
          <text class="section-extra">{{ dayItems.length }} 项安排</text>
          <text class="cal-add" @click="openSheet(null)">＋ 记日子</text>
        </view>
      </view>

      <view v-if="!dayItems.length" class="cal-empty">这天没有安排，安心摸鱼。</view>

      <view v-for="(it, i) in dayItems" :key="it.kind + '-' + it.id + '-' + i"
            class="cal-item" @click="openItem(it)">
        <text class="ci-emoji">{{ it.emoji }}</text>
        <view class="ci-main">
          <text class="ci-name">{{ it.title }}</text>
          <text class="ci-sub">{{ it.sub }}</text>
        </view>
        <text :class="['ci-kind', 'kind-' + it.kind]">{{ kindLabel(it.kind) }}</text>
      </view>
    </view>

    <view class="notice">
      <text class="notice-title">✳️ 关于日历</text>
      <text class="notice-text">日历汇总「值得记」里的日子、旅游行程与大事件。新增或修改日子后，回到这里会自动更新。</text>
    </view>

    <CountdownSheet :visible="sheetVisible" :item="editingItem"
                    @close="sheetVisible = false" @saved="onSaved" @deleted="onSaved" />
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiCountdowns, apiTrips, apiEvents } from '@/api'
import CountdownSheet from '@/components/CountdownSheet.vue'

const weeks = ['一', '二', '三', '四', '五', '六', '日']
const now = new Date()
const calYear = ref(now.getFullYear())
const calMonth = ref(now.getMonth() + 1)
const selectedDay = ref(now.getDate())

const countdowns = ref([])
const trips = ref([])
const events = ref([])
const loading = ref(false)
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

function shiftMonth(delta) {
  const idx = calYear.value * 12 + (calMonth.value - 1) + delta
  calYear.value = Math.floor(idx / 12)
  calMonth.value = (idx % 12) + 1
  selectedDay.value = 1
  loadMonth()
}

function select(d) { selectedDay.value = d }

function openSheet(cd) {
  editingItem.value = cd || null
  sheetVisible.value = true
}

function openItem(it) {
  if (it.kind === 'countdown') return openSheet(it.raw)
  if (it.kind === 'trip') return uni.navigateTo({ url: `/pages/trips/detail?id=${it.id}` })
  // 大事件没有独立详情页，回到值得记的大事件分段查看
  uni.setStorageSync('worth_tab', 'event')
  uni.switchTab({ url: '/pages/worth/worth' })
}

function onSaved() {
  sheetVisible.value = false
  loadMonth()
}

async function loadMonth() {
  const reqMonth = monthKey.value
  loading.value = true
  try {
    const d = await apiCountdowns({ month: reqMonth })
    if (reqMonth !== monthKey.value) return
    countdowns.value = d.items || []
  } finally {
    loading.value = false
  }
}

async function loadTripsAndEvents() {
  try {
    const [t, e] = await Promise.all([apiTrips(), apiEvents()])
    trips.value = t.items || []
    const groups = e.groups || []
    events.value = groups.reduce((all, g) => all.concat(g.items || []), [])
  } catch (err) { /* toast 已统一 */ }
}

onMounted(() => {
  loadMonth()
  loadTripsAndEvents()
})

onShow(() => {
  // 从值得记改完日子回来时刷新，避免日历还是旧数据
  loadMonth()
})
</script>

<style scoped>
.page { padding: 24rpx; min-height: 100vh; background: var(--bg); box-sizing: border-box; }

.cal-nav { display: flex; align-items: center; justify-content: space-between; padding: 4rpx 10rpx 20rpx; }
.cn-arrow { font-size: 44rpx; color: var(--ink2); padding: 0 24rpx; line-height: 1; }
.cn-center { display: flex; flex-direction: column; align-items: center; gap: 6rpx; }
.cn-label { font-size: 31rpx; font-weight: 700; color: var(--ink); }
.cn-sub { font-size: 20rpx; color: var(--ink3); }

.calendar { background: #fff; border: 1rpx solid var(--line2); border-radius: 24rpx; padding: 20rpx 16rpx; }
.week-head { display: flex; }
.wh-item { flex: 1; text-align: center; font-size: 20rpx; color: var(--ink3); padding-bottom: 12rpx; }
.cal-grid { display: flex; flex-wrap: wrap; }
.cal-cell {
  width: 14.28%; height: 92rpx; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 6rpx; border-radius: 14rpx;
}
.cal-cell.blank { visibility: hidden; }
.cc-day { font-size: 26rpx; color: var(--ink); }
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

.legend { display: flex; gap: 26rpx; padding: 18rpx 12rpx 4rpx; }
.lg-item { display: flex; align-items: center; gap: 8rpx; }
.lg-text { font-size: 19rpx; color: var(--ink3); }

.day-block { margin-top: 26rpx; }
.section-title {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 27rpx; font-weight: 700; color: var(--ink); padding: 0 6rpx 16rpx;
}
.st-right { display: flex; align-items: center; gap: 14rpx; }
.section-extra { font-size: 22rpx; color: var(--ink3); font-weight: 400; }
.cal-add { font-size: 23rpx; color: var(--brand-d); font-weight: 600; }
.cal-empty { text-align: center; font-size: 22rpx; color: var(--ink3); padding: 36rpx 0; }

.cal-item {
  display: flex; align-items: center; gap: 16rpx; background: #fff;
  border: 1rpx solid var(--line2); border-radius: 18rpx; padding: 20rpx 22rpx; margin-bottom: 12rpx;
}
.ci-emoji { font-size: 32rpx; }
.ci-main { flex: 1; display: flex; flex-direction: column; gap: 4rpx; min-width: 0; }
.ci-name { font-size: 27rpx; font-weight: 600; color: var(--ink); }
.ci-sub { font-size: 20rpx; color: var(--ink3); }
.ci-kind { font-size: 18rpx; padding: 4rpx 12rpx; border-radius: 8rpx; }
.kind-countdown { background: var(--brand-l); color: var(--brand-d); }
.kind-trip { background: #EAF2F7; color: #426E82; }
.kind-event { background: #F1ECF9; color: #6C5B8E; }

.notice { padding: 22rpx; border-radius: 18rpx; background: var(--line2); margin-top: 16rpx; }
.notice-title { display: block; font-size: 21rpx; font-weight: 600; color: var(--ink2); }
.notice-text { display: block; font-size: 19rpx; color: var(--ink3); line-height: 1.7; margin-top: 8rpx; }

@media (min-width: 768px) {
  .page { max-width: 720px; margin: 0 auto; }
}
</style>
