<template>
  <view class="assets-panel">
    <!-- 净值卡（克制专业蓝） -->
    <view class="net-card">
      <text class="nc-label">家庭净值</text>
      <text class="nc-value">¥{{ money(netWorth) }}</text>
      <view class="nc-row">
        <view class="nc-cell">
          <text class="ncc-label">总资产</text>
          <text class="ncc-val">¥{{ money(totalAssets) }}</text>
        </view>
        <view class="nc-cell">
          <text class="ncc-label">总负债</text>
          <text class="ncc-val debt">¥{{ money(totalDebt) }}</text>
        </view>
      </view>
      <view class="nc-actions">
        <view class="nc-btn" @click="takeSnapshot" :class="taking ? 'loading' : ''">
          {{ taking ? '盘点中…' : '📸 现在盘点' }}
        </view>
        <view class="nc-btn ghost" @click="goInvest">📈 投资持仓</view>
      </view>
      <text v-if="fxFallback" class="nc-tip">汇率暂用固定值折算，后台汇率更新后自动修正</text>
      <text v-else-if="investmentMeta" class="nc-tip">投资持仓部分按最新价自动估值（不含未更新现价的标的）</text>
    </view>

    <!-- 趋势 -->
    <view v-if="snapshots.length > 1" class="card">
      <view class="section-title"><text>净值趋势</text><text class="section-extra">近 {{ snapshots.length }} 次盘点</text></view>
      <view class="trend">
        <view v-for="s in snapshots.slice(-6)" :key="s.id" class="trend-col">
          <text class="trend-val">{{ money(s.net_worth) }}</text>
          <view class="trend-bar-wrap">
            <view class="trend-bar" :style="{ height: barH(s.net_worth) + 'rpx' }"></view>
          </view>
          <text class="trend-label">{{ s.snapshot_date.slice(5) }}</text>
        </view>
      </view>
    </view>

    <!-- 分组明细 -->
    <view v-for="g in visibleGroups" :key="g.category" class="card">
      <view class="section-title">
        <text>{{ g.emoji }} {{ g.label }}</text>
        <text class="section-extra">¥{{ money(groupTotal(g)) }}</text>
      </view>
      <view v-for="it in g.items" :key="g.category + '-' + (it.id || it.name)"
            :class="['item-row', g.category === 'investment' ? 'linked' : '']"
            @click="g.category === 'investment' ? goInvest() : openItem(it)">
        <view class="ir-main">
          <text class="ir-name">{{ it.name }}</text>
          <text class="ir-sub">
            {{ it.is_linked ? '来自投资模块' : (it.note || currencyText(it)) }}
          </text>
        </view>
        <view class="ir-right">
          <text class="ir-amount">¥{{ money(it.amount_cny) }}</text>
          <text v-if="it.currency && it.currency !== 'CNY'" class="ir-orig">{{ it.currency }} {{ money(it.amount) }}</text>
        </view>
      </view>
      <view v-if="g.category !== 'investment'" class="ir-add" @click="openItem(null, g.category)">＋ 加一项</view>
    </view>

    <view v-if="!hasData" class="empty">
      <text class="empty-title">家底还没盘点过。</text>
      <text class="empty-sub">存款、房子、车、欠的钱，都算。诚实一点。</text>
      <view class="empty-btn" @click="openItem()">加第一项</view>
    </view>

    <!-- ===== 条目表单 ===== -->
    <view v-if="sheetVisible" class="sheet-mask" @click="sheetVisible = false">
      <view class="sheet" @click.stop>
        <view class="sheet-head">
          <text class="sheet-title">{{ editingId ? '编辑资产项' : '加一项资产' }}</text>
          <text class="sheet-close" @click="sheetVisible = false">✕</text>
        </view>

        <view class="field">
          <text class="f-label">类别</text>
          <view class="opt-chips">
            <view v-for="c in categories" :key="c.value"
                  :class="['opt-chip', form.category === c.value ? 'on' : '']"
                  @click="form.category = c.value">{{ c.emoji }} {{ c.label }}</view>
          </view>
        </view>

        <view class="field">
          <text class="f-label">名称</text>
          <input class="f-input" v-model="form.name" maxlength="20" placeholder="工资卡 / 房贷 / 车位" />
        </view>

        <view class="field">
          <text class="f-label">金额</text>
          <input class="f-input" type="digit" v-model="form.amount" placeholder="0.00" />
        </view>

        <view class="field">
          <text class="f-label">币种</text>
          <view class="opt-chips">
            <view v-for="c in currencies" :key="c.value"
                  :class="['opt-chip', form.currency === c.value ? 'on' : '']"
                  @click="form.currency = c.value">{{ c.label }}</view>
          </view>
        </view>

        <view class="field">
          <text class="f-label">备注</text>
          <input class="f-input" v-model="form.note" maxlength="50" placeholder="可不填" />
        </view>

        <button class="btn-primary submit" :loading="saving" @click="save">保存</button>
        <view v-if="editingId" class="del-link" @click="removeCurrent">删除这项</view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  apiAssets, apiCreateAssetItem, apiUpdateAssetItem,
  apiDeleteAssetItem, apiTakeAssetSnapshot,
} from '@/api'

const saving = ref(false)
const taking = ref(false)
const sheetVisible = ref(false)
const editingId = ref(null)

const groups = ref([])
const investmentMeta = ref(null)
const snapshots = ref([])
const netWorth = ref(0)
const totalAssets = ref(0)
const totalDebt = ref(0)
const fxFallback = ref(false)
const hasData = ref(false)

const categories = [
  { value: 'cash', label: '现金存款', emoji: '💰' },
  { value: 'property', label: '房产', emoji: '🏠' },
  { value: 'vehicle', label: '车辆', emoji: '🚗' },
  { value: 'other', label: '其他资产', emoji: '🧾' },
  { value: 'liability', label: '负债', emoji: '💳' },
]
const currencies = [
  { value: 'CNY', label: '人民币' },
  { value: 'USD', label: '美元' },
  { value: 'HKD', label: '港币' },
]

const form = reactive({ category: 'cash', name: '', amount: '', currency: 'CNY', note: '' })

const maxTrend = computed(() => Math.max(1, ...snapshots.value.map(s => s.net_worth)))
// 只显示有内容的分组（投资持仓固定保留，作为模块联动入口）
const visibleGroups = computed(() =>
  groups.value.filter(g => (g.items && g.items.length) || g.category === 'investment'))

function money(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function currencyText(it) {
  return it.currency === 'CNY' ? '人民币' : it.currency
}
function groupTotal(g) {
  return (g.items || []).reduce((a, i) => a + (i.amount_cny || 0), 0)
}
function barH(v) { return Math.max(6, (v / maxTrend.value) * 150) }

async function load() {
  try {
    const data = await apiAssets()
    groups.value = data.groups || []
    investmentMeta.value = data.investment || null
    snapshots.value = data.snapshots || []
    netWorth.value = data.net_worth || 0
    totalAssets.value = data.total_assets || 0
    totalDebt.value = data.total_liabilities || 0
    fxFallback.value = !!data.fallback_fx
    hasData.value = !!data.has_data
  } catch (e) { /* toast 已统一 */ }
}

function openItem(it, cat) {
  if (it) {
    editingId.value = it.id
    form.category = it.category
    form.name = it.name
    form.amount = String(it.amount)
    form.currency = it.currency || 'CNY'
    form.note = it.note || ''
  } else {
    editingId.value = null
    form.category = cat || 'cash'
    form.name = ''
    form.amount = ''
    form.currency = 'CNY'
    form.note = ''
  }
  sheetVisible.value = true
}

async function save() {
  const amount = Number(form.amount)
  if (!form.name.trim()) return uni.showToast({ title: '给它起个名字吧', icon: 'none' })
  if (amount < 0) return uni.showToast({ title: '金额不能是负的', icon: 'none' })
  saving.value = true
  const payload = {
    category: form.category, name: form.name.trim(), amount,
    currency: form.currency, note: form.note || null,
  }
  try {
    if (editingId.value) await apiUpdateAssetItem(editingId.value, payload)
    else await apiCreateAssetItem(payload)
    sheetVisible.value = false
    uni.showToast({ title: '记下了', icon: 'none' })
    load()
  } catch (e) { /* toast 已统一 */ } finally {
    saving.value = false
  }
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
      await apiDeleteAssetItem(id)
      sheetVisible.value = false
      load()
    },
  })
}

async function takeSnapshot() {
  if (taking.value) return
  taking.value = true
  try {
    await apiTakeAssetSnapshot()
    uni.showToast({ title: '盘点完成，净值已记录', icon: 'none' })
    load()
  } catch (e) { /* toast 已统一 */ } finally {
    taking.value = false
  }
}

function goInvest() { uni.navigateTo({ url: '/pages/holdings/holdings' }) }

defineExpose({ reload: load })
onMounted(load)
</script>

<style scoped>
/* 净值卡 · 克制专业蓝（与暖色主色区分，PRD §M6） */
.net-card {
  background: linear-gradient(135deg, #5B7FA6 0%, #456B92 100%);
  border-radius: 28rpx; padding: 34rpx 32rpx; color: #fff; margin-bottom: 24rpx;
  box-shadow: 0 10rpx 26rpx rgba(69, 107, 146, 0.24);
}
.nc-label { font-size: 23rpx; opacity: 0.85; }
.nc-value { display: block; font-size: 58rpx; font-weight: 700; margin: 10rpx 0 24rpx; letter-spacing: 0.5rpx; }
.nc-row { display: flex; gap: 40rpx; padding-bottom: 24rpx; border-bottom: 1rpx solid rgba(255,255,255,0.22); }
.nc-cell { display: flex; flex-direction: column; gap: 6rpx; }
.ncc-label { font-size: 20rpx; opacity: 0.8; }
.ncc-val { font-size: 28rpx; font-weight: 600; }
.ncc-val.debt { color: #FFE3E6; }
.nc-actions { display: flex; gap: 16rpx; margin-top: 24rpx; }
.nc-btn {
  flex: 1; height: 72rpx; line-height: 72rpx; text-align: center;
  background: #fff; color: #456B92; border-radius: 9999rpx;
  font-size: 25rpx; font-weight: 600;
}
.nc-btn.ghost { background: rgba(255,255,255,0.18); color: #fff; font-weight: 400; }
.nc-btn.loading { opacity: 0.7; }
.nc-tip { display: block; font-size: 19rpx; opacity: 0.78; margin-top: 18rpx; line-height: 1.6; }

/* 趋势 */
.trend { display: flex; align-items: flex-end; justify-content: space-between; height: 250rpx; padding-top: 10rpx; }
.trend-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6rpx; }
.trend-val { font-size: 17rpx; color: #5B7FA6; }
.trend-bar-wrap { height: 150rpx; display: flex; align-items: flex-end; }
.trend-bar { width: 40rpx; background: linear-gradient(180deg, #7C9DC0, #5B7FA6); border-radius: 8rpx 8rpx 0 0; }
.trend-label { font-size: 19rpx; color: var(--ink3); }

/* 明细 */
.item-row { display: flex; align-items: center; justify-content: space-between; padding: 20rpx 0; border-bottom: 1rpx solid var(--line2); }
.ir-main { display: flex; flex-direction: column; gap: 4rpx; min-width: 0; flex: 1; }
.ir-name { font-size: 27rpx; color: var(--ink); }
.ir-sub { font-size: 20rpx; color: var(--ink3); }
.ir-right { display: flex; flex-direction: column; align-items: flex-end; gap: 4rpx; }
.ir-amount { font-size: 28rpx; font-weight: 600; color: #2F4358; }
.ir-orig { font-size: 19rpx; color: var(--ink3); }
.ir-add {
  text-align: center; padding: 22rpx 0 4rpx; font-size: 24rpx;
  color: #5B7FA6;
}

.empty-btn {
  display: inline-block; margin-top: 28rpx; padding: 16rpx 40rpx;
  background: #5B7FA6; color: #fff; border-radius: 9999rpx; font-size: 26rpx;
}

/* 表单 */
.opt-chips { display: flex; flex-wrap: wrap; gap: 12rpx; }
.opt-chip {
  padding: 10rpx 22rpx; border-radius: 9999rpx; font-size: 23rpx;
  background: var(--bg); border: 1rpx solid var(--line2); color: var(--ink2);
}
.opt-chip.on { background: #DFEAF5; border-color: #8FB3D4; color: #2E5C86; font-weight: 600; }

.submit { margin-top: 28rpx; background: #5B7FA6; }
.del-link { text-align: center; color: var(--danger); font-size: 24rpx; padding: 24rpx 0 0; }
</style>
