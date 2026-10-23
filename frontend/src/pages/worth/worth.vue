<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="值得记" subtitle="值得等的事，值得回头的日子" /><!-- #endif -->

    <!-- 顶部可横向滑动的分段：后续想加「纪念物 / 健康打卡」等大项，只需往 segments 里加一行 -->
    <scroll-view class="seg-scroll" scroll-x :scroll-into-view="scrollTo"
                 :show-scrollbar="false" scroll-with-animation enable-flex>
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

    <!-- ===== 日程（已移至「发现 → 日历」） ===== -->

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
        <view v-if="tripHasMore" class="load-more" @click="loadMoreTrips">
          <text v-if="tripLoadingMore">加载中…</text>
          <text v-else>上拉或点击加载更多</text>
        </view>
      </block>
    </block>

    <!-- ===== 待办 ===== -->
    <block v-else-if="tab === 'todo'">
      <!-- 快速添加：输入 + 回车/＋，日期用胶囊选 -->
      <view class="todo-add">
        <input class="ta-input" v-model="quickTitle" maxlength="60"
               placeholder="要做点什么？" confirm-type="done" @confirm="quickAdd" />
        <view :class="['ta-btn', quickTitle.trim() ? 'on' : '']" @click="quickAdd">＋</view>
      </view>
      <view class="quick-days">
        <view v-for="d in quickDayOptions" :key="d.label"
              :class="['qd-chip', quickDue === d.value ? 'on' : '']"
              @click="quickDue = d.value">{{ d.label }}</view>
        <picker mode="date" :value="quickCustomDate" @change="quickPickDate">
          <view :class="['qd-chip', quickCustom ? 'on' : '']">
            {{ quickCustom ? '📅 ' + quickDue.slice(5) : '📅 选日期' }}
          </view>
        </picker>
      </view>

      <view v-if="todoLoading && !todos.length" class="loading-text">牛马拉磨中…</view>

      <view v-else-if="!todos.length" class="empty">
        <text class="empty-title">清单是空的，活不是。</text>
        <text class="empty-sub">把脑子里悬着的事写下来，才能安心摸鱼。</text>
        <view class="empty-btn" @click="openTodo(null)">写第一条待办</view>
      </view>

      <block v-else>
        <view class="todo-sum">
          <text class="sum-open"><text class="sum-num">{{ todoStats.open }}</text> 项未完成</text>
          <text v-if="todoStats.today" class="sum-pill">今天 {{ todoStats.today }}</text>
          <text v-if="todoStats.overdue" class="sum-pill danger">逾期 {{ todoStats.overdue }}</text>
        </view>

        <view v-if="!todoStats.open" class="todo-allclear">
          <text class="tac-emoji">🎉</text>
          <text class="tac-text">清单清了，今天的牛马暂时自由。</text>
        </view>

        <view v-for="g in todoGroups" :key="g.key" class="todo-group">
          <view class="tg-head" @click="g.key === 'done' && (showDone = !showDone)">
            <text :class="['tg-dot', g.tone]"></text>
            <text class="tg-label">{{ g.label }}</text>
            <text class="tg-count">{{ g.count }}</text>
            <text v-if="g.key === 'done'" class="tg-fold">{{ showDone ? '收起' : '展开' }}</text>
          </view>
          <block v-if="g.key !== 'done' || showDone">
            <view v-for="t in g.items" :key="t.id" class="todo-row" :class="{ done: t.done }"
                  @click="openTodo(t)">
              <view :class="['tr-check', t.done ? 'on' : '']" @click.stop="toggleTodo(t)">
                <text v-if="t.done" class="tr-tick">✓</text>
              </view>
              <view class="tr-main">
                <text class="tr-title">{{ t.title }}</text>
                <view v-if="t.due_text || t.note" class="tr-meta">
                  <text v-if="t.due_text" :class="['tr-due', t.overdue ? 'over' : '']">{{ t.due_text }}</text>
                  <text v-if="t.note" class="tr-note">{{ t.note }}</text>
                </view>
              </view>
              <text v-if="t.important" class="tr-star">★</text>
            </view>
          </block>
        </view>
      </block>
    </block>

    <!-- ===== 健康（周期 / 亲密 / 睡眠） ===== -->
    <block v-else-if="tab === 'health'">
      <HealthPanel ref="healthRef" />
    </block>

    <!-- ===== 大事件 ===== -->
    <block v-else-if="tab === 'event'">
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

        <view v-if="eventHasMore" class="load-more" @click="loadMoreEvents">
          <text v-if="eventLoadingMore">加载中…</text>
          <text v-else>上拉或点击加载更多</text>
        </view>
      </block>
    </block>

    <!-- ===== 盘点 · 家庭资产 ===== -->
    <block v-else-if="tab === 'assets'">
      <AssetsPanel ref="assetsRef" />
    </block>
    </view>

    <view style="height: 180rpx"></view>

    <!-- ===== 日子表单（值得记与日历共用） ===== -->
    <CountdownSheet :visible="sheetVisible" :item="editingItem"
                    @close="sheetVisible = false"
                    @saved="onCountdownSaved"
                    @deleted="onCountdownSaved" />

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

    <!-- ===== 待办表单 ===== -->
    <view v-if="todoSheet" class="sheet-mask" @click="todoSheet = false">
      <view class="sheet" @click.stop>
        <view class="sheet-head">
          <text class="sheet-title">{{ editingTodoId ? '编辑待办' : '新建待办' }}</text>
          <text class="sheet-close" @click="todoSheet = false">✕</text>
        </view>

        <view class="field">
          <text class="f-label">要做什么</text>
          <input class="f-input" v-model="todoForm.title" maxlength="60"
                 placeholder="例如：把报销单交了" />
        </view>

        <view class="field">
          <text class="f-label">哪天做（可不填）</text>
          <view class="f-row">
            <picker class="date-picker" mode="date" :value="todoForm.due_date || today"
                    @change="e => todoForm.due_date = e.detail.value">
              <view class="f-input">{{ todoForm.due_date || '不设日期' }}</view>
            </picker>
            <text v-if="todoForm.due_date" class="clear-date" @click="todoForm.due_date = ''">清除</text>
          </view>
        </view>

        <view class="field">
          <text class="f-label">备注（可不填）</text>
          <textarea class="f-area" v-model="todoForm.note" maxlength="200"
                    placeholder="补充点细节…" auto-height />
        </view>

        <view class="pin-row">
          <text class="pin-label">标为重要（同一天里排前面）</text>
          <text :class="['pin-switch', todoForm.important ? 'on' : '']"
                @click="todoForm.important = !todoForm.important">
            {{ todoForm.important ? '★ 已标重要' : '☆ 标为重要' }}
          </text>
        </view>

        <button class="btn-primary submit" :loading="saving" @click="saveTodo">保存</button>
        <view v-if="editingTodoId" class="del-link" @click="removeTodo">删除这条</view>
      </view>
    </view>

    <BackTop :scroll-top="pageScroll" />

    <!-- #ifdef H5 --><CustomTab current="/pages/worth/worth" /><!-- #endif -->
  </view>
</template>

<script setup>
import { computed, nextTick, reactive, ref } from 'vue'
import { onShow, onPullDownRefresh, onReachBottom, onPageScroll } from '@dcloudio/uni-app'
import {
  apiCountdowns, apiUpdateCountdown,
  apiTrips, apiCreateTrip, apiUpdateTrip,
  apiTodos, apiCreateTodo, apiUpdateTodo, apiDeleteTodo,
  apiEvent, apiEvents, apiCreateEvent, apiUpdateEvent, apiDeleteEvent, apiUploadMedia,
} from '@/api'
import { mediaUrl } from '@/utils/config'
import WebLayout from '@/components/WebLayout.vue'
import CustomTab from '@/components/CustomTab.vue'
import BackTop from '@/components/BackTop.vue'
import CountdownSheet from '@/components/CountdownSheet.vue'
import HealthPanel from '@/components/HealthPanel.vue'
import AssetsPanel from '@/components/AssetsPanel.vue'

/** 顶部大项。新增模块时在这里加一项，并在下方加对应的内容块即可。 */
const segments = [
  { key: 'health', label: '健康', emoji: '💪' },
  { key: 'todo', label: '待办', emoji: '✅' },
  { key: 'countdown', label: '日子', emoji: '🎯' },
  { key: 'trip', label: '旅游', emoji: '🧳' },
  { key: 'event', label: '大事件', emoji: '🎉' },
  { key: 'assets', label: '盘点', emoji: '🏦' },
]

const tab = ref('health')
const scrollTo = ref('')
const pageScroll = ref(0)
const healthRef = ref(null)
const assetsRef = ref(null)
const cdLoading = ref(false)
const tripLoading = ref(false)
const eventLoading = ref(false)
const saving = ref(false)

// ---- 日子 ----
const items = ref([])
const sheetVisible = ref(false)
const editingItem = ref(null)
/** 本地日期（不用 toISOString：东八区凌晨会算成前一天） */
function localDate(offset = 0) {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}
function shiftDate(iso, days) {
  const d = new Date(iso + 'T00:00:00')
  d.setDate(d.getDate() + days)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}
/** 用 ref：tabBar 页面会常驻，跨过零点后 onShow 要能把「今天」推到新的一天 */
const today = ref(localDate())

const topItem = computed(() => {
  const active = items.value.filter(i => !i.is_past)
  const pinned = active.filter(i => i.pinned)
  return (pinned.length ? pinned : active).slice().sort((a, b) => a.days_left - b.days_left)[0] || null
})

// ---- 旅游 ----
const trips = ref([])
const tripMeta = reactive({ trip_count: 0, city_count: 0, photo_limit: 20 })
const tripPage = ref(1)
const tripHasMore = ref(false)
const tripLoadingMore = ref(false)
const tripSheet = ref(false)
const editingTripId = ref(null)
const photoLimit = computed(() => tripMeta.photo_limit || 20)
const totalPhotos = computed(() => trips.value.reduce((a, t) => a + (t.photo_count || 0), 0))
const tripForm = reactive({
  destinations: '', start_date: today.value, end_date: today.value, companions: '',
  cost: '', content: '', photos: [],
})

// ---- 待办 ----
const todos = ref([])
const todoLoading = ref(false)
const todoStats = reactive({ open: 0, done: 0, today: 0, overdue: 0, total: 0 })
const quickTitle = ref('')
const quickDue = ref(today.value)
const todoSheet = ref(false)
const editingTodoId = ref(null)
const showDone = ref(false)
const todoForm = reactive({ title: '', due_date: '', note: '', important: false })

/** 以 today 为基准偏移，跨零点后胶囊能跟着重算（computed 无依赖会永久缓存） */
const quickDayOptions = computed(() => [
  { label: '今天', value: today.value },
  { label: '明天', value: shiftDate(today.value, 1) },
  { label: '不设日期', value: '' },
])
const quickCustom = computed(() =>
  !!quickDue.value && !quickDayOptions.value.some(d => d.value === quickDue.value))
const quickCustomDate = computed(() => quickDue.value || today.value)

/** 分组：逾期 → 今天 → 明天 → 以后 → 没定日子 → 已完成（可折叠） */
const todoGroups = computed(() => {
  const buckets = { overdue: [], today: [], tomorrow: [], later: [], nodate: [] }
  for (const t of todos.value) {
    if (!t.done) buckets[t.bucket].push(t)
  }
  const meta = [
    ['overdue', '逾期', 'danger'],
    ['today', '今天', 'brand'],
    ['tomorrow', '明天', 'info'],
    ['later', '以后', 'info'],
    ['nodate', '没定日子', 'muted'],
  ]
  const groups = meta
    .filter(([key]) => buckets[key].length)
    .map(([key, label, tone]) => ({
      key, label, tone, items: buckets[key], count: buckets[key].length,
    }))
  const doneItems = todos.value.filter(t => t.done)
  if (doneItems.length) {
    groups.push({
      key: 'done', label: '已完成', tone: 'done',
      items: doneItems, count: todoStats.done || doneItems.length,
    })
  }
  return groups
})

/** 给一条待办补上「分组 + 人话日期」，模板只负责展示 */
function decorateTodo(t) {
  let bucket = 'nodate'
  let dueText = ''
  let overdue = false
  if (t.due_date) {
    const diff = Math.round(
      (new Date(t.due_date + 'T00:00:00') - new Date(localDate() + 'T00:00:00')) / 86400000)
    if (t.done) {
      dueText = `${Number(t.due_date.slice(5, 7))}月${Number(t.due_date.slice(8, 10))}日`
    } else if (diff < 0) {
      bucket = 'overdue'
      overdue = true
      dueText = `逾期 ${-diff} 天`
    } else if (diff === 0) {
      bucket = 'today'
      dueText = '今天'
    } else if (diff === 1) {
      bucket = 'tomorrow'
      dueText = '明天'
    } else {
      bucket = 'later'
      dueText = diff === 2 ? '后天' : `${Number(t.due_date.slice(5, 7))}月${Number(t.due_date.slice(8, 10))}日`
    }
  }
  return { ...t, bucket, due_text: dueText, overdue }
}

// ---- 大事件 ----
const eventGroups = ref([])
const eventTotal = ref(0)
const eventPage = ref(1)
const eventHasMore = ref(false)
const eventLoadingMore = ref(false)
const eventCats = ref([])
const eventPhotoLimit = ref(9)
const eventSheet = ref(false)
const editingEventId = ref(null)
const eventForm = reactive({
  title: '', event_date: today.value, category: '里程碑', emoji: '🏆',
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
  return sheetVisible.value || tripSheet.value || todoSheet.value || eventSheet.value
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
const loaded = reactive({ countdown: false, trip: false, todo: false, event: false })
const loadedAt = reactive({ countdown: 0, trip: 0, todo: 0, event: 0 })
const CACHE_TTL = 30000

/** 同一接口并发只发一次（onShow、切分段、预取可能同时触发） */
const inflight = new Map()
function once(key, fn) {
  if (inflight.has(key)) return inflight.get(key)
  const p = fn().finally(() => {
    // 只清掉自己：强制刷新时这个 key 可能已经被更新的请求占用
    if (inflight.get(key) === p) inflight.delete(key)
  })
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

function loadTrips() {
  tripPage.value = 1
  return once('trip', async () => {
    tripLoading.value = true
    try {
      const data = await apiTrips({ page: 1, page_size: 20 })
      trips.value = data.items || []
      tripHasMore.value = !!data.has_more
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

/** 滑到底/点按钮时追加下一页；分页中写操作仍走 loadTrips 全量重取 */
async function loadMoreTrips() {
  if (!tripHasMore.value || tripLoadingMore.value || tripLoading.value) return
  tripLoadingMore.value = true
  try {
    const data = await apiTrips({ page: tripPage.value + 1, page_size: 20 })
    const more = data.items || []
    const seen = new Set(trips.value.map(t => t.id))
    trips.value = trips.value.concat(more.filter(t => !seen.has(t.id)))
    tripPage.value += 1
    tripHasMore.value = !!data.has_more
  } catch (e) { /* toast 已统一 */ } finally {
    tripLoadingMore.value = false
  }
}

/** 每次请求的序号：增删改后强制重拉时，避免上一个更早的请求把新结果覆盖掉 */
let todoSeq = 0

function loadTodos(force = false) {
  // 写操作必须 force：once 会复用「写之前发出、还没回来」的旧请求，列表就会少一条
  if (force) inflight.delete('todo')
  return once('todo', async () => {
    const seq = ++todoSeq
    todoLoading.value = true
    try {
      const data = await apiTodos()
      if (seq !== todoSeq) return
      todos.value = (data.items || []).map(decorateTodo)
      Object.assign(todoStats, data.stats || {})
      loaded.todo = true
      loadedAt.todo = Date.now()
    } finally {
      if (seq === todoSeq) todoLoading.value = false
    }
  })
}

function loadEvents() {
  eventPage.value = 1
  return once('event', async () => {
    eventLoading.value = true
    try {
      const data = await apiEvents({ page: 1, page_size: 20 })
      eventGroups.value = data.groups || []
      eventTotal.value = data.total || 0
      eventHasMore.value = !!data.has_more
      eventCats.value = data.categories || []
      eventPhotoLimit.value = data.photo_limit || 9
      loaded.event = true
      loadedAt.event = Date.now()
    } finally {
      eventLoading.value = false
    }
  })
}

/** 同一年可能跨页，追加时按年份合并，避免出现两个「2026」分组 */
async function loadMoreEvents() {
  if (!eventHasMore.value || eventLoadingMore.value || eventLoading.value) return
  eventLoadingMore.value = true
  try {
    const data = await apiEvents({ page: eventPage.value + 1, page_size: 20 })
    const merged = eventGroups.value.map(g => ({ ...g, items: [...g.items] }))
    for (const g of data.groups || []) {
      const hit = merged.find(x => x.year === g.year)
      if (hit) {
        const seen = new Set(hit.items.map(e => e.id))
        hit.items = hit.items.concat(g.items.filter(e => !seen.has(e.id)))
        hit.count = hit.items.length
      } else {
        merged.push({ ...g, items: [...g.items] })
      }
    }
    merged.sort((a, b) => Number(b.year) - Number(a.year))
    eventGroups.value = merged
    eventPage.value += 1
    eventHasMore.value = !!data.has_more
  } catch (e) { /* toast 已统一 */ } finally {
    eventLoadingMore.value = false
  }
}

/** 切到某分段时按需取数：有缓存就不再打扰用户 */
function ensureTabData(key, force = false) {
  const fresh = loaded[key] && Date.now() - loadedAt[key] < CACHE_TTL
  if (!force && fresh) return
  if (key === 'countdown') return loadCountdowns()
  if (key === 'trip') return loadTrips()
  if (key === 'todo') return loadTodos()
  if (key === 'event') return loadEvents()
}

/** 首屏只等当前分段，其余分段空闲时预取，滑动过去就是现成的 */
function refresh(force = true) {
  if (tab.value === 'health') {
    // 健康面板自己管数据，页面刷新时让它重取当前分段
    if (force) healthRef.value && healthRef.value.reload()
    return
  }
  ensureTabData(tab.value, force)
  if (tab.value !== 'trip' && loaded.trip) loadTrips()
  if (tab.value !== 'todo' && loaded.todo) loadTodos()
  if (tab.value !== 'event' && loaded.event) loadEvents()
}

function prefetch() {
  setTimeout(() => {
    if (!loaded.trip) loadTrips()
    if (!loaded.todo) loadTodos()
    if (!loaded.event) loadEvents()
  }, 350)
}

// ---------- 日子 ----------
function openSheet(cd) {
  editingItem.value = cd || null
  sheetVisible.value = true
}

function onCountdownSaved() {
  sheetVisible.value = false
  loadCountdowns()
}

async function togglePin(cd) {
  try {
    await apiUpdateCountdown(cd.id, { pinned: !cd.pinned })
    await loadCountdowns()
  } catch (e) { /* toast 已统一 */ }
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
    tripForm.start_date = today.value
    tripForm.end_date = today.value
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

// ---------- 待办 ----------
async function quickAdd() {
  const title = quickTitle.value.trim()
  if (!title) return uni.showToast({ title: '先写要做什么', icon: 'none' })
  try {
    await apiCreateTodo({ title, due_date: quickDue.value || null })
    quickTitle.value = ''
    await loadTodos(true)
  } catch (e) { /* toast 已统一 */ }
}

function quickPickDate(e) {
  quickDue.value = e.detail.value
}

function openTodo(t) {
  editingTodoId.value = t ? t.id : null
  todoForm.title = t ? t.title : ''
  todoForm.due_date = t ? (t.due_date || '') : (quickDue.value || '')
  todoForm.note = t ? (t.note || '') : ''
  todoForm.important = t ? !!t.important : false
  todoSheet.value = true
}

async function toggleTodo(t) {
  try {
    await apiUpdateTodo(t.id, { done: !t.done })
    await loadTodos(true)
  } catch (e) { /* toast 已统一 */ }
}

async function saveTodo() {
  const title = todoForm.title.trim()
  if (!title) return uni.showToast({ title: '写点什么吧', icon: 'none' })
  saving.value = true
  const payload = {
    title,
    due_date: todoForm.due_date || null,
    note: todoForm.note.trim() || null,
    important: todoForm.important,
  }
  try {
    if (editingTodoId.value) await apiUpdateTodo(editingTodoId.value, payload)
    else await apiCreateTodo(payload)
    todoSheet.value = false
    await loadTodos(true)
  } catch (e) { /* toast 已统一 */ } finally {
    saving.value = false
  }
}

function removeTodo() {
  if (!editingTodoId.value) return
  const id = editingTodoId.value
  uni.showModal({
    title: '删掉这条？',
    content: '待办没有回收站，删了就是删了。',
    confirmText: '删掉',
    confirmColor: '#C0555F',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await apiDeleteTodo(id)
        todoSheet.value = false
        await loadTodos(true)
      } catch (e) { /* toast 已统一 */ }
    },
  })
}

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
    eventForm.event_date = today.value
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
  // 常驻页面跨零点：把「今天」和待办的快速默认日期推进到新的一天
  const d = localDate()
  if (d !== today.value) {
    if (quickDue.value === today.value) quickDue.value = d
    today.value = d
  }
  refresh()
  applyPendingTab()
  prefetch()
})
onPullDownRefresh(async () => {
  const guard = setTimeout(() => uni.stopPullDownRefresh(), 8000)
  try {
    const jobs = [loadCountdowns(), loadTrips(), loadTodos(), loadEvents()]
    if (healthRef.value) jobs.push(healthRef.value.reload())
    if (assetsRef.value) jobs.push(assetsRef.value.reload())
    await Promise.all(jobs)
  } finally {
    clearTimeout(guard)
    uni.stopPullDownRefresh()
  }
})
// 触底加载：旅游/大事件各自追加下一页，健康面板自己决定加载哪一段
onPageScroll((e) => { pageScroll.value = e.scrollTop })
onReachBottom(() => {
  if (tab.value === 'trip') return loadMoreTrips()
  if (tab.value === 'event') return loadMoreEvents()
  if (tab.value === 'health' && healthRef.value) return healthRef.value.loadMore()
})
</script>

<style scoped>
.page { padding: 24rpx; }
.load-more {
  text-align: center; font-size: 22rpx; color: var(--ink3);
  padding: 20rpx 0 6rpx;
}

/* 顶部可滑动分段 */
.seg-scroll {
  width: 100%; white-space: nowrap; margin-bottom: 20rpx;
  -webkit-overflow-scrolling: touch;
}
/* H5 下隐藏横向滚动条，滑动仍是原生手感 */
.seg-scroll ::-webkit-scrollbar { display: none; width: 0; height: 0; }
/* H5 的 scroll-view 内层容器默认 block 且宽度被压到可视宽，胶囊会被挤成多行；
   这里让它按内容真实宽度铺开，超出的部分交给 scroll-view 横向滚动 */
.seg-scroll :deep(.uni-scroll-view-content) {
  display: inline-block; width: max-content; min-width: 100%;
  white-space: nowrap;
}
.seg-inner {
  display: inline-flex; align-items: center; gap: 12rpx;
  padding: 2rpx 24rpx 2rpx 2rpx;     /* 右侧留白，最后一个胶囊不贴边 */
}
.seg-pill {
  display: inline-flex; align-items: center; gap: 8rpx;
  flex: 0 0 auto;                    /* 关键：屏幕再窄也不压缩胶囊，改为横向滚动 */
  white-space: nowrap;
  padding: 13rpx 26rpx; border-radius: 9999rpx;
  background: #fff; border: 1rpx solid var(--line2);
  color: var(--ink2); font-size: 24rpx; font-weight: 500;
  line-height: 1.2;
  transition: background-color .18s ease, color .18s ease, border-color .18s ease;
}
.seg-pill.on {
  background: var(--brand); border-color: var(--brand);
  color: #fff; font-weight: 600;
}
.sp-emoji { font-size: 25rpx; line-height: 1.2; }
.sp-label { white-space: nowrap; }

/* 小屏（iPhone SE 这类 320~375）再收一点，五个分段尽量不用滑也能看全 */
@media (max-width: 380px) {
  .seg-inner { gap: 10rpx; }
  .seg-pill { padding: 12rpx 20rpx; font-size: 23rpx; gap: 6rpx; }
  .sp-emoji { font-size: 23rpx; }
}

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
.cat-chip.on { background: var(--brand-sel); border-color: var(--brand-bd); color: var(--brand-d); font-weight: 600; }
.opt-chips { display: flex; flex-wrap: wrap; gap: 12rpx; }
.opt-chip {
  padding: 10rpx 22rpx; border-radius: 9999rpx; font-size: 23rpx;
  background: var(--bg); border: 1rpx solid var(--line2); color: var(--ink2);
}
.opt-chip.on { background: var(--brand-sel); border-color: var(--brand-bd); color: var(--brand-d); font-weight: 600; }
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
.date-picker { flex: 1; }
.clear-date { font-size: 23rpx; color: var(--ink3); padding-left: 20rpx; }

/* 待办 */
.todo-add {
  display: flex; align-items: center; gap: 14rpx; background: #fff;
  border: 1rpx solid var(--line2); border-radius: 9999rpx;
  padding: 10rpx 10rpx 10rpx 30rpx; margin-bottom: 16rpx;
}
.ta-input { flex: 1; font-size: 27rpx; height: 56rpx; color: var(--ink); }
.ta-btn {
  width: 64rpx; height: 64rpx; flex-shrink: 0; border-radius: 9999rpx;
  background: var(--line2); color: var(--ink3);
  display: flex; align-items: center; justify-content: center;
  font-size: 34rpx; transition: background-color .16s ease, color .16s ease;
}
.ta-btn.on { background: var(--brand); color: #fff; }

.quick-days { display: flex; flex-wrap: wrap; gap: 12rpx; margin-bottom: 24rpx; }
.qd-chip {
  padding: 10rpx 22rpx; border-radius: 9999rpx; background: #fff;
  border: 1rpx solid var(--line2); color: var(--ink2); font-size: 22rpx;
}
.qd-chip.on { background: var(--brand-sel); border-color: var(--brand-bd); color: var(--brand-d); font-weight: 600; }

.todo-sum { display: flex; flex-wrap: wrap; align-items: center; gap: 14rpx; padding: 0 6rpx 18rpx; }
.sum-open { font-size: 22rpx; color: var(--ink3); }
.sum-num { font-size: 26rpx; font-weight: 700; color: var(--ink); }
.sum-pill {
  font-size: 19rpx; color: var(--ink2); background: var(--line2);
  padding: 3rpx 12rpx; border-radius: 8rpx;
}
.sum-pill.danger { color: var(--danger); background: var(--danger-l); }

.todo-allclear {
  display: flex; align-items: center; gap: 14rpx; padding: 26rpx 28rpx;
  background: var(--ok-l); border: 1rpx solid #CFE6DB; border-radius: 20rpx;
  margin-bottom: 24rpx;
}
.tac-emoji { font-size: 34rpx; }
.tac-text { font-size: 24rpx; color: var(--ok); }

.todo-group { margin-bottom: 24rpx; }
.tg-head { display: flex; align-items: center; gap: 10rpx; padding: 0 6rpx 12rpx; }
.tg-dot { width: 12rpx; height: 12rpx; border-radius: 50%; background: var(--ink3); }
.tg-dot.overdue { background: var(--danger); }
.tg-dot.today { background: var(--brand); }
.tg-dot.tomorrow { background: var(--info); }
.tg-dot.later { background: #B7C7D6; }
.tg-dot.done { background: var(--ok); }
.tg-label { font-size: 24rpx; font-weight: 600; color: var(--ink2); }
.tg-count { font-size: 20rpx; color: var(--ink3); }
.tg-fold { margin-left: auto; font-size: 20rpx; color: var(--ink3); padding: 4rpx 6rpx; }

.todo-row {
  display: flex; align-items: flex-start; gap: 16rpx; background: #fff;
  border: 1rpx solid var(--line2); border-radius: 18rpx;
  padding: 22rpx; margin-bottom: 12rpx;
}
.todo-row.done { opacity: 0.72; }
.tr-check {
  width: 38rpx; height: 38rpx; border-radius: 50%; border: 2rpx solid var(--line);
  flex-shrink: 0; margin-top: 4rpx;
  display: flex; align-items: center; justify-content: center;
  transition: background-color .16s ease, border-color .16s ease;
}
.tr-check.on { background: var(--ok); border-color: var(--ok); }
.tr-tick { color: #fff; font-size: 24rpx; line-height: 1; }
.tr-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6rpx; }
.tr-title { font-size: 28rpx; line-height: 1.5; color: var(--ink); word-break: break-all; }
.todo-row.done .tr-title { color: var(--ink3); text-decoration: line-through; }
.tr-meta { display: flex; align-items: center; gap: 12rpx; min-width: 0; }
.tr-due {
  font-size: 19rpx; color: var(--ink3); background: var(--line2);
  padding: 2rpx 10rpx; border-radius: 6rpx; flex-shrink: 0;
}
.tr-due.over { color: var(--danger); background: var(--danger-l); }
.tr-note {
  flex: 1; min-width: 0; font-size: 20rpx; color: var(--ink3);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.tr-star { font-size: 24rpx; color: var(--gold); flex-shrink: 0; padding-left: 6rpx; }

@media (min-width: 768px) {
  .page { max-width: 720px; margin: 0 auto; }
}
</style>
