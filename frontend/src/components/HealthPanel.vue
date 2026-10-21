<template>
  <view class="hp">
    <!-- 四段：月历 / 周期 / 亲密 / 睡眠 -->
    <view class="hp-seg">
      <view v-for="s in sections" :key="s.key"
            :class="['hs-item', sec === s.key ? 'on' : '']"
            @click="switchSection(s.key)">
        <text class="hs-emoji">{{ s.emoji }}</text>
        <text class="hs-label">{{ s.label }}</text>
      </view>
    </view>

    <!-- ================= 月历总览 ================= -->
    <block v-if="sec === 'calendar'">
      <view :class="['cal-card', calLoading ? 'is-loading' : '']">
        <view class="cal-head">
          <view class="cal-nav" @click="goMonth(-1)">‹</view>
          <text class="cal-title">{{ monthLabel }}</text>
          <view class="cal-nav" @click="goMonth(1)">›</view>
          <text v-if="calMonth !== thisMonth" class="cal-back" @click="backToToday">回到本月</text>
        </view>

        <view class="cal-week">
          <text v-for="w in weeks" :key="w" class="cw">{{ w }}</text>
        </view>

        <view class="cal-grid">
          <view v-for="(c, i) in calCells" :key="i"
                :class="['cal-cell', c && c.selected ? 'sel' : '', c && c.fertile ? 'fertile' : '']"
                @click="c && selectDay(c.date)">
            <block v-if="c">
              <text :class="['cal-day', c.today ? 'today' : '']">{{ c.day }}</text>
              <view class="cal-marks">
                <view v-if="c.cycle" class="mk mk-period"></view>
                <view v-else-if="c.predictedPeriod" class="mk mk-period pre"></view>
                <view v-if="c.ovulation" class="mk mk-ovu"></view>
                <view v-if="c.intimacy" class="mk mk-intimacy"></view>
                <view v-if="c.sleep" :class="['mk', 'mk-sleep', sleepTone(c.sleep.quality)]"></view>
              </view>
            </block>
          </view>
        </view>

        <view class="cal-legend">
          <view class="lg"><view class="mk mk-period"></view><text>经期</text></view>
          <view class="lg"><view class="mk mk-period pre"></view><text>预计</text></view>
          <view class="lg"><view class="mk mk-ovu"></view><text>排卵</text></view>
          <view class="lg"><view class="mk mk-intimacy"></view><text>亲密</text></view>
          <view class="lg"><view class="mk mk-sleep good"></view><text>睡眠</text></view>
          <view class="lg"><view class="lg-fertile"></view><text>易孕</text></view>
        </view>
      </view>

      <view class="cal-sum">
        <text class="cs-title">{{ calMonth === thisMonth ? '本月' : '当月' }}</text>
        <text class="cs-item">经期 {{ calStats.cycle_days }} 天</text>
        <text class="cs-item">亲密 {{ calStats.intimacy_count }} 次</text>
        <text class="cs-item">睡眠 {{ calStats.sleep_count }} 天</text>
        <text v-if="calStats.sleep_count" class="cs-item">平均 {{ minutesText(calStats.avg_minutes) }}</text>
        <text v-if="calData.predicted" class="cs-item">
          下次预计 {{ shortDate(calData.predicted.period_start) }}
        </text>
      </view>

      <!-- 选中日期的当天明细 -->
      <view v-if="selectedCell" class="day-card">
        <view class="dc-head">
          <text class="dc-date">{{ selectedCell.date.slice(5) }} {{ selectedWeekday }}</text>
          <text v-if="selectedCell.today" class="dc-today">今天</text>
        </view>

        <view v-if="!dayHasRecords" class="dc-empty">这一天还没记录。</view>

        <block v-else>
          <view v-if="selectedCell.cycle" class="dc-row" @click="openCycle(selectedCell.cycle)">
            <text class="dc-icon">🩸</text>
            <view class="dc-main">
              <text class="dc-title">经期第 {{ selectedCell.cycle.day_index }} 天 · {{ selectedCell.cycle.flow_label }}</text>
              <text v-if="selectedCell.cycle.symptoms.length" class="dc-sub">
                {{ selectedCell.cycle.symptoms.join(' · ') }}
              </text>
              <text v-if="selectedCell.cycle.note" class="dc-sub">{{ selectedCell.cycle.note }}</text>
            </view>
            <text class="dc-edit">编辑</text>
          </view>

          <view v-for="it in (selectedCell.intimacy ? selectedCell.intimacy.items : [])"
                :key="it.id" class="dc-row" @click="openIntimacy(it)">
            <text class="dc-icon">💞</text>
            <view class="dc-main">
              <text class="dc-title">
                {{ it.kind_label }}{{ it.kind === 'self' ? '' : ' · ' + it.protection_label }}
                <text v-if="it.happen_time" class="dc-time">{{ it.happen_time }}</text>
              </text>
              <text v-if="it.note" class="dc-sub">{{ it.note }}</text>
            </view>
            <text class="dc-edit">编辑</text>
          </view>

          <view v-if="selectedCell.sleep" class="dc-row" @click="openSleep(selectedCell.sleep)">
            <text class="dc-icon">😴</text>
            <view class="dc-main">
              <text class="dc-title">{{ selectedCell.sleep.hours_text }} · {{ selectedCell.sleep.quality_label }}</text>
              <text class="dc-sub">{{ selectedCell.sleep.bed_time }} → {{ selectedCell.sleep.wake_time }}</text>
            </view>
            <text class="dc-edit">编辑</text>
          </view>
        </block>

        <view v-if="canAddOnSelected" class="dc-add">
          <text class="dca" @click="openCycle(null, selectedCell.date)">＋ 经期</text>
          <text class="dca" @click="openIntimacy(null, selectedCell.date)">＋ 亲密</text>
          <text class="dca" @click="openSleep(null, selectedCell.date)">＋ 睡眠</text>
        </view>
        <view v-else class="dc-future">未来的日期只能看预测，当天到了再记录。</view>
      </view>

      <view v-else class="cal-hint">点某一天看当天明细；完整列表在下方「周期 / 亲密 / 睡眠」里。</view>
    </block>

    <!-- ================= 周期 ================= -->
    <block v-else-if="sec === 'cycle'">
      <view v-if="loading.cycle && !cycle" class="loading-text">牛马拉磨中…</view>

      <view v-else-if="!cycle || !cycle.has_data" class="empty">
        <text class="empty-title">先记下最近一次经期。</text>
        <text class="empty-sub">之后每次开始、结束记一笔，就能自动推算周期和易孕期。</text>
        <view class="empty-btn" @click="openCycle()">记这次经期</view>
      </view>

      <block v-else>
        <view :class="['cy-hero', 'phase-' + cycle.phase]">
          <view class="ch-top">
            <text class="ch-phase">{{ cycle.phase_label }}</text>
            <text v-if="cycle.ongoing" class="ch-ongoing">进行中</text>
          </view>
          <text class="ch-main">
            {{ cycle.phase === 'period' ? '周期第 ' + cycle.cycle_day + ' 天' :
               cycle.phase === 'late' ? '比预计晚了 ' + cycle.late_days + ' 天' :
               '距下次预计 ' + cycle.days_left + ' 天' }}
          </text>
          <view class="ch-cells">
            <view class="ch-cell">
              <text class="cc-num">{{ cycle.cycle_len }}</text><text class="cc-label">平均周期</text>
            </view>
            <view class="ch-cell">
              <text class="cc-num">{{ cycle.period_len }}</text><text class="cc-label">经期长度</text>
            </view>
            <view class="ch-cell">
              <text class="cc-num">{{ shortDate(cycle.next_start) }}</text><text class="cc-label">下次预计</text>
            </view>
          </view>
        </view>

        <view class="cy-tip">{{ cycle.tip }}</view>

        <view class="cy-fertile">
          <text class="cf-label">易孕期（预计）</text>
          <text class="cf-value">{{ shortDate(cycle.fertile_start) }} - {{ shortDate(cycle.fertile_end) }}</text>
          <text class="cf-sub">排卵日约 {{ shortDate(cycle.ovulation) }}</text>
        </view>

        <view class="hp-actions">
          <view class="hp-add" @click="openCycle(cycle.ongoing ? cycle.history[0] : null)">
            {{ cycle.ongoing ? '更新这次经期' : '＋ 记录经期' }}
          </view>
        </view>

        <view class="hp-list">
          <view v-for="c in cycle.history" :key="c.id" class="cy-row" @click="openCycle(c)">
            <view class="cy-left">
              <text class="cy-date">{{ c.start_date.slice(5) }}</text>
              <text class="cy-year">{{ c.start_date.slice(0, 4) }}</text>
            </view>
            <view class="cy-main">
              <view class="cy-title">
                <text class="cy-days">{{ c.ongoing ? '进行中' : (c.days || 1) + ' 天' }}</text>
                <text class="chip chip-countdown">{{ c.flow_label }}</text>
                <text v-for="s in c.symptoms" :key="s" class="cy-sym">{{ s }}</text>
              </view>
              <text v-if="c.note" class="cy-note">{{ c.note }}</text>
            </view>
          </view>
        </view>
        <view class="hp-note">预测只作参考，不能替代医疗建议。</view>
      </block>
    </block>

    <!-- ================= 亲密 ================= -->
    <block v-else-if="sec === 'intimacy'">
      <view class="privacy-bar">🔒 只有你自己能看到，不会出现在手札流里</view>

      <view class="im-stats">
        <view class="is-cell">
          <text class="is-num">{{ intimacy.stats.month_count || 0 }}</text>
          <text class="is-label">本月</text>
        </view>
        <view class="is-cell">
          <text class="is-num">{{ intimacy.stats.recent_count || 0 }}</text>
          <text class="is-label">近 30 天</text>
        </view>
        <view class="is-cell">
          <text class="is-num">{{ intimacy.stats.days_since === null || intimacy.stats.days_since === undefined ? '—' : intimacy.stats.days_since }}</text>
          <text class="is-label">距上次（天）</text>
        </view>
      </view>

      <view class="im-kinds">
        <text class="ik-item">自己 {{ intimacy.stats.by_kind ? intimacy.stats.by_kind.self : 0 }}</text>
        <text class="ik-item">两人 {{ intimacy.stats.by_kind ? intimacy.stats.by_kind.partner : 0 }}</text>
        <text class="ik-item">多人 {{ intimacy.stats.by_kind ? intimacy.stats.by_kind.multi : 0 }}</text>
        <text class="ik-hint">近 30 天</text>
      </view>

      <view class="hp-actions">
        <view class="hp-add" @click="openIntimacy()">＋ 记一次</view>
      </view>

      <view v-if="loading.intimacy && !intimacy.items.length" class="loading-text">牛马拉磨中…</view>

      <view v-else-if="!intimacy.items.length" class="empty">
        <text class="empty-title">还没有记录。</text>
        <text class="empty-sub">记下来，方便回看频率和避孕方式。</text>
      </view>

      <view v-else class="hp-list">
        <view v-for="i in intimacy.items" :key="i.id" class="im-row" @click="openIntimacy(i)">
          <view class="im-date">
            <text class="im-day">{{ i.happen_date.slice(5) }}</text>
            <text v-if="i.happen_time" class="im-time">{{ i.happen_time }}</text>
          </view>
          <view class="im-main">
            <view class="im-tags">
              <text :class="['chip', i.kind === 'self' ? 'chip-asset' : 'chip-ledger']">{{ i.kind_label }}</text>
              <text v-if="i.kind !== 'self'" :class="['chip', i.protection === 'none' ? 'chip-danger' : 'chip-trip']">
                {{ i.protection_label }}
              </text>
            </view>
            <text v-if="i.note" class="im-note">{{ i.note }}</text>
          </view>
        </view>
      </view>
    </block>

    <!-- ================= 睡眠 ================= -->
    <block v-else>
      <view class="sl-stats">
        <view class="ss-main">
          <text class="ss-value">{{ minutesText(sleep.stats.avg_minutes) }}</text>
          <text class="ss-label">近 7 次平均</text>
        </view>
        <view class="ss-right">
          <text class="ss-quality">{{ sleep.stats.avg_quality || 0 }} 分</text>
          <text class="ss-label">平均质量</text>
        </view>
      </view>

      <view v-if="sleep.stats.week && sleep.stats.week.length" class="sl-chart">
        <view v-for="w in sleep.stats.week" :key="w.date" class="sc-col">
          <text class="sc-hours">{{ (w.minutes / 60).toFixed(1) }}</text>
          <view class="sc-bar-wrap">
            <view :class="['sc-bar', qualityClass(w.quality)]"
                  :style="{ height: barHeight(w.minutes) + 'rpx' }"></view>
          </view>
          <text class="sc-date">{{ w.date.slice(5) }}</text>
        </view>
      </view>

      <view class="hp-actions">
        <view class="hp-add" @click="openSleep()">＋ 记睡眠</view>
      </view>

      <view v-if="loading.sleep && !sleep.items.length" class="loading-text">牛马拉磨中…</view>

      <view v-else-if="!sleep.items.length" class="empty">
        <text class="empty-title">还没记过睡眠。</text>
        <text class="empty-sub">记一周，就能看出哪几天在报复性熬夜。</text>
      </view>

      <view v-else class="hp-list">
        <view v-for="s in sleep.items" :key="s.id" class="sl-row" @click="openSleep(s)">
          <view class="sl-date">
            <text class="sl-day">{{ s.sleep_date.slice(5) }}</text>
            <text class="sl-clock">{{ s.bed_time }} → {{ s.wake_time }}</text>
          </view>
          <view class="sl-main">
            <text class="sl-hours">{{ s.hours_text }}</text>
            <text class="sl-stars">{{ stars(s.quality) }} {{ s.quality_label }}</text>
            <text v-if="s.note" class="sl-note">{{ s.note }}</text>
          </view>
        </view>
      </view>
    </block>

    <view style="height: 40rpx"></view>

    <!-- ================= 表单：周期 ================= -->
    <view v-if="sheet === 'cycle'" class="sheet-mask" @touchstart.stop @click="sheet = ''">
      <view class="sheet" @click.stop>
        <view class="sheet-head">
          <text class="sheet-title">{{ cycleEdit ? '编辑经期' : '记录经期' }}</text>
          <text class="sheet-close" @click="sheet = ''">✕</text>
        </view>

        <view class="field">
          <text class="f-label">开始日期</text>
          <picker mode="date" :value="cycleForm.start_date" @change="e => cycleForm.start_date = e.detail.value">
            <view class="f-input">{{ cycleForm.start_date }}</view>
          </picker>
        </view>
        <view class="field">
          <text class="f-label">结束日期（不填表示还在进行）</text>
          <view class="f-row">
            <picker class="pick" mode="date" :value="cycleForm.end_date || cycleForm.start_date"
                    @change="e => cycleForm.end_date = e.detail.value">
              <view class="f-input">{{ cycleForm.end_date || '还在进行中' }}</view>
            </picker>
            <text v-if="cycleForm.end_date" class="clear" @click="cycleForm.end_date = ''">清除</text>
          </view>
        </view>
        <view class="field">
          <text class="f-label">流量</text>
          <view class="chips">
            <text v-for="f in flows" :key="f.value"
                  :class="['pick-chip', cycleForm.flow === f.value ? 'on' : '']"
                  @click="cycleForm.flow = f.value">{{ f.label }}</text>
          </view>
        </view>
        <view class="field">
          <text class="f-label">症状（可多选）</text>
          <view class="chips">
            <text v-for="s in symptoms" :key="s"
                  :class="['pick-chip', cycleForm.symptoms.includes(s) ? 'on' : '']"
                  @click="toggleSymptom(s)">{{ s }}</text>
          </view>
        </view>
        <view class="field">
          <text class="f-label">备注</text>
          <input class="f-input" v-model="cycleForm.note" maxlength="200" placeholder="想补充点什么" />
        </view>

        <button class="btn-primary submit" :loading="saving" @click="saveCycle">保存</button>
        <view v-if="cycleEdit" class="del-link" @click="removeCycle">删除这条</view>
      </view>
    </view>

    <!-- ================= 表单：亲密 ================= -->
    <view v-if="sheet === 'intimacy'" class="sheet-mask" @touchstart.stop @click="sheet = ''">
      <view class="sheet" @click.stop>
        <view class="sheet-head">
          <text class="sheet-title">{{ intimacyEdit ? '编辑记录' : '记一次' }}</text>
          <text class="sheet-close" @click="sheet = ''">✕</text>
        </view>
        <view class="privacy-bar">🔒 仅自己可见</view>

        <view class="field">
          <text class="f-label">日期</text>
          <picker mode="date" :value="intimacyForm.happen_date"
                  @change="e => intimacyForm.happen_date = e.detail.value">
            <view class="f-input">{{ intimacyForm.happen_date }}</view>
          </picker>
        </view>
        <view class="field">
          <text class="f-label">时间（可不填）</text>
          <view class="f-row">
            <picker class="pick" mode="time" :value="intimacyForm.happen_time || '22:00'"
                    @change="e => intimacyForm.happen_time = e.detail.value">
              <view class="f-input">{{ intimacyForm.happen_time || '不记录时间' }}</view>
            </picker>
            <text v-if="intimacyForm.happen_time" class="clear" @click="intimacyForm.happen_time = ''">清除</text>
          </view>
        </view>
        <view class="field">
          <text class="f-label">类型</text>
          <view class="chips">
            <text v-for="k in kinds" :key="k.value"
                  :class="['pick-chip', intimacyForm.kind === k.value ? 'on' : '']"
                  @click="intimacyForm.kind = k.value">{{ k.label }}</text>
          </view>
        </view>
        <view v-if="intimacyForm.kind !== 'self'" class="field">
          <text class="f-label">保护措施</text>
          <view class="chips">
            <text v-for="p in protections" :key="p.value"
                  :class="['pick-chip', intimacyForm.protection === p.value ? 'on' : '']"
                  @click="intimacyForm.protection = p.value">{{ p.label }}</text>
          </view>
        </view>
        <view class="field">
          <text class="f-label">备注</text>
          <input class="f-input" v-model="intimacyForm.note" maxlength="200" placeholder="可不填" />
        </view>

        <button class="btn-primary submit" :loading="saving" @click="saveIntimacy">保存</button>
        <view v-if="intimacyEdit" class="del-link" @click="removeIntimacy">删除这条</view>
      </view>
    </view>

    <!-- ================= 表单：睡眠 ================= -->
    <view v-if="sheet === 'sleep'" class="sheet-mask" @touchstart.stop @click="sheet = ''">
      <view class="sheet" @click.stop>
        <view class="sheet-head">
          <text class="sheet-title">{{ sleepEdit ? '编辑睡眠' : '记录睡眠' }}</text>
          <text class="sheet-close" @click="sheet = ''">✕</text>
        </view>

        <view class="field">
          <text class="f-label">起床日期</text>
          <picker mode="date" :value="sleepForm.sleep_date"
                  @change="e => sleepForm.sleep_date = e.detail.value">
            <view class="f-input">{{ sleepForm.sleep_date }}</view>
          </picker>
        </view>
        <view class="field">
          <text class="f-label">入睡时间</text>
          <view class="f-row">
            <picker class="pick" mode="time" :value="sleepForm.bed_time"
                    @change="e => sleepForm.bed_time = e.detail.value">
              <view class="f-input">{{ sleepForm.bed_time }}</view>
            </picker>
            <text class="clear" @click="setQuick('bed')">刚才</text>
          </view>
        </view>
        <view class="field">
          <text class="f-label">起床时间</text>
          <picker mode="time" :value="sleepForm.wake_time"
                  @change="e => sleepForm.wake_time = e.detail.value">
            <view class="f-input">{{ sleepForm.wake_time }}</view>
          </picker>
        </view>
        <view class="sleep-preview">睡了 {{ sleepPreview }}</view>

        <view class="field">
          <text class="f-label">睡眠质量</text>
          <view class="quality-row">
            <text v-for="q in [1, 2, 3, 4, 5]" :key="q"
                  :class="['q-star', sleepForm.quality >= q ? 'on' : '']"
                  @click="sleepForm.quality = q">★</text>
            <text class="q-label">{{ qualityLabel(sleepForm.quality) }}</text>
          </view>
        </view>
        <view class="field">
          <text class="f-label">备注</text>
          <input class="f-input" v-model="sleepForm.note" maxlength="200" placeholder="做梦、失眠、被吵醒…" />
        </view>

        <button class="btn-primary submit" :loading="saving" @click="saveSleep">保存</button>
        <view v-if="sleepEdit" class="del-link" @click="removeSleep">删除这条</view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import {
  apiHealthOverview, apiHealthCycle,
  apiCreateCycle, apiUpdateCycle, apiDeleteCycle,
  apiIntimacy, apiCreateIntimacy, apiUpdateIntimacy, apiDeleteIntimacy,
  apiSleep, apiCreateSleep, apiUpdateSleep, apiDeleteSleep,
} from '@/api'

const sections = [
  { key: 'calendar', label: '月历', emoji: '📅' },
  { key: 'cycle', label: '周期', emoji: '🩸' },
  { key: 'intimacy', label: '亲密', emoji: '💞' },
  { key: 'sleep', label: '睡眠', emoji: '😴' },
]
const weeks = ['日', '一', '二', '三', '四', '五', '六']
const flows = [
  { value: 'light', label: '少量' },
  { value: 'medium', label: '中等' },
  { value: 'heavy', label: '较多' },
]
const kinds = [
  { value: 'self', label: '自己' },
  { value: 'partner', label: '两人' },
  { value: 'multi', label: '多人' },
]
const protections = [
  { value: 'condom', label: '避孕套' },
  { value: 'pill', label: '避孕药' },
  { value: 'none', label: '无保护' },
  { value: 'na', label: '不记录' },
]
const qualityLabels = { 1: '很差', 2: '一般', 3: '还行', 4: '不错', 5: '很香' }

function localDate(offset = 0) {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}
function shortDate(iso) {
  return iso ? iso.slice(5) : ''
}

const sec = ref('calendar')
const sheet = ref('')
const saving = ref(false)
const loading = reactive({ cycle: false, intimacy: false, sleep: false })

// ---------- 月历 ----------
const calMonth = ref(localDate().slice(0, 7))
const calLoading = ref(false)
const calData = ref({ cycle_days: [], intimacy_days: [], sleep_days: [], predicted: null, stats: {} })
const selectedDate = ref(localDate())
const calCache = new Map()
let calSeq = 0
const thisMonth = localDate().slice(0, 7)
const calStats = computed(() => calData.value.stats || {})

const monthLabel = computed(() => {
  const [y, m] = calMonth.value.split('-')
  return `${y} 年 ${Number(m)} 月`
})

const calCells = computed(() => {
  const [y, m] = calMonth.value.split('-').map(Number)
  const lead = new Date(y, m - 1, 1).getDay()   // 0 = 周日
  const days = new Date(y, m, 0).getDate()
  const pred = calData.value.predicted

  const cycleMap = {}
  ;(calData.value.cycle_days || []).forEach(d => {
    cycleMap[d.date] = { ...d, id: d.record_id }
  })
  const intimacyMap = {}
  ;(calData.value.intimacy_days || []).forEach(d => { intimacyMap[d.date] = d })
  const sleepMap = {}
  ;(calData.value.sleep_days || []).forEach(d => { sleepMap[d.date] = d })

  const pad = n => String(n).padStart(2, '0')
  const cells = []
  for (let i = 0; i < lead; i++) cells.push(null)

  for (let day = 1; day <= days; day++) {
    const date = `${y}-${pad(m)}-${pad(day)}`
    const inPredictedPeriod = pred && date >= pred.period_start && date <= pred.period_end
    cells.push({
      day, date,
      today: date === calData.value.today,
      selected: date === selectedDate.value,
      cycle: cycleMap[date] || null,
      intimacy: intimacyMap[date] || null,
      sleep: sleepMap[date] || null,
      predictedPeriod: !!inPredictedPeriod,
      ovulation: !!(pred && date === pred.ovulation),
      fertile: !!(pred && date >= pred.fertile_start && date <= pred.fertile_end
                 && !cycleMap[date]),
    })
  }
  while (cells.length % 7) cells.push(null)
  return cells
})

const selectedCell = computed(() =>
  calCells.value.find(c => c && c.date === selectedDate.value) || null)

const selectedWeekday = computed(() => {
  if (!selectedCell.value) return ''
  const d = new Date(selectedCell.value.date + 'T00:00:00')
  return '周' + weeks[d.getDay()]
})

const dayHasRecords = computed(() => {
  const c = selectedCell.value
  return !!(c && (c.cycle || c.intimacy || c.sleep))
})

/** 未来的日期不允许记录（后端也只接受今天及以前） */
const canAddOnSelected = computed(() =>
  !!selectedCell.value && selectedCell.value.date <= localDate())

function sleepTone(quality) {
  if (quality >= 4) return 'good'
  if (quality === 3) return 'mid'
  return 'bad'
}

async function loadOverview(force = false) {
  const month = calMonth.value
  const seq = ++calSeq
  const hit = calCache.get(month)
  if (!force && hit && Date.now() - hit.at < 30000) {
    calData.value = hit.data
    return
  }
  calLoading.value = true
  try {
    const data = await apiHealthOverview(month)
    calCache.set(month, { data, at: Date.now() })
    if (seq === calSeq) calData.value = data
  } catch (e) { /* toast 已统一 */ } finally {
    if (seq === calSeq) calLoading.value = false
  }
}

/** 增删改之后：清掉缓存并重取当月的日历与周期预测 */
async function refreshAfterChange() {
  calCache.clear()
  await Promise.all([loadOverview(true), cycle.value ? loadCycle() : Promise.resolve()])
}

/** 亲密/睡眠不影响周期预测，只刷日历 */
function refreshCalendar() {
  calCache.clear()
  return loadOverview(true)
}

function shiftMonth(month, delta) {
  const [y, m] = month.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function goMonth(delta) {
  calMonth.value = shiftMonth(calMonth.value, delta)
  // 换月后不保留选中，避免明细与当月对不上；回到本月时自动选今天
  selectedDate.value = calMonth.value === thisMonth ? localDate() : ''
  loadOverview()
}

function backToToday() {
  calMonth.value = thisMonth
  selectedDate.value = localDate()
  loadOverview()
}

function selectDay(date) {
  selectedDate.value = date
}

const cycle = ref(null)
const cycleEdit = ref(null)
const cycleForm = reactive({ start_date: localDate(), end_date: '', flow: 'medium', symptoms: [], note: '' })

const intimacy = reactive({ items: [], stats: {} })
const intimacyEdit = ref(null)
const intimacyForm = reactive({
  happen_date: localDate(), happen_time: '', kind: 'partner', protection: 'condom', note: '',
})

const sleep = reactive({ items: [], stats: {} })
const sleepEdit = ref(null)
const sleepForm = reactive({
  sleep_date: localDate(), bed_time: '23:30', wake_time: '07:30', quality: 4, note: '',
})

const symptoms = computed(() => (cycle.value && cycle.value.symptom_options) || [])
const sleepPreview = computed(() => {
  const mins = durationMinutes(sleepForm.bed_time, sleepForm.wake_time)
  return mins === null ? '时间有误' : minutesText(mins)
})

function minutesText(minutes) {
  if (!minutes) return '—'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h} 小时 ${m} 分` : `${h} 小时`
}
function durationMinutes(bed, wake) {
  const parse = (v) => {
    const [h, m] = String(v || '').split(':').map(Number)
    return Number.isNaN(h) || Number.isNaN(m) ? null : h * 60 + m
  }
  const b = parse(bed)
  let w = parse(wake)
  if (b === null || w === null) return null
  if (w <= b) w += 24 * 60
  const d = w - b
  return d > 0 && d < 24 * 60 ? d : null
}
function stars(quality) {
  return '★'.repeat(quality) + '☆'.repeat(5 - quality)
}
function qualityLabel(q) {
  return qualityLabels[q] || ''
}
function qualityClass(quality) {
  if (quality >= 4) return 'good'
  if (quality === 3) return 'mid'
  return 'bad'
}
function barHeight(minutes) {
  // 以 9 小时为满格，最低 16rpx，避免短睡整条看不见
  const ratio = Math.min(1, (minutes || 0) / 540)
  return Math.max(16, Math.round(ratio * 180))
}

async function loadCycle() {
  loading.cycle = true
  try {
    cycle.value = await apiHealthCycle()
  } catch (e) { /* toast 已统一 */ } finally { loading.cycle = false }
}
async function loadIntimacy() {
  loading.intimacy = true
  try {
    const d = await apiIntimacy()
    intimacy.items = d.items || []
    intimacy.stats = d.stats || {}
  } catch (e) { /* toast 已统一 */ } finally { loading.intimacy = false }
}
async function loadSleep() {
  loading.sleep = true
  try {
    const d = await apiSleep()
    sleep.items = d.items || []
    sleep.stats = d.stats || {}
  } catch (e) { /* toast 已统一 */ } finally { loading.sleep = false }
}

function switchSection(key) {
  if (sec.value === key) return
  sec.value = key
  if (key === 'calendar' && !calData.value.today) loadOverview()
  if (key === 'cycle' && !cycle.value) loadCycle()
  if (key === 'intimacy' && !intimacy.items.length) loadIntimacy()
  if (key === 'sleep' && !sleep.items.length) loadSleep()
}

/** 供页面下拉刷新 / 回到前台时重取当前分段 */
async function reload() {
  if (sec.value === 'calendar') return loadOverview(true)
  if (sec.value === 'cycle') return loadCycle()
  if (sec.value === 'intimacy') return loadIntimacy()
  return loadSleep()
}
defineExpose({ reload })

// ---------- 周期 ----------
function openCycle(item, date) {
  if (!cycle.value) loadCycle()   // 症状选项来自 /cycle，没进过周期段时补一次
  cycleEdit.value = item || null
  cycleForm.start_date = item ? item.start_date : (date || localDate())
  cycleForm.end_date = item ? (item.end_date || '') : ''
  cycleForm.flow = item ? item.flow : 'medium'
  cycleForm.symptoms = item ? [...(item.symptoms || [])] : []
  cycleForm.note = item ? (item.note || '') : ''
  sheet.value = 'cycle'
}
function toggleSymptom(name) {
  const idx = cycleForm.symptoms.indexOf(name)
  if (idx >= 0) cycleForm.symptoms.splice(idx, 1)
  else cycleForm.symptoms.push(name)
}
async function saveCycle() {
  if (cycleForm.end_date && cycleForm.end_date < cycleForm.start_date) {
    return uni.showToast({ title: '结束日期不能早于开始', icon: 'none' })
  }
  saving.value = true
  const payload = {
    start_date: cycleForm.start_date,
    end_date: cycleForm.end_date || null,
    flow: cycleForm.flow,
    symptoms: cycleForm.symptoms,
    note: cycleForm.note.trim() || null,
  }
  try {
    if (cycleEdit.value) await apiUpdateCycle(cycleEdit.value.id, payload)
    else await apiCreateCycle(payload)
    sheet.value = ''
    await refreshAfterChange()
  } catch (e) { /* toast 已统一 */ } finally { saving.value = false }
}
function removeCycle() {
  const id = cycleEdit.value && cycleEdit.value.id
  if (!id) return
  uni.showModal({
    title: '删掉这条经期记录？', content: '删了之后预测会重新计算。',
    confirmText: '删掉', confirmColor: '#C0555F',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await apiDeleteCycle(id)
        sheet.value = ''
        await refreshAfterChange()
      } catch (e) { /* toast 已统一 */ }
    },
  })
}

// ---------- 亲密 ----------
function openIntimacy(item, date) {
  intimacyEdit.value = item || null
  intimacyForm.happen_date = item ? item.happen_date : (date || localDate())
  intimacyForm.happen_time = item ? (item.happen_time || '') : ''
  intimacyForm.kind = item ? item.kind : 'partner'
  intimacyForm.protection = item ? item.protection : 'condom'
  intimacyForm.note = item ? (item.note || '') : ''
  sheet.value = 'intimacy'
}
async function saveIntimacy() {
  saving.value = true
  const payload = {
    happen_date: intimacyForm.happen_date,
    happen_time: intimacyForm.happen_time || null,
    kind: intimacyForm.kind,
    protection: intimacyForm.kind === 'self' ? 'na' : intimacyForm.protection,
    note: intimacyForm.note.trim() || null,
  }
  try {
    if (intimacyEdit.value) await apiUpdateIntimacy(intimacyEdit.value.id, payload)
    else await apiCreateIntimacy(payload)
    sheet.value = ''
    await Promise.all([loadIntimacy(), refreshCalendar()])
  } catch (e) { /* toast 已统一 */ } finally { saving.value = false }
}
function removeIntimacy() {
  const id = intimacyEdit.value && intimacyEdit.value.id
  if (!id) return
  uni.showModal({
    title: '删掉这条记录？', content: '删除后无法恢复。',
    confirmText: '删掉', confirmColor: '#C0555F',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await apiDeleteIntimacy(id)
        sheet.value = ''
        await Promise.all([loadIntimacy(), refreshCalendar()])
      } catch (e) { /* toast 已统一 */ }
    },
  })
}

// ---------- 睡眠 ----------
function openSleep(item, date) {
  sleepEdit.value = item || null
  sleepForm.sleep_date = item ? item.sleep_date : (date || localDate())
  sleepForm.bed_time = item ? item.bed_time : '23:30'
  sleepForm.wake_time = item ? item.wake_time : '07:30'
  sleepForm.quality = item ? item.quality : 4
  sleepForm.note = item ? (item.note || '') : ''
  sheet.value = 'sleep'
}
function setQuick(which) {
  const now = new Date()
  const clock = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
  if (which === 'bed') sleepForm.bed_time = clock
}
async function saveSleep() {
  if (durationMinutes(sleepForm.bed_time, sleepForm.wake_time) === null) {
    return uni.showToast({ title: '起睡时间不能相同', icon: 'none' })
  }
  saving.value = true
  const payload = {
    sleep_date: sleepForm.sleep_date,
    bed_time: sleepForm.bed_time,
    wake_time: sleepForm.wake_time,
    quality: sleepForm.quality,
    note: sleepForm.note.trim() || null,
  }
  try {
    if (sleepEdit.value) await apiUpdateSleep(sleepEdit.value.id, payload)
    else await apiCreateSleep(payload)
    sheet.value = ''
    await Promise.all([loadSleep(), refreshCalendar()])
  } catch (e) { /* toast 已统一 */ } finally { saving.value = false }
}
function removeSleep() {
  const id = sleepEdit.value && sleepEdit.value.id
  if (!id) return
  uni.showModal({
    title: '删掉这条睡眠记录？', content: '删除后无法恢复。',
    confirmText: '删掉', confirmColor: '#C0555F',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await apiDeleteSleep(id)
        sheet.value = ''
        await Promise.all([loadSleep(), refreshCalendar()])
      } catch (e) { /* toast 已统一 */ }
    },
  })
}

loadOverview()
</script>

<style scoped>
.hp { padding-top: 4rpx; }

/* 内部三段 */
.hp-seg { display: flex; gap: 10rpx; margin-bottom: 22rpx; }
.hs-item {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6rpx;
  height: 62rpx; border-radius: 9999rpx; background: #fff;
  border: 1rpx solid var(--line2); color: var(--ink2); font-size: 24rpx;
}
.hs-item.on { background: var(--brand-l); border-color: #F3CDB3; color: var(--brand-d); font-weight: 600; }
.hs-emoji { font-size: 24rpx; }

.privacy-bar {
  font-size: 21rpx; color: var(--ink3); background: var(--line2);
  padding: 12rpx 18rpx; border-radius: 12rpx; margin-bottom: 20rpx;
}

.hp-actions { display: flex; justify-content: flex-end; margin: 6rpx 0 18rpx; }
.hp-add {
  font-size: 24rpx; color: var(--brand-d); background: var(--brand-l);
  padding: 12rpx 26rpx; border-radius: 9999rpx; font-weight: 600;
}
.hp-list { display: flex; flex-direction: column; gap: 12rpx; }
.hp-note { font-size: 20rpx; color: var(--ink3); text-align: center; padding: 24rpx 0 8rpx; }

/* ---------- 月历 ---------- */
.cal-card {
  background: #fff; border: 1rpx solid var(--line2); border-radius: 22rpx;
  padding: 16rpx 12rpx 10rpx; margin-bottom: 12rpx;
}
.cal-card.is-loading { opacity: .55; }
.cal-head { display: flex; align-items: center; gap: 6rpx; padding: 0 4rpx 10rpx; }
.cal-nav {
  width: 52rpx; height: 52rpx; display: flex; align-items: center; justify-content: center;
  font-size: 34rpx; color: var(--ink2); border-radius: 50%;
}
.cal-title { font-size: 28rpx; font-weight: 600; color: var(--ink); }
.cal-back {
  margin-left: auto; font-size: 20rpx; color: var(--brand-d);
  background: var(--brand-l); padding: 6rpx 16rpx; border-radius: 9999rpx;
}
.cal-week { display: flex; padding: 2rpx 0 6rpx; }
.cw { flex: 1; text-align: center; font-size: 19rpx; color: var(--ink3); }
.cal-grid { display: flex; flex-wrap: wrap; }
.cal-cell {
  width: 14.2857%; height: 84rpx; box-sizing: border-box;
  display: flex; flex-direction: column; align-items: center; gap: 4rpx;
  padding-top: 12rpx; border-radius: 12rpx;
}
.cal-cell.fertile { background: #FDF3E6; }
.cal-cell.sel { background: var(--brand-l); box-shadow: inset 0 0 0 2rpx var(--brand); }
.cal-day { font-size: 24rpx; color: var(--ink); line-height: 1; }
.cal-day.today {
  width: 40rpx; height: 40rpx; border-radius: 50%; background: var(--brand);
  color: #fff; font-size: 22rpx; font-weight: 600;
  display: flex; align-items: center; justify-content: center;
}
.cal-marks { height: 14rpx; display: flex; align-items: center; justify-content: center; gap: 4rpx; }
.mk { width: 8rpx; height: 8rpx; border-radius: 50%; }
.mk-period { width: 10rpx; height: 10rpx; border-radius: 50%; background: var(--danger); }
.mk-period.pre { background: transparent; border: 1rpx solid var(--danger); opacity: .75; }
.mk-ovu { background: transparent; border: 2rpx solid var(--gold); }
.mk-intimacy { background: #E48FA0; }
.mk-sleep.good { background: var(--ok); }
.mk-sleep.mid { background: var(--info); }
.mk-sleep.bad { background: var(--warn); }

.cal-legend {
  display: flex; flex-wrap: wrap; align-items: center; gap: 12rpx 18rpx;
  border-top: 1rpx solid var(--line2); margin-top: 8rpx; padding: 12rpx 8rpx 2rpx;
}
.lg { display: flex; align-items: center; gap: 6rpx; font-size: 18rpx; color: var(--ink3); }
.lg-fertile { width: 16rpx; height: 16rpx; border-radius: 4rpx; background: #FDF3E6; border: 1rpx solid #F1D8B6; }

.cal-sum { display: flex; align-items: center; flex-wrap: wrap; gap: 8rpx 10rpx; padding: 0 4rpx 14rpx; }
.cs-title { font-size: 20rpx; color: var(--ink3); }
.cs-item {
  font-size: 19rpx; color: var(--ink2); background: #fff;
  border: 1rpx solid var(--line2); border-radius: 9999rpx; padding: 5rpx 14rpx;
}

.day-card { background: #fff; border: 1rpx solid var(--line2); border-radius: 20rpx; padding: 22rpx; }
.dc-head { display: flex; align-items: center; gap: 10rpx; margin-bottom: 10rpx; }
.dc-date { font-size: 26rpx; font-weight: 600; color: var(--ink); }
.dc-today { font-size: 18rpx; color: var(--brand-d); background: var(--brand-l); padding: 3rpx 12rpx; border-radius: 8rpx; }
.dc-empty { font-size: 22rpx; color: var(--ink3); padding: 8rpx 0 14rpx; }
.dc-row { display: flex; align-items: flex-start; gap: 14rpx; padding: 14rpx 0; border-top: 1rpx solid var(--line2); }
.dc-icon { width: 34rpx; font-size: 26rpx; }
.dc-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4rpx; }
.dc-title { font-size: 24rpx; color: var(--ink); font-weight: 500; }
.dc-time { font-size: 19rpx; color: var(--ink3); margin-left: 8rpx; font-weight: 400; }
.dc-sub { font-size: 20rpx; color: var(--ink3); line-height: 1.5; }
.dc-edit { font-size: 20rpx; color: var(--ink3); padding-top: 4rpx; }
.dc-add { display: flex; gap: 12rpx; margin-top: 16rpx; }
.dca {
  flex: 1; text-align: center; font-size: 21rpx; font-weight: 600;
  color: var(--brand-d); background: var(--brand-l); padding: 12rpx 0; border-radius: 12rpx;
}
.dc-future { font-size: 20rpx; color: var(--ink3); margin-top: 14rpx; }
.cal-hint { font-size: 21rpx; color: var(--ink3); text-align: center; padding: 18rpx 10rpx 6rpx; line-height: 1.6; }

/* ---------- 周期 ---------- */
.cy-hero {
  border-radius: 24rpx; padding: 30rpx; color: #fff; margin-bottom: 16rpx;
  background: linear-gradient(135deg, #E38B7A, #C0555F);
}
.cy-hero.phase-fertile { background: linear-gradient(135deg, #E9A96A, #D97742); }
.cy-hero.phase-late { background: linear-gradient(135deg, #C99A4E, #A8752C); }
.cy-hero.phase-safe,
.cy-hero.phase-luteal { background: linear-gradient(135deg, #7FA3B8, #5B7FA6); }
.ch-top { display: flex; align-items: center; gap: 10rpx; }
.ch-phase { font-size: 24rpx; opacity: .92; }
.ch-ongoing {
  font-size: 18rpx; background: rgba(255, 255, 255, .22);
  padding: 3rpx 12rpx; border-radius: 8rpx;
}
.ch-main { display: block; font-size: 40rpx; font-weight: 700; margin: 14rpx 0 24rpx; }
.ch-cells { display: flex; }
.ch-cell { flex: 1; display: flex; flex-direction: column; gap: 4rpx; }
.cc-num { font-size: 30rpx; font-weight: 600; }
.cc-label { font-size: 19rpx; opacity: .82; }

.cy-tip {
  font-size: 22rpx; color: var(--ink2); line-height: 1.6;
  background: #fff; border: 1rpx solid var(--line2); border-radius: 16rpx;
  padding: 18rpx 22rpx; margin-bottom: 12rpx;
}
.cy-fertile {
  display: flex; align-items: center; gap: 12rpx; flex-wrap: wrap;
  background: var(--brand-l); border-radius: 16rpx; padding: 16rpx 22rpx;
  margin-bottom: 14rpx;
}
.cf-label { font-size: 20rpx; color: var(--brand-d); }
.cf-value { font-size: 24rpx; font-weight: 600; color: var(--brand-d); }
.cf-sub { font-size: 19rpx; color: var(--ink3); margin-left: auto; }

.cy-row {
  display: flex; gap: 18rpx; background: #fff; border: 1rpx solid var(--line2);
  border-radius: 18rpx; padding: 22rpx;
}
.cy-left { width: 88rpx; flex-shrink: 0; display: flex; flex-direction: column; gap: 2rpx; }
.cy-date { font-size: 26rpx; font-weight: 600; color: var(--ink); }
.cy-year { font-size: 18rpx; color: var(--ink3); }
.cy-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8rpx; }
.cy-title { display: flex; align-items: center; gap: 10rpx; flex-wrap: wrap; }
.cy-days { font-size: 24rpx; color: var(--ink); font-weight: 600; }
.cy-sym {
  font-size: 18rpx; color: var(--ink3); background: var(--line2);
  padding: 3rpx 10rpx; border-radius: 6rpx;
}
.cy-note { font-size: 21rpx; color: var(--ink3); line-height: 1.5; }

/* ---------- 亲密 ---------- */
.im-stats {
  display: flex; background: #fff; border: 1rpx solid var(--line2);
  border-radius: 20rpx; padding: 26rpx 0; margin-bottom: 14rpx;
}
.is-cell { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4rpx; }
.is-num { font-size: 34rpx; font-weight: 700; color: var(--ink); }
.is-label { font-size: 19rpx; color: var(--ink3); }

.im-kinds {
  display: flex; align-items: center; gap: 10rpx; flex-wrap: wrap;
  padding: 0 4rpx 16rpx;
}
.ik-item {
  font-size: 20rpx; color: var(--ink2); background: #fff;
  border: 1rpx solid var(--line2); padding: 6rpx 16rpx; border-radius: 9999rpx;
}
.ik-hint { font-size: 18rpx; color: var(--ink3); margin-left: auto; }

.im-row {
  display: flex; gap: 18rpx; background: #fff; border: 1rpx solid var(--line2);
  border-radius: 18rpx; padding: 22rpx;
}
.im-date { width: 88rpx; flex-shrink: 0; display: flex; flex-direction: column; gap: 2rpx; }
.im-day { font-size: 26rpx; font-weight: 600; }
.im-time { font-size: 18rpx; color: var(--ink3); }
.im-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8rpx; }
.im-tags { display: flex; gap: 10rpx; flex-wrap: wrap; }
.im-note { font-size: 21rpx; color: var(--ink3); line-height: 1.5; }
.chip-danger { background: var(--danger-l); color: var(--danger); }

/* ---------- 睡眠 ---------- */
.sl-stats {
  display: flex; align-items: center; background: #fff;
  border: 1rpx solid var(--line2); border-radius: 20rpx;
  padding: 26rpx 30rpx; margin-bottom: 16rpx;
}
.ss-main { flex: 1; display: flex; flex-direction: column; gap: 4rpx; }
.ss-value { font-size: 36rpx; font-weight: 700; color: var(--ink); }
.ss-right { display: flex; flex-direction: column; align-items: flex-end; gap: 4rpx; }
.ss-quality { font-size: 28rpx; font-weight: 600; color: var(--ok); }
.ss-label { font-size: 19rpx; color: var(--ink3); }

.sl-chart {
  display: flex; align-items: flex-end; gap: 10rpx;
  background: #fff; border: 1rpx solid var(--line2); border-radius: 20rpx;
  padding: 22rpx 20rpx 16rpx; margin-bottom: 16rpx;
}
.sc-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6rpx; }
.sc-hours { font-size: 16rpx; color: var(--ink3); }
.sc-bar-wrap { height: 180rpx; display: flex; align-items: flex-end; width: 100%; justify-content: center; }
.sc-bar { width: 26rpx; border-radius: 8rpx 8rpx 4rpx 4rpx; background: var(--info); }
.sc-bar.good { background: var(--ok); }
.sc-bar.mid { background: var(--info); }
.sc-bar.bad { background: var(--warn); }
.sc-date { font-size: 16rpx; color: var(--ink3); }

.sl-row {
  display: flex; gap: 18rpx; background: #fff; border: 1rpx solid var(--line2);
  border-radius: 18rpx; padding: 22rpx;
}
.sl-date { width: 110rpx; flex-shrink: 0; display: flex; flex-direction: column; gap: 2rpx; }
.sl-day { font-size: 26rpx; font-weight: 600; }
.sl-clock { font-size: 17rpx; color: var(--ink3); }
.sl-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6rpx; }
.sl-hours { font-size: 26rpx; font-weight: 600; color: var(--ink); }
.sl-stars { font-size: 20rpx; color: var(--gold); }
.sl-note { font-size: 21rpx; color: var(--ink3); }

/* ---------- 表单 ---------- */
.chips { display: flex; flex-wrap: wrap; gap: 12rpx; }
.pick-chip {
  font-size: 22rpx; color: var(--ink2); background: var(--line2);
  padding: 10rpx 22rpx; border-radius: 9999rpx;
}
.pick-chip.on { background: var(--brand-l); color: var(--brand-d); font-weight: 600; }
.pick { flex: 1; }
.clear { font-size: 23rpx; color: var(--ink3); padding-left: 18rpx; }
.sleep-preview {
  font-size: 22rpx; color: var(--brand-d); background: var(--brand-l);
  padding: 12rpx 20rpx; border-radius: 12rpx; margin-top: 12rpx;
}
.quality-row { display: flex; align-items: center; gap: 8rpx; }
.q-star { font-size: 40rpx; color: var(--line); }
.q-star.on { color: var(--gold); }
.q-label { font-size: 22rpx; color: var(--ink3); margin-left: 10rpx; }
.submit { margin-top: 28rpx; }
.del-link { text-align: center; color: var(--danger); font-size: 24rpx; padding: 24rpx 0 0; }

@media (min-width: 768px) {
  .hp { max-width: 720px; margin: 0 auto; }
}
</style>
