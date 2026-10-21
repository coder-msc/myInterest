<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="值得记" subtitle="值得等的事，值得回头的日子" /><!-- #endif -->

    <!-- 顶部可横向滑动的分段：后续想加「纪念物 / 健康打卡」等大项，只需往 segments 里加一行 -->
    <scroll-view class="seg-scroll" scroll-x :scroll-into-view="scrollTo"
                 :show-scrollbar="false" scroll-with-animation>
      <view class="seg-inner">
        <view
          v-for="(s, i) in segments"
          :key="s.key"
          :id="'seg-' + s.key"
          :class="['seg-pill', tab === s.key ? 'on' : '']"
          @click="switchTab(s.key, i)"
        >
          <text class="sp-emoji">{{ s.emoji }}</text>
          <text class="sp-label">{{ s.label }}</text>
        </view>
      </view>
    </scroll-view>

    <!-- 内容区：左右滑动切分段；切换时做位移动画 -->
    <view class="seg-body" :class="slideClass"
          @touchstart="onTouchStart" @touchend="onTouchEnd" @touchcancel="onTouchCancel">
    <!-- ===== 倒计时 ===== -->
    <block v-if="tab === 'countdown'">
      <view v-if="cdLoading && !items.length" class="loading-text">牛马拉磨中…</view>

      <view v-else-if="!items.length" class="empty">
        <text class="empty-title">还没有任何日子。</text>
        <text class="empty-sub">生日、纪念日、发薪日、还款日，都值得被记住。</text>
        <view class="empty-btn" @click="openSheet()">记一个重要日子</view>
      </view>

      <block v-else>
        <view class="cd-head">
          <text class="cd-total">共 {{ items.length }} 个日子</text>
          <text class="cd-add" @click="openSheet()">＋ 新增</text>
        </view>

        <view v-if="topItem" class="top-banner" :class="'state-' + topItem.state">
          <text class="tb-emoji">{{ topItem.emoji }}</text>
          <view class="tb-main">
            <text class="tb-name">{{ topItem.name }}</text>
            <text class="tb-date">{{ topItem.next_date }}{{ topItem.lunar_text ? ' · 农历' + topItem.lunar_text : '' }}</text>
          </view>
          <text class="tb-days">{{ topItem.state_label }}</text>
        </view>

        <view v-for="cd in items" :key="cd.id" :class="['cd-card', 'state-' + cd.state]" @click="openSheet(cd)">
          <view class="cd-left">
            <text class="cd-emoji">{{ cd.emoji || '🎯' }}</text>
          </view>
          <view class="cd-main">
            <view class="cd-title-row">
              <text class="cd-name">{{ cd.name }}</text>
              <text v-if="cd.pinned" class="cd-pin">📌</text>
              <text class="cd-rule">{{ ruleLabel(cd.repeat_rule) }}</text>
            </view>
            <text class="cd-date">
              <text v-if="cd.repeat_rule === 'anniversary'">{{ cd.base_date }} 起 · {{ cd.days_since }} 天</text>
              <text v-else>{{ cd.next_date }}<text v-if="cd.year_no > 1" class="cd-year">第 {{ cd.year_no }} 次</text></text>
              <text v-if="cd.lunar_text" class="cd-lunar">农历 {{ cd.lunar_text }}</text>
            </text>
            <view class="cd-foot">
              <text v-for="o in cd.remind_offsets" :key="o" class="cd-offset">{{ offsetLabel(o) }}</text>
              <text v-if="!cd.remind_offsets.length" class="cd-offset muted">不提醒</text>
            </view>
          </view>
          <view class="cd-right" @click.stop="togglePin(cd)">
            <text class="cd-days">{{ cd.state_label }}</text>
            <text class="cd-pin-btn">{{ cd.pinned ? '取消置顶' : '置顶' }}</text>
          </view>
        </view>
        <view class="hint">长按某一条可以删掉它</view>
      </block>
    </block>

    <!-- ===== 月历 ===== -->
    <block v-else-if="tab === 'calendar'">
      <view class="cal-nav">
        <text class="cn-arrow" @click="shiftCal(-1)">‹</text>
        <text class="cn-label">{{ calYear }} 年 {{ calMonth }} 月</text>
        <text class="cn-arrow" @click="shiftCal(1)">›</text>
      </view>

      <view class="calendar">
        <view class="week-head">
          <text v-for="w in weeks" :key="w" class="wh-item">{{ w }}</text>
        </view>
        <view class="cal-grid">
          <view v-for="(cell, i) in calendarCells" :key="i"
                :class="['cal-cell', !cell.day ? 'blank' : '', cell.isToday ? 'today' : '',
                         cell.items.length ? 'has' : '', selectedDay === cell.day ? 'sel' : '']"
                @click="cell.day && selectDay(cell.day)">
            <text v-if="cell.day" class="cc-day">{{ cell.day }}</text>
            <view v-if="cell.items.length" class="cc-dots">
              <view v-for="(it, j) in cell.items.slice(0, 3)" :key="j" class="cc-dot"></view>
            </view>
          </view>
        </view>
      </view>

      <view class="cal-list">
        <view class="section-title">
          <text>{{ calMonth }} 月 {{ selectedDay || '—' }} 日</text>
          <view class="st-right">
            <text class="section-extra">{{ dayItems.length }} 个日子</text>
            <text class="cal-add" @click="openSheet()">＋ 新增</text>
          </view>
        </view>
        <view v-if="!dayItems.length" class="cal-empty">这天没有安排，安心摸鱼。</view>
        <view v-for="cd in dayItems" :key="cd.id" class="cal-item" @click="openSheet(cd)">
          <text class="ci-emoji">{{ cd.emoji }}</text>
          <view class="ci-main">
            <text class="ci-name">{{ cd.name }}</text>
            <text class="ci-sub">{{ ruleLabel(cd.repeat_rule) }} · {{ cd.state_label }}</text>
          </view>
          <text class="ci-arrow">›</text>
        </view>
      </view>
    </block>

    <!-- ===== 旅游 ===== -->
    <block v-else-if="tab === 'trip'">
      <view v-if="tripLoading && !trips.length" class="loading-text">牛马拉磨中…</view>

      <view v-else-if="!trips.length" class="empty">
        <text class="empty-title">还没出去走过。</text>
        <text class="empty-sub">先把想去的地方记下来，也是一种出发。</text>
        <view class="empty-btn" @click="openTrip()">记一次出行</view>
      </view>

      <block v-else>
        <view class="trip-stats">
          <view class="ts-cell"><text class="ts-num">{{ tripMeta.trip_count || 0 }}</text><text class="ts-label">次出行</text></view>
          <view class="ts-cell"><text class="ts-num">{{ tripMeta.city_count || 0 }}</text><text class="ts-label">座城市</text></view>
          <view class="ts-cell"><text class="ts-num">{{ totalPhotos }}</text><text class="ts-label">张照片</text></view>
          <view class="ts-add" @click="openTrip()">＋ 新增</view>
        </view>

        <view v-for="t in trips" :key="t.id" class="trip-card" @click="goTrip(t.id)">
          <image v-if="t.cover_url" class="tc-cover" :src="mediaUrl(t.cover_url)" mode="aspectFill" />
          <view v-else class="tc-cover tc-cover-empty"><text>🧳</text></view>
          <view class="tc-body">
            <view class="tc-top">
              <text class="tc-title">{{ t.title }}</text>
              <text v-if="t.status === 'ongoing'" class="chip chip-countdown">进行中</text>
              <text v-else-if="t.status === 'upcoming'" class="chip chip-trip">计划中</text>
            </view>
            <text class="tc-dest">{{ t.destinations.join(' · ') }}</text>
            <text class="tc-date">{{ t.start_date }} → {{ t.end_date }}</text>
            <view class="tc-foot">
              <text class="tc-pill" v-if="t.companions">👥 {{ t.companions }}</text>
              <text class="tc-pill" v-if="t.photo_count">📷 {{ t.photo_count }}</text>
              <text class="tc-pill" v-if="t.cost">💰 ¥{{ money(t.cost) }}</text>
            </view>
          </view>
        </view>
      </block>
    </block>

    <!-- ===== 大事件 ===== -->
    <block v-else>
      <view v-if="eventLoading && !eventGroups.length" class="loading-text">牛马拉磨中…</view>

      <view v-else-if="!eventGroups.length" class="empty">
        <text class="empty-title">人生还没被分成章节。</text>
        <text class="empty-sub">换工作、搬家、毕业、第一次一个人旅行，都算。</text>
        <view class="empty-btn" @click="openEvent()">记一个节点</view>
      </view>

      <block v-else>
        <view class="ev-head">
          <text class="ev-total">共 {{ eventTotal }} 个节点</text>
          <text class="ev-add" @click="openEvent()">＋ 新增</text>
        </view>

        <view v-for="g in eventGroups" :key="g.year" class="year-block">
          <view class="year-label">{{ g.year }}<text class="year-count">{{ g.count }} 件</text></view>
          <view class="ev-list">
            <view v-for="e in g.items" :key="e.id" class="ev-card" @click="openEvent(e)">
              <text class="ev-emoji">{{ e.emoji || '🎉' }}</text>
              <view class="ev-main">
                <text class="ev-title">{{ e.title }}</text>
                <text class="ev-sub">{{ e.event_date }} · {{ e.category }}</text>
                <text v-if="e.content" class="ev-content">{{ e.content }}</text>
              </view>
              <image v-if="e.cover_url" class="ev-cover" :src="mediaUrl(e.cover_url)" mode="aspectFill" />
              <text v-else-if="e.photo_count" class="ev-photo">📷{{ e.photo_count }}</text>
            </view>
          </view>
        </view>
      </block>
    </block>
    </view>

    <view style="height: 180rpx"></view>

    <!-- ===== 日子表单 ===== -->
    <view v-if="sheetVisible" class="sheet-mask" @click="sheetVisible = false">
      <view class="sheet" @click.stop>
        <view class="sheet-head">
          <text class="sheet-title">{{ editingId ? '编辑日子' : '记一个重要日子' }}</text>
          <text class="sheet-close" @click="sheetVisible = false">✕</text>
        </view>

        <view class="field">
          <text class="f-label">名称</text>
          <input class="f-input" v-model="form.name" maxlength="20" placeholder="发薪日 / 妈妈生日 / 结婚纪念日" />
        </view>

        <view class="field">
          <text class="f-label">{{ form.repeat_rule === 'anniversary' ? '起始日' : '日期' }}</text>
          <picker mode="date" :value="form.date" @change="e => form.date = e.detail.value">
            <view class="f-input">{{ form.date }}</view>
          </picker>
        </view>

        <view class="field">
          <text class="f-label">重复方式</text>
          <view class="opt-chips">
            <view v-for="r in rules" :key="r.value"
                  :class="['opt-chip', form.repeat_rule === r.value ? 'on' : '']"
                  @click="form.repeat_rule = r.value">{{ r.label }}</view>
          </view>
          <text v-if="form.repeat_rule === 'anniversary'" class="rule-tip">
            填已经发生的那一天，会显示「已经 N 周年 / N 天」，每年这一天照常提醒。
          </text>
          <text v-if="form.repeat_rule === 'yearly_lunar'" class="rule-tip">
            按农历保存，每年公历日期会自动换算（春节、生日都可以）。
          </text>
        </view>

        <view class="field">
          <text class="f-label">提前提醒</text>
          <view class="opt-chips">
            <view v-for="o in offsets" :key="o.value"
                  :class="['opt-chip', form.remind_offsets.includes(o.value) ? 'on' : '']"
                  @click="toggleOffset(o.value)">{{ o.label }}</view>
          </view>
          <text class="rule-tip">提醒以站内消息形式发送，在「提醒中心」查看。</text>
        </view>

        <view class="field">
          <text class="f-label">图标</text>
          <view class="opt-chips">
            <view v-for="em in emojis" :key="em"
                  :class="['opt-chip', 'emoji-chip', form.emoji === em ? 'on' : '']"
                  @click="form.emoji = em">{{ em }}</view>
          </view>
        </view>

        <view class="field">
          <text class="f-label">备注</text>
          <input class="f-input" v-model="form.note" maxlength="100" placeholder="要准备什么（可不填）" />
        </view>

        <view class="pin-row" @click="form.pinned = !form.pinned">
          <text class="pin-label">置顶显示在手札首页</text>
          <text :class="['pin-switch', form.pinned ? 'on' : '']">{{ form.pinned ? '已开启' : '未开启' }}</text>
        </view>

        <button class="btn-primary submit" :loading="saving" @click="save">保存</button>
        <view v-if="editingId" class="del-link" @click="removeCurrent">删除这个日子</view>
      </view>
    </view>

    <!-- ===== 旅游表单 ===== -->
    <view v-if="tripSheet" class="sheet-mask" @click="tripSheet = false">
      <view class="sheet" @click.stop>
        <view class="sheet-head">
          <text class="sheet-title">{{ editingTripId ? '编辑行程' : '记一次出行' }}</text>
          <text class="sheet-close" @click="tripSheet = false">✕</text>
        </view>

        <view class="field">
          <text class="f-label">去了哪（多个城市用逗号分隔）</text>
          <input class="f-input" v-model="tripForm.destinations" placeholder="成都, 重庆" />
        </view>
        <view class="field">
          <text class="f-label">开始日期</text>
          <picker mode="date" :value="tripForm.start_date" @change="e => tripForm.start_date = e.detail.value">
            <view class="f-input">{{ tripForm.start_date }}</view>
          </picker>
        </view>
        <view class="field">
          <text class="f-label">结束日期</text>
          <picker mode="date" :value="tripForm.end_date" @change="e => tripForm.end_date = e.detail.value">
            <view class="f-input">{{ tripForm.end_date }}</view>
          </picker>
        </view>
        <view class="field">
          <text class="f-label">同行的人</text>
          <input class="f-input" v-model="tripForm.companions" maxlength="30" placeholder="自己 / 朋友 / 家人" />
        </view>
        <view class="field">
          <text class="f-label">花了多少（可不填）</text>
          <input class="f-input" type="digit" v-model="tripForm.cost" placeholder="0.00" />
        </view>
        <view class="field">
          <text class="f-label">想说点什么</text>
          <textarea class="f-area" v-model="tripForm.content" maxlength="1000"
                    placeholder="天气、味道、当时的心情…" auto-height />
        </view>

        <view class="photo-block">
          <text class="f-label">照片（最多 {{ photoLimit }} 张）</text>
          <view class="photo-grid">
            <view v-for="(p, i) in tripForm.photos" :key="p.id" class="photo-cell">
              <image class="photo-img" :src="mediaUrl(p.thumb_url || p.url)" mode="aspectFill" />
              <text class="photo-del" @click="tripForm.photos.splice(i, 1)">✕</text>
            </view>
            <view v-if="tripForm.photos.length < photoLimit" class="photo-add" @click="pickPhotos('trip')">＋</view>
          </view>
        </view>

        <button class="btn-primary submit" :loading="saving" @click="saveTrip">保存</button>
      </view>
    </view>

    <!-- ===== 大事件表单 ===== -->
    <view v-if="eventSheet" class="sheet-mask" @click="eventSheet = false">
      <view class="sheet" @click.stop>
        <view class="sheet-head">
          <text class="sheet-title">{{ editingEventId ? '编辑大事件' : '记一个节点' }}</text>
          <text class="sheet-close" @click="eventSheet = false">✕</text>
        </view>

        <view class="field">
          <text class="f-label">发生了什么</text>
          <input class="f-input" v-model="eventForm.title" maxlength="30" placeholder="换了第一份工作" />
        </view>
        <view class="field">
          <text class="f-label">日期</text>
          <picker mode="date" :value="eventForm.event_date" @change="e => eventForm.event_date = e.detail.value">
            <view class="f-input">{{ eventForm.event_date }}</view>
          </picker>
        </view>

        <view class="field">
          <text class="f-label">分类</text>
          <view class="cat-chips">
            <view v-for="c in eventCats" :key="c.name"
                  :class="['cat-chip', eventForm.category === c.name ? 'on' : '']"
                  @click="pickEventCat(c)">
              {{ c.emoji }} {{ c.name }}
            </view>
          </view>
        </view>

        <view class="field">
          <text class="f-label">当时心情</text>
          <view class="cat-chips">
            <view v-for="m in moods" :key="m" :class="['cat-chip', eventForm.mood === m ? 'on' : '']"
                  @click="eventForm.mood = eventForm.mood === m ? '' : m">{{ m }}</view>
          </view>
        </view>

        <view class="field">
          <text class="f-label">展开说说</text>
          <textarea class="f-area" v-model="eventForm.content" maxlength="2000"
                    placeholder="那一刻你在想什么…" auto-height />
        </view>

        <view class="photo-block">
          <text class="f-label">照片</text>
          <view class="photo-grid">
            <view v-for="(p, i) in eventForm.photos" :key="p.id" class="photo-cell">
              <image class="photo-img" :src="mediaUrl(p.thumb_url || p.url)" mode="aspectFill" />
              <text class="photo-del" @click="eventForm.photos.splice(i, 1)">✕</text>
            </view>
            <view v-if="eventForm.photos.length < eventPhotoLimit" class="photo-add" @click="pickPhotos('event')">＋</view>
          </view>
        </view>

        <button class="btn-primary submit" :loading="saving" @click="saveEvent">保存</button>
        <view v-if="editingEventId" class="del-link" @click="removeEvent">删除这条</view>
      </view>
    </view>

    <!-- #ifdef H5 --><CustomTab current="/pages/worth/worth" /><!-- #endif -->
  </view>
</template>

<script setup>
import { computed, nextTick, reactive, ref } from 'vue'
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import {
  apiCountdowns, apiCreateCountdown, apiUpdateCountdown, apiDeleteCountdown,
  apiTrips, apiCreateTrip, apiUpdateTrip, apiEvent, apiEvents,
  apiCreateEvent, apiUpdateEvent, apiDeleteEvent, apiUploadMedia,
} from '@/api'
import { mediaUrl } from '@/utils/config'
import WebLayout from '@/components/WebLayout.vue'
import CustomTab from '@/components/CustomTab.vue'

/** 顶部大项。新增模块时在这里加一项，并在下方加对应的内容块即可。 */
const segments = [
  { key: 'countdown', label: '倒计时', emoji: '🎯' },
  { key: 'calendar', label: '月历', emoji: '📅' },
  { key: 'trip', label: '旅游', emoji: '🧳' },
  { key: 'event', label: '大事件', emoji: '🎉' },
]

const tab = ref('countdown')
const scrollTo = ref('')
const cdLoading = ref(false)
const tripLoading = ref(false)
const eventLoading = ref(false)
const saving = ref(false)

// ---- 日子 ----
const items = ref([])
const sheetVisible = ref(false)
const editingId = ref(null)
const today = new Date().toISOString().slice(0, 10)
const form = reactive({
  name: '', date: today, repeat_rule: 'yearly', remind_offsets: [7, 0],
  emoji: '🎯', note: '', pinned: false,
})
const rules = [
  { value: 'once', label: '只一次' },
  { value: 'yearly', label: '每年' },
  { value: 'monthly', label: '每月' },
  { value: 'yearly_lunar', label: '每年农历' },
  { value: 'anniversary', label: '纪念日' },
]
const offsets = [
  { value: 30, label: '提前 30 天' },
  { value: 7, label: '提前 7 天' },
  { value: 1, label: '提前 1 天' },
  { value: 0, label: '当天' },
]
const emojis = ['🎯', '🎂', '💍', '💰', '🏖️', '🎓', '🏥', '🏠', '🐣', '🌟']
const weeks = ['一', '二', '三', '四', '五', '六', '日']

const topItem = computed(() => {
  const active = items.value.filter(i => !i.is_past)
  const pinned = active.filter(i => i.pinned)
  return (pinned.length ? pinned : active).slice().sort((a, b) => a.days_left - b.days_left)[0] || null
})

// ---- 月历 ----
const calYear = ref(new Date().getFullYear())
const calMonth = ref(new Date().getMonth() + 1)
const selectedDay = ref(new Date().getDate())
const monthItems = ref([])
const monthKey = computed(() => `${calYear.value}-${String(calMonth.value).padStart(2, '0')}`)

const calendarCells = computed(() => {
  const first = new Date(calYear.value, calMonth.value - 1, 1)
  const offset = (first.getDay() + 6) % 7 // 周一为第一列
  const total = new Date(calYear.value, calMonth.value, 0).getDate()
  const cells = []
  for (let i = 0; i < offset; i++) cells.push({ day: 0, items: [] })
  const todayStr = new Date().toISOString().slice(0, 10)
  for (let d = 1; d <= total; d++) {
    const ds = `${monthKey.value}-${String(d).padStart(2, '0')}`
    cells.push({
      day: d,
      isToday: ds === todayStr,
      items: monthItems.value.filter(i => i.next_date === ds),
    })
  }
  return cells
})

const dayItems = computed(() => {
  const ds = `${monthKey.value}-${String(selectedDay.value).padStart(2, '0')}`
  return monthItems.value.filter(i => i.next_date === ds)
})

// ---- 旅游 ----
const trips = ref([])
const tripMeta = reactive({ trip_count: 0, city_count: 0, photo_limit: 20 })
const tripSheet = ref(false)
const editingTripId = ref(null)
const photoLimit = computed(() => tripMeta.photo_limit || 20)
const totalPhotos = computed(() => trips.value.reduce((a, t) => a + (t.photo_count || 0), 0))
const tripForm = reactive({
  destinations: '', start_date: today, end_date: today, companions: '',
  cost: '', content: '', photos: [],
})

// ---- 大事件 ----
const eventGroups = ref([])
const eventTotal = ref(0)
const eventCats = ref([])
const eventPhotoLimit = ref(9)
const eventSheet = ref(false)
const editingEventId = ref(null)
const eventForm = reactive({
  title: '', event_date: today, category: '里程碑', emoji: '🏆',
  mood: '', content: '', photos: [],
})
const moods = ['😀', '😌', '🥲', '🔥', '🌧️', '❤️']

function money(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function ruleLabel(r) {
  return {
    once: '只一次', yearly: '每年', monthly: '每月',
    yearly_lunar: '每年农历', anniversary: '纪念日',
  }[r] || ''
}
function offsetLabel(o) {
  return o === 0 ? '当天提醒' : `提前 ${o} 天`
}

// ---------- 分段切换 ----------
const slideClass = ref('')
let slideTimer = null

/** 分段位移动画：dir=1 从右滑入，dir=-1 从左滑入 */
function playSlide(dir) {
  clearTimeout(slideTimer)
  slideClass.value = ''
  nextTick(() => {
    slideClass.value = dir > 0 ? 'slide-in-right' : 'slide-in-left'
    slideTimer = setTimeout(() => { slideClass.value = '' }, 280)
  })
}

/**
 * 切换分段。
 * @param key 目标分段
 * @param idx 目标下标（点击时传入，滑动时由 onTouchEnd 计算）
 * @param scrollTop 是否回到页面顶部，默认 true
 */
function switchTab(key, idx, scrollTop = true) {
  if (key === tab.value) return
  const prevIdx = segments.findIndex(s => s.key === tab.value)
  const target = typeof idx === 'number' ? idx : segments.findIndex(s => s.key === key)
  tab.value = key
  playSlide(target >= prevIdx ? 1 : -1)
  ensureTabData(key)
  scrollTo.value = 'seg-' + key
  if (scrollTop) uni.pageScrollTo({ scrollTop: 0, duration: 0 })
}

/** 其他页面用 uni.setStorageSync('worth_tab', key) + switchTab 跳进来指定分段。 */
function applyPendingTab() {
  const want = uni.getStorageSync('worth_tab')
  if (!want) return
  uni.removeStorageSync('worth_tab')
  const idx = segments.findIndex(s => s.key === want)
  if (idx >= 0) switchTab(want, idx, false)
}

// ---------- 左右滑动 ----------
const touch = { x: 0, y: 0, at: 0, ok: false }

function anySheetOpen() {
  return sheetVisible.value || tripSheet.value || eventSheet.value
}

function onTouchStart(e) {
  const t = e.touches && e.touches[0]
  if (!t || anySheetOpen()) { touch.ok = false; return }
  touch.x = t.clientX
  touch.y = t.clientY
  touch.at = Date.now()
  touch.ok = true
}

function onTouchCancel() {
  touch.ok = false
}

function onTouchEnd(e) {
  if (!touch.ok) return
  touch.ok = false
  const t = e.changedTouches && e.changedTouches[0]
  if (!t) return
  const dx = t.clientX - touch.x
  const dy = t.clientY - touch.y
  // 手指得有明确横向意图：位移够大、明显横向、且不是长按拖动
  if (Date.now() - touch.at > 700) return
  if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.5) return
  const idx = segments.findIndex(s => s.key === tab.value)
  const next = dx < 0 ? idx + 1 : idx - 1
  if (next < 0 || next >= segments.length) {
    // 已经到头：给一点回弹提示，不做数据请求
    playSlide(dx < 0 ? 1 : -1)
    return
  }
  switchTab(segments[next].key, next)
}

// ---------- 数据加载 ----------
/** 每个分段是否已取过数、取数时间；用于切回时复用缓存，避免每次都闪 loading */
const loaded = reactive({ countdown: false, trip: false, event: false })
const loadedAt = reactive({ countdown: 0, trip: 0, event: 0 })
const CACHE_TTL = 30000

/** 同一接口并发只发一次（onShow、切分段、预取可能同时触发） */
const inflight = new Map()
function once(key, fn) {
  if (inflight.has(key)) return inflight.get(key)
  const p = fn().finally(() => inflight.delete(key))
  inflight.set(key, p)
  return p
}

function loadCountdowns() {
  return once('countdown', async () => {
    cdLoading.value = true
    try {
      const data = await apiCountdowns()
      items.value = data.items || []
      loaded.countdown = true
      loadedAt.countdown = Date.now()
    } finally {
      cdLoading.value = false
    }
  })
}

function loadMonth() {
  const reqMonth = monthKey.value
  return once('month:' + reqMonth, async () => {
    const data = await apiCountdowns({ month: reqMonth })
    // 期间又翻了月份就不覆盖，避免旧月份数据闪一下
    if (reqMonth !== monthKey.value) return
    monthItems.value = data.items || []
  })
}

function loadTrips() {
  return once('trip', async () => {
    tripLoading.value = true
    try {
      const data = await apiTrips()
      trips.value = data.items || []
      tripMeta.trip_count = data.trip_count || 0
      tripMeta.city_count = data.city_count || 0
      tripMeta.photo_limit = data.photo_limit || 20
      loaded.trip = true
      loadedAt.trip = Date.now()
    } finally {
      tripLoading.value = false
    }
  })
}

function loadEvents() {
  return once('event', async () => {
    eventLoading.value = true
    try {
      const data = await apiEvents()
      eventGroups.value = data.groups || []
      eventTotal.value = data.total || 0
      eventCats.value = data.categories || []
      eventPhotoLimit.value = data.photo_limit || 9
      loaded.event = true
      loadedAt.event = Date.now()
    } finally {
      eventLoading.value = false
    }
  })
}

/** 切到某分段时按需取数：有缓存就不再打扰用户 */
function ensureTabData(key, force = false) {
  if (key === 'calendar') return loadMonth()
  const fresh = loaded[key] && Date.now() - loadedAt[key] < CACHE_TTL
  if (!force && fresh) return
  if (key === 'countdown') return loadCountdowns()
  if (key === 'trip') return loadTrips()
  if (key === 'event') return loadEvents()
}

/** 首屏只等当前分段，其余分段空闲时预取，滑动过去就是现成的 */
function refresh(force = true) {
  ensureTabData(tab.value, force)
  if (tab.value !== 'trip' && loaded.trip) loadTrips()
  if (tab.value !== 'event' && loaded.event) loadEvents()
}

function prefetch() {
  setTimeout(() => {
    if (!loaded.trip) loadTrips()
    if (!loaded.event) loadEvents()
  }, 350)
}

// ---------- 日子 ----------
function shiftCal(delta) {
  const idx = calYear.value * 12 + (calMonth.value - 1) + delta
  calYear.value = Math.floor(idx / 12)
  calMonth.value = (idx % 12) + 1
  selectedDay.value = 1
  loadMonth()
}
function selectDay(d) { selectedDay.value = d }

function openSheet(cd) {
  if (cd) {
    editingId.value = cd.id
    form.name = cd.name
    form.date = cd.base_date
    form.repeat_rule = cd.repeat_rule
    form.remind_offsets = [...(cd.remind_offsets || [])]
    form.emoji = cd.emoji || '🎯'
    form.note = cd.note || ''
    form.pinned = !!cd.pinned
  } else {
    editingId.value = null
    form.name = ''
    form.date = today
    form.repeat_rule = 'yearly'
    form.remind_offsets = [7, 0]
    form.emoji = '🎯'
    form.note = ''
    form.pinned = false
  }
  sheetVisible.value = true
}

function toggleOffset(v) {
  const i = form.remind_offsets.indexOf(v)
  if (i >= 0) form.remind_offsets.splice(i, 1)
  else form.remind_offsets.push(v)
}

async function save() {
  if (!form.name.trim()) return uni.showToast({ title: '给它起个名字吧', icon: 'none' })
  saving.value = true
  const payload = {
    name: form.name.trim(), date: form.date, repeat_rule: form.repeat_rule,
    remind_offsets: form.remind_offsets, emoji: form.emoji,
    note: form.note || null,
  }
  try {
    if (editingId.value) {
      await apiUpdateCountdown(editingId.value, { ...payload, pinned: form.pinned })
    } else {
      const cd = await apiCreateCountdown(payload)
      if (form.pinned) await apiUpdateCountdown(cd.id, { pinned: true })
    }
    sheetVisible.value = false
    uni.showToast({ title: '记下了', icon: 'none' })
    await loadCountdowns()
    if (tab.value === 'calendar') loadMonth()
  } catch (e) { /* toast 已统一 */ } finally {
    saving.value = false
  }
}

async function togglePin(cd) {
  try {
    await apiUpdateCountdown(cd.id, { pinned: !cd.pinned })
    await loadCountdowns()
  } catch (e) { /* toast 已统一 */ }
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
      await apiDeleteCountdown(id)
      sheetVisible.value = false
      await loadCountdowns()
      if (tab.value === 'calendar') loadMonth()
    },
  })
}

// ---------- 旅游 ----------
function openTrip(t) {
  editingTripId.value = t ? t.id : null
  if (t) {
    tripForm.destinations = (t.destinations || []).join(', ')
    tripForm.start_date = t.start_date
    tripForm.end_date = t.end_date
    tripForm.companions = t.companions || ''
    tripForm.cost = t.cost ? String(t.cost) : ''
    tripForm.content = t.content || ''
    tripForm.photos = t.photos && t.photos.length ? t.photos : []
  } else {
    tripForm.destinations = ''
    tripForm.start_date = today
    tripForm.end_date = today
    tripForm.companions = ''
    tripForm.cost = ''
    tripForm.content = ''
    tripForm.photos = []
  }
  tripSheet.value = true
}

async function saveTrip() {
  const dests = tripForm.destinations.split(/[,，\s]+/).map(s => s.trim()).filter(Boolean)
  if (!dests.length) return uni.showToast({ title: '至少填一个城市', icon: 'none' })
  saving.value = true
  const payload = {
    destinations: dests,
    start_date: tripForm.start_date,
    end_date: tripForm.end_date,
    companions: tripForm.companions || null,
    cost: tripForm.cost ? Number(tripForm.cost) : null,
    content: tripForm.content || null,
    media_ids: tripForm.photos.map(p => p.id),
  }
  try {
    if (editingTripId.value) {
      const t = await apiUpdateTrip(editingTripId.value, payload)
      await apiUpdateTrip(editingTripId.value, { cover_media_id: t.photos?.[0]?.id || null })
    } else {
      const t = await apiCreateTrip(payload)
      if (t.photos && t.photos.length) {
        await apiUpdateTrip(t.id, { cover_media_id: t.photos[0].id })
      }
    }
    tripSheet.value = false
    uni.showToast({ title: '记下了', icon: 'none' })
    loadTrips()
  } catch (e) { /* toast 已统一 */ } finally {
    saving.value = false
  }
}

function goTrip(id) { uni.navigateTo({ url: `/pages/trips/detail?id=${id}` }) }

// ---------- 大事件 ----------
async function openEvent(e) {
  editingEventId.value = e ? e.id : null
  if (e) {
    const detail = await apiEvent(e.id)
    eventForm.title = detail.title
    eventForm.event_date = detail.event_date
    eventForm.category = detail.category || '里程碑'
    eventForm.emoji = detail.emoji || '🎉'
    eventForm.mood = detail.mood || ''
    eventForm.content = detail.content || ''
    eventForm.photos = detail.photos || []
  } else {
    eventForm.title = ''
    eventForm.event_date = today
    eventForm.category = '里程碑'
    eventForm.emoji = '🏆'
    eventForm.mood = ''
    eventForm.content = ''
    eventForm.photos = []
  }
  eventSheet.value = true
}

function pickEventCat(c) {
  eventForm.category = c.name
  eventForm.emoji = c.emoji
}

function pickPhotos(kind) {
  const target = kind === 'trip' ? tripForm : eventForm
  const limit = kind === 'trip' ? photoLimit.value : eventPhotoLimit.value
  const remain = Math.max(1, limit - target.photos.length)
  uni.chooseImage({
    count: Math.min(remain, 9),
    sizeType: ['compressed'],
    success: async (res) => {
      const paths = res.tempFilePaths || []
      for (const p of paths) {
        try {
          const asset = await apiUploadMedia(p, 'unanchored')
          target.photos.push(asset)
        } catch (e) { /* toast 已统一 */ }
      }
    },
  })
}

async function saveEvent() {
  if (!eventForm.title.trim()) return uni.showToast({ title: '给它起个名字吧', icon: 'none' })
  saving.value = true
  const payload = {
    title: eventForm.title.trim(),
    event_date: eventForm.event_date,
    category: eventForm.category,
    emoji: eventForm.emoji,
    mood: eventForm.mood || null,
    content: eventForm.content || null,
    media_ids: eventForm.photos.map(p => p.id),
  }
  try {
    if (editingEventId.value) await apiUpdateEvent(editingEventId.value, payload)
    else await apiCreateEvent(payload)
    eventSheet.value = false
    uni.showToast({ title: '记下了', icon: 'none' })
    loadEvents()
  } catch (e) { /* toast 已统一 */ } finally {
    saving.value = false
  }
}

function removeEvent() {
  if (!editingEventId.value) return
  const id = editingEventId.value
  uni.showModal({
    title: '真的删？',
    content: '它不会记仇。',
    confirmText: '删掉',
    confirmColor: '#C0555F',
    success: async (res) => {
      if (!res.confirm) return
      await apiDeleteEvent(id)
      eventSheet.value = false
      loadEvents()
    },
  })
}

onShow(() => {
  refresh()
  applyPendingTab()
  prefetch()
})
onPullDownRefresh(async () => {
  refresh()
  try {
    await Promise.all([loadCountdowns(), loadTrips(), loadEvents()])
  } finally {
    uni.stopPullDownRefresh()
  }
})
</script>

<style scoped>
.page { padding: 24rpx; }

/* 顶部可滑动分段 */
.seg-scroll {
  width: 100%; white-space: nowrap; margin-bottom: 20rpx;
  -webkit-overflow-scrolling: touch;
}
/* H5 下隐藏横向滚动条，滑动仍是原生手感 */
.seg-scroll ::-webkit-scrollbar { display: none; width: 0; height: 0; }
.seg-inner { display: inline-flex; gap: 14rpx; padding: 2rpx; }
.seg-pill {
  display: inline-flex; align-items: center; gap: 8rpx;
  padding: 14rpx 30rpx; border-radius: 9999rpx;
  background: #fff; border: 1rpx solid var(--line2);
  color: var(--ink2); font-size: 25rpx; font-weight: 500;
  transition: background-color .18s ease, color .18s ease, border-color .18s ease;
}
.seg-pill.on {
  background: var(--brand); border-color: var(--brand);
  color: #fff; font-weight: 600;
}
.sp-emoji { font-size: 26rpx; }

/* 内容区：切换分段时的位移动画（向左滑出 → 从右侧进） */
.seg-body { min-height: 200rpx; will-change: transform, opacity; }
.slide-in-right { animation: slideInRight .26s cubic-bezier(.22, .61, .36, 1) both; }
.slide-in-left { animation: slideInLeft .26s cubic-bezier(.22, .61, .36, 1) both; }
@keyframes slideInRight {
  from { opacity: 0; transform: translateX(28px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-28px); }
  to { opacity: 1; transform: translateX(0); }
}

/* 顶部最近的日子 */
.cd-head { display: flex; align-items: center; justify-content: space-between; padding: 4rpx 6rpx 18rpx; }
.cd-total { font-size: 22rpx; color: var(--ink3); }
.cd-add { font-size: 24rpx; color: var(--brand-d); font-weight: 600; }
.st-right { display: flex; align-items: center; gap: 18rpx; }
.cal-add { font-size: 24rpx; color: var(--brand-d); font-weight: 600; }

.top-banner {
  display: flex; align-items: center; gap: 18rpx; padding: 26rpx 28rpx;
  border-radius: 24rpx; margin-bottom: 24rpx;
  background: var(--brand-l); border: 1rpx solid #F3CDB3;
}
.top-banner.state-today { background: linear-gradient(135deg, #D97742, #B85C2E); border: none; }
.top-banner.state-today .tb-name,
.top-banner.state-today .tb-date,
.top-banner.state-today .tb-days { color: #fff; }
.top-banner.state-urgent { background: var(--warn-l); border-color: #F0DCB4; }
.top-banner.state-normal { background: var(--ok-l); border-color: #CFE6DB; }
.top-banner.state-anniversary { background: var(--brand-l); border-color: #F3CDB3; }
.tb-emoji { font-size: 44rpx; }
.tb-main { flex: 1; display: flex; flex-direction: column; gap: 4rpx; }
.tb-name { font-size: 30rpx; font-weight: 700; color: var(--ink); }
.tb-date { font-size: 22rpx; color: var(--ink3); opacity: 0.9; }
.tb-days { font-size: 28rpx; font-weight: 700; color: var(--brand-d); }

/* 倒计时卡 */
.cd-card {
  display: flex; align-items: center; gap: 18rpx; background: #fff;
  border: 1rpx solid var(--line2); border-radius: 22rpx; padding: 24rpx;
  margin-bottom: 16rpx;
}
.cd-card.state-today { border-color: #F3CDB3; background: linear-gradient(180deg, #FFF8F2, #FFFFFF); }
.cd-card.state-anniversary { border-color: #EFDCC8; background: linear-gradient(180deg, #FFFBF6, #FFFFFF); }
.cd-card.state-past { opacity: 0.55; }
.cd-left { width: 66rpx; flex-shrink: 0; text-align: center; }
.cd-emoji { font-size: 40rpx; }
.cd-main { flex: 1; display: flex; flex-direction: column; gap: 6rpx; min-width: 0; }
.cd-title-row { display: flex; align-items: center; gap: 10rpx; }
.cd-name { font-size: 29rpx; font-weight: 600; color: var(--ink); }
.cd-pin { font-size: 20rpx; }
.cd-rule { font-size: 19rpx; color: var(--ink3); background: var(--bg); padding: 2rpx 10rpx; border-radius: 6rpx; }
.cd-date { font-size: 22rpx; color: var(--ink3); }
.cd-year { margin-left: 10rpx; color: var(--warn); }
.cd-lunar { margin-left: 10rpx; color: var(--brand-d); }
.cd-foot { display: flex; gap: 10rpx; margin-top: 4rpx; }
.cd-offset { font-size: 18rpx; color: var(--brand-d); background: var(--brand-l); padding: 2rpx 10rpx; border-radius: 6rpx; }
.cd-offset.muted { color: var(--ink3); background: var(--line2); }
.cd-right { display: flex; flex-direction: column; align-items: flex-end; gap: 6rpx; flex-shrink: 0; }
.cd-days { font-size: 26rpx; font-weight: 700; color: var(--brand-d); }
.cd-card.state-past .cd-days { color: var(--ink3); font-weight: 500; }
.cd-pin-btn { font-size: 18rpx; color: var(--ink3); }

.hint { text-align: center; font-size: 20rpx; color: var(--ink3); padding: 20rpx 0; }

.empty-btn {
  display: inline-block; margin-top: 28rpx; padding: 16rpx 40rpx;
  background: var(--brand); color: #fff; border-radius: 9999rpx; font-size: 26rpx;
}

/* 月历 */
.cal-nav { display: flex; align-items: center; justify-content: center; gap: 40rpx; margin-bottom: 20rpx; }
.cn-arrow { font-size: 40rpx; color: var(--ink2); padding: 0 16rpx; }
.cn-label { font-size: 30rpx; font-weight: 700; color: var(--ink); }

.calendar { background: #fff; border: 1rpx solid var(--line2); border-radius: 24rpx; padding: 20rpx 16rpx; }
.week-head { display: flex; }
.wh-item { flex: 1; text-align: center; font-size: 20rpx; color: var(--ink3); padding-bottom: 12rpx; }
.cal-grid { display: flex; flex-wrap: wrap; }
.cal-cell {
  width: 14.28%; height: 92rpx; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 4rpx; border-radius: 14rpx;
}
.cal-cell.blank { visibility: hidden; }
.cc-day { font-size: 26rpx; color: var(--ink); }
.cal-cell.today .cc-day { color: var(--brand-d); font-weight: 700; }
.cal-cell.has { background: var(--brand-l); }
.cal-cell.sel { background: var(--brand); }
.cal-cell.sel .cc-day { color: #fff; }
.cc-dots { display: flex; gap: 4rpx; }
.cc-dot { width: 8rpx; height: 8rpx; border-radius: 50%; background: var(--brand); }
.cal-cell.sel .cc-dot { background: #fff; }

.cal-list { margin-top: 26rpx; }
.cal-empty { text-align: center; font-size: 22rpx; color: var(--ink3); padding: 30rpx 0; }
.cal-item {
  display: flex; align-items: center; gap: 16rpx; background: #fff;
  border: 1rpx solid var(--line2); border-radius: 18rpx; padding: 20rpx 22rpx; margin-bottom: 12rpx;
}
.ci-emoji { font-size: 32rpx; }
.ci-main { flex: 1; display: flex; flex-direction: column; gap: 4rpx; }
.ci-name { font-size: 27rpx; font-weight: 600; color: var(--ink); }
.ci-sub { font-size: 20rpx; color: var(--ink3); }
.ci-arrow { font-size: 30rpx; color: var(--ink3); }

/* 旅游统计条 */
.trip-stats {
  display: flex; align-items: center; background: #fff; border: 1rpx solid var(--line2);
  border-radius: 22rpx; padding: 22rpx 24rpx; margin-bottom: 22rpx;
}
.ts-cell { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4rpx; }
.ts-num { font-size: 32rpx; font-weight: 700; color: var(--ink); }
.ts-label { font-size: 20rpx; color: var(--ink3); }
.ts-add {
  padding: 12rpx 22rpx; background: var(--brand-l); color: var(--brand-d);
  border-radius: 9999rpx; font-size: 23rpx; font-weight: 600;
}

/* 行程卡 */
.trip-card {
  display: flex; gap: 20rpx; background: #fff; border: 1rpx solid var(--line2);
  border-radius: 24rpx; padding: 18rpx; margin-bottom: 20rpx; overflow: hidden;
}
.tc-cover { width: 168rpx; height: 168rpx; border-radius: 18rpx; flex-shrink: 0; background: var(--line2); }
.tc-cover-empty { display: flex; align-items: center; justify-content: center; font-size: 52rpx; }
.tc-body { flex: 1; display: flex; flex-direction: column; gap: 8rpx; min-width: 0; padding: 4rpx 4rpx 0 0; }
.tc-top { display: flex; align-items: center; gap: 10rpx; }
.tc-title {
  font-size: 29rpx; font-weight: 600; color: var(--ink); flex: 1;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.tc-dest { font-size: 23rpx; color: var(--brand-d); }
.tc-date { font-size: 21rpx; color: var(--ink3); }
.tc-foot { display: flex; flex-wrap: wrap; gap: 10rpx; margin-top: auto; }
.tc-pill { font-size: 19rpx; color: var(--ink2); background: var(--bg); padding: 4rpx 12rpx; border-radius: 8rpx; }

/* 大事件 */
.ev-head { display: flex; align-items: center; justify-content: space-between; padding: 4rpx 6rpx 18rpx; }
.ev-total { font-size: 22rpx; color: var(--ink3); }
.ev-add { font-size: 24rpx; color: var(--brand-d); font-weight: 600; }
.year-block { margin-bottom: 28rpx; }
.year-label {
  font-size: 32rpx; font-weight: 800; color: var(--ink); padding: 0 6rpx 14rpx;
  display: flex; align-items: baseline; gap: 12rpx;
}
.year-count { font-size: 20rpx; font-weight: 400; color: var(--ink3); }
.ev-list { display: flex; flex-direction: column; gap: 14rpx; }
.ev-card {
  display: flex; align-items: center; gap: 18rpx; background: #fff;
  border: 1rpx solid var(--line2); border-radius: 20rpx; padding: 22rpx;
}
.ev-emoji { font-size: 36rpx; }
.ev-main { flex: 1; display: flex; flex-direction: column; gap: 4rpx; min-width: 0; }
.ev-title { font-size: 28rpx; font-weight: 600; color: var(--ink); }
.ev-sub { font-size: 20rpx; color: var(--ink3); }
.ev-content {
  font-size: 22rpx; color: var(--ink2); margin-top: 4rpx;
  overflow: hidden; text-overflow: ellipsis; display: -webkit-box;
  -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.ev-cover { width: 88rpx; height: 88rpx; border-radius: 14rpx; flex-shrink: 0; }
.ev-photo { font-size: 20rpx; color: var(--ink3); }

/* 表单 */
.f-area {
  width: 100%; min-height: 120rpx; font-size: 27rpx; color: var(--ink);
  background: var(--bg); border-radius: 14rpx; padding: 18rpx; box-sizing: border-box;
}
.cat-chips { display: flex; flex-wrap: wrap; gap: 12rpx; }
.cat-chip {
  padding: 10rpx 22rpx; border-radius: 9999rpx; font-size: 23rpx;
  background: var(--bg); border: 1rpx solid var(--line2); color: var(--ink2);
}
.cat-chip.on { background: var(--brand-l); border-color: #F3CDB3; color: var(--brand-d); font-weight: 600; }
.opt-chips { display: flex; flex-wrap: wrap; gap: 12rpx; }
.opt-chip {
  padding: 10rpx 22rpx; border-radius: 9999rpx; font-size: 23rpx;
  background: var(--bg); border: 1rpx solid var(--line2); color: var(--ink2);
}
.opt-chip.on { background: var(--brand-l); border-color: #F3CDB3; color: var(--brand-d); font-weight: 600; }
.emoji-chip { font-size: 28rpx; padding: 8rpx 18rpx; }
.rule-tip { display: block; font-size: 20rpx; color: var(--ink3); margin-top: 12rpx; line-height: 1.6; }

.pin-row { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 0; border-top: 1rpx solid var(--line2); }
.pin-label { font-size: 26rpx; color: var(--ink2); }
.pin-switch { font-size: 24rpx; color: var(--ink3); }
.pin-switch.on { color: var(--brand-d); font-weight: 600; }

.photo-block { padding: 20rpx 0; }
.photo-grid { display: flex; flex-wrap: wrap; gap: 14rpx; margin-top: 12rpx; }
.photo-cell { position: relative; width: 148rpx; height: 148rpx; border-radius: 14rpx; overflow: hidden; }
.photo-img { width: 100%; height: 100%; }
.photo-del {
  position: absolute; top: 0; right: 0; width: 40rpx; height: 40rpx; line-height: 40rpx;
  text-align: center; background: rgba(47,42,38,0.6); color: #fff; font-size: 20rpx;
  border-bottom-left-radius: 12rpx;
}
.photo-add {
  width: 148rpx; height: 148rpx; border-radius: 14rpx; border: 2rpx dashed var(--line);
  display: flex; align-items: center; justify-content: center;
  font-size: 46rpx; color: var(--ink3); background: var(--bg);
}
.submit { margin-top: 28rpx; }
.del-link { text-align: center; color: var(--danger); font-size: 24rpx; padding: 24rpx 0 0; }

@media (min-width: 768px) {
  .page { max-width: 720px; margin: 0 auto; }
}
</style>
