<template>
  <view v-if="visible" class="sheet-mask" @click="close">
    <view class="sheet" @click.stop>
      <view class="sheet-head">
        <text class="sheet-title">{{ item ? '编辑日子' : '记一个重要日子' }}</text>
        <text class="sheet-close" @click="close">✕</text>
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
      <view v-if="item" class="del-link" @click="remove">删除这个日子</view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { apiCreateCountdown, apiUpdateCountdown, apiDeleteCountdown } from '@/api'

const props = defineProps({
  visible: { type: Boolean, default: false },
  item: { type: Object, default: null },
})
const emit = defineEmits(['close', 'saved', 'deleted'])

const today = new Date().toISOString().slice(0, 10)
const saving = ref(false)
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

function fill() {
  const cd = props.item
  if (cd) {
    form.name = cd.name
    form.date = cd.base_date
    form.repeat_rule = cd.repeat_rule
    form.remind_offsets = [...(cd.remind_offsets || [])]
    form.emoji = cd.emoji || '🎯'
    form.note = cd.note || ''
    form.pinned = !!cd.pinned
  } else {
    form.name = ''
    form.date = today
    form.repeat_rule = 'yearly'
    form.remind_offsets = [7, 0]
    form.emoji = '🎯'
    form.note = ''
    form.pinned = false
  }
}

watch(() => props.visible, (v) => { if (v) fill() }, { immediate: true })

function close() { emit('close') }

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
    if (props.item) {
      await apiUpdateCountdown(props.item.id, { ...payload, pinned: form.pinned })
    } else {
      const cd = await apiCreateCountdown(payload)
      if (form.pinned) await apiUpdateCountdown(cd.id, { pinned: true })
    }
    uni.showToast({ title: '记下了', icon: 'none' })
    emit('saved')
    close()
  } catch (e) { /* toast 已统一 */ } finally {
    saving.value = false
  }
}

function remove() {
  if (!props.item) return
  const id = props.item.id
  uni.showModal({
    title: '真的删？',
    content: '它不会记仇。',
    confirmText: '删掉',
    confirmColor: '#C0555F',
    success: async (res) => {
      if (!res.confirm) return
      await apiDeleteCountdown(id)
      emit('deleted')
      close()
    },
  })
}
</script>

<style scoped>
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

.submit { margin-top: 28rpx; }
.del-link { text-align: center; color: var(--danger); font-size: 24rpx; padding: 24rpx 0 0; }
</style>
