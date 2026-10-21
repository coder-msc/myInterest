<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout :title="tool ? tool.name : '工具'" subtitle="算清楚，再决定" /><!-- #endif -->

    <block v-if="tool">
      <view class="head">
        <text class="head-emoji">{{ tool.emoji }}</text>
        <view class="head-main">
          <text class="head-name">{{ tool.name }}</text>
          <text class="head-desc">{{ tool.desc }}</text>
        </view>
      </view>

      <!-- 输入区：改一个数，结果立刻刷新 -->
      <view class="card form-card">
        <view v-for="f in tool.fields" :key="f.key" class="field-row">
          <view class="fr-label">
            <text class="fr-name">{{ f.label }}</text>
            <text v-if="f.hint" class="fr-hint">{{ f.hint }}</text>
          </view>

          <view v-if="f.type === 'select'" class="fr-select">
            <picker mode="selector" :value="selectIndex(f)" :range="f.options"
                    @change="e => onSelect(f, e)">
              <view class="select-box">
                <text>{{ optionLabel(f) }}</text>
                <text class="select-arrow">▾</text>
              </view>
            </picker>
          </view>

          <view v-else class="fr-input-wrap">
            <input class="fr-input" type="digit" :value="String(values[f.key])"
                   @input="e => onInput(f, e)" />
            <text class="fr-suffix">{{ f.suffix }}</text>
          </view>
        </view>
      </view>

      <!-- 结果区 -->
      <view :class="['result', 'bg-' + result.primary.tone]">
        <text class="res-label">{{ result.primary.label }}</text>
        <text class="res-value">{{ result.primary.value }}</text>
        <view v-if="result.verdict" class="res-verdict">{{ result.verdict }}</view>
      </view>

      <view class="card detail-card">
        <view v-for="(r, i) in result.rows" :key="i" class="detail-row">
          <text class="dr-label">{{ r.label }}</text>
          <text class="dr-value">{{ r.value }}</text>
        </view>
      </view>

      <text class="note">{{ tool.note }}</text>
      <text v-if="sourceHint" class="source-hint">{{ sourceHint }}</text>

      <view class="actions">
        <button class="btn-ghost" @click="reset">恢复默认</button>
      </view>
    </block>

    <view v-else class="empty">
      <text class="empty-title">没找到这个工具。</text>
      <view class="empty-btn" @click="goBack">返回</view>
    </view>

    <view style="height: 120rpx"></view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { TOOLS } from '@/utils/tools'
import { get } from '@/utils/request'
import WebLayout from '@/components/WebLayout.vue'

const key = ref('')
const tool = computed(() => TOOLS[key.value] || null)
const values = reactive({})
// 需要外部数据的工具（如「年度攒钱进度」读账本）把数据放在这里
const ctx = reactive({ ledger: null })
const sourceHint = ref('')

function initValues() {
  if (!tool.value) return
  for (const f of tool.value.fields) {
    values[f.key] = f.default
  }
}

const result = computed(() => {
  if (!tool.value) return { primary: { label: '', value: '', tone: 'brand' }, rows: [] }
  try {
    return tool.value.compute(values, ctx)
  } catch (e) {
    return { primary: { label: '计算失败', value: '—', tone: 'danger' }, rows: [] }
  }
})

/** 读账本近 12 个月的收支，取今年的结余当作已存 */
async function loadLedger() {
  const year = String(new Date().getFullYear())
  try {
    const d = await get('/api/ledger/stats', { months: 12 })
    const rows = (d.trend || []).filter(r => String(r.month || '').startsWith(year))
    const income = rows.reduce((s, r) => s + Number(r.income || 0), 0)
    const expense = rows.reduce((s, r) => s + Number(r.expense || 0), 0)
    ctx.ledger = { income, expense, net: income - expense, months: rows.length }
    sourceHint.value = rows.length
      ? `已自动读取账本今年 ${rows.length} 个月的数据`
      : '账本今年还没有记录，可在下方手动填写已存金额'
  } catch (e) {
    sourceHint.value = '账本数据读取失败，可在下方手动填写已存金额'
  }
}

function onInput(f, e) {
  const raw = e.detail.value
  values[f.key] = raw === '' ? '' : Number(raw)
}

function onSelect(f, e) {
  const opt = f.options[Number(e.detail.value)]
  values[f.key] = opt ? opt.value : ''
}
function selectIndex(f) {
  const i = f.options.findIndex(o => o.value === values[f.key])
  return i < 0 ? 0 : i
}
function optionLabel(f) {
  const o = f.options.find(x => x.value === values[f.key])
  return o ? o.label : (f.options[0] ? f.options[0].label : '')
}

function reset() {
  initValues()
  uni.showToast({ title: '已恢复默认值', icon: 'none' })
}

function goBack() {
  uni.navigateBack({
    delta: 1,
    fail: () => uni.switchTab({ url: '/pages/discover/discover' }),
  })
}

onLoad((q) => {
  key.value = q && q.key ? q.key : ''
  initValues()
  uni.setNavigationBarTitle({ title: tool.value ? tool.value.name : '小工具' })
  if (tool.value && tool.value.source === 'ledger') loadLedger()
})
</script>

<style scoped>
.page { padding: 24rpx; }

.head { display: flex; align-items: center; gap: 16rpx; padding: 0 6rpx 22rpx; }
.head-emoji { font-size: 52rpx; }
.head-main { flex: 1; display: flex; flex-direction: column; gap: 6rpx; }
.head-name { font-size: 34rpx; font-weight: 700; color: var(--ink); }
.head-desc { font-size: 21rpx; color: var(--ink3); line-height: 1.5; }

.form-card { padding: 8rpx 24rpx; margin-bottom: 24rpx; }
.field-row {
  display: flex; align-items: center; justify-content: space-between; gap: 20rpx;
  padding: 22rpx 0; border-bottom: 1rpx solid var(--line2);
}
.field-row:last-child { border-bottom: none; }
.fr-label { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4rpx; }
.fr-name { font-size: 26rpx; color: var(--ink); }
.fr-hint { font-size: 18rpx; color: var(--ink3); line-height: 1.4; }

.fr-input-wrap { display: flex; align-items: center; gap: 8rpx; flex-shrink: 0; }
.fr-input {
  width: 190rpx; height: 62rpx; text-align: right; font-size: 28rpx;
  color: var(--ink); background: var(--bg); border-radius: 12rpx; padding: 0 16rpx;
  box-sizing: border-box;
}
.fr-suffix { font-size: 22rpx; color: var(--ink3); width: 46rpx; }

.select-box {
  display: flex; align-items: center; gap: 10rpx; height: 62rpx; padding: 0 18rpx;
  background: var(--bg); border-radius: 12rpx; font-size: 24rpx; color: var(--ink);
}
.select-arrow { font-size: 20rpx; color: var(--ink3); }

.result {
  padding: 36rpx 28rpx; border-radius: 24rpx; margin-bottom: 22rpx;
  background: linear-gradient(135deg, #D97742, #B85C2E);
  display: flex; flex-direction: column; align-items: center; gap: 8rpx;
}
/* 结果主色调：按语义区分（不依赖 :has，兼容小程序 webview） */
.result.bg-info { background: linear-gradient(135deg, #5B7FA6, #456B92); }
.result.bg-ok { background: linear-gradient(135deg, #3F8F6D, #34775B); }
.result.bg-warn { background: linear-gradient(135deg, #C9861F, #A96E16); }
.result.bg-danger { background: linear-gradient(135deg, #C0555F, #A34650); }
.res-label { font-size: 22rpx; color: rgba(255, 255, 255, .82); }
.res-value { font-size: 60rpx; font-weight: 800; color: #fff; line-height: 1.2; text-align: center; }
.res-verdict {
  margin-top: 12rpx; font-size: 22rpx; color: #fff; text-align: center;
  background: rgba(255, 255, 255, .16); padding: 10rpx 22rpx; border-radius: 12rpx; line-height: 1.6;
}

.detail-card { padding: 6rpx 24rpx; }
.detail-row {
  display: flex; align-items: center; justify-content: space-between; gap: 20rpx;
  padding: 22rpx 0; border-bottom: 1rpx solid var(--line2);
}
.detail-row:last-child { border-bottom: none; }
.dr-label { font-size: 24rpx; color: var(--ink2); flex: 1; }
.dr-value { font-size: 25rpx; font-weight: 600; color: var(--ink); text-align: right; }

.note { display: block; font-size: 19rpx; color: var(--ink3); line-height: 1.7; padding: 20rpx 8rpx; }
.source-hint { display: block; font-size: 19rpx; color: var(--brand); line-height: 1.6; padding: 0 8rpx 8rpx; }

.actions { display: flex; justify-content: center; }
.btn-ghost {
  font-size: 24rpx; color: var(--ink2); background: #fff;
  border: 1rpx solid var(--line); border-radius: 9999rpx; padding: 0 40rpx; height: 68rpx;
  line-height: 68rpx;
}

.empty { padding: 120rpx 40rpx; display: flex; flex-direction: column; align-items: center; }
.empty-title { font-size: 26rpx; color: var(--ink3); }
.empty-btn {
  margin-top: 28rpx; padding: 16rpx 44rpx; background: var(--brand); color: #fff;
  border-radius: 9999rpx; font-size: 26rpx;
}

@media (min-width: 768px) {
  .page { max-width: 720px; margin: 0 auto; }
}
</style>
