<template>
  <div class="treehole">
    <div class="toolbar">
      <el-radio-group v-model="status" size="small" @change="load(1)">
        <el-radio-button value="pending">待审核（{{ pendingCount }}）</el-radio-button>
        <el-radio-button value="approved">已通过</el-radio-button>
        <el-radio-button value="rejected">已拒绝</el-radio-button>
        <el-radio-button value="hidden">待复核</el-radio-button>
        <el-radio-button value="visited">全部处理过</el-radio-button>
      </el-radio-group>
      <span class="tip">先审后发 · 举报 3 次自动转入待复核</span>
    </div>

    <div v-loading="loading" class="list">
      <div v-if="!items.length" class="empty-tip">这个分类下暂时没有发言</div>

      <div v-for="p in items" :key="p.id" class="post">
        <div class="post-head">
          <span class="code">{{ p.anon_code }}</span>
          <el-tag size="small" :type="statusType(p.status)">{{ p.status_text }}</el-tag>
          <span v-if="p.reports" class="reports">被举报 {{ p.reports }} 次</span>
          <span class="grow"></span>
          <span class="meta">{{ p.username }} · {{ p.created_at?.slice(0, 16) }}</span>
        </div>

        <div class="post-content">{{ p.content }}</div>

        <div v-if="p.reason" class="post-reason">说明：{{ p.reason }}</div>

        <div class="post-actions">
          <el-button v-if="p.status === 'pending'" type="primary" size="small" @click="approve(p)">
            通过
          </el-button>
          <el-button v-if="p.status === 'pending'" type="danger" size="small" plain @click="openReject(p)">
            拒绝
          </el-button>
          <el-button v-if="p.status === 'approved'" type="warning" size="small" plain @click="openHide(p)">
            下架
          </el-button>
          <el-button v-if="p.status === 'hidden'" type="success" size="small" plain @click="approve(p)">
            恢复
          </el-button>
        </div>
      </div>
    </div>

    <div v-if="total > pageSize" class="pager">
      <el-pagination background layout="prev, pager, next" :total="total"
                     :page-size="pageSize" :current-page="page" @current-change="load" />
    </div>

    <el-dialog v-model="dialog" :title="dialogTitle" width="420px">
      <el-input v-model="reason" type="textarea" :rows="3" maxlength="100"
                placeholder="填写原因，用户会在「我的发言」里看到" />
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="confirmAction">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import {
  ElButton, ElDialog, ElInput, ElMessage, ElPagination, ElRadioButton,
  ElRadioGroup, ElTag, vLoading,
} from '@/utils/admin-ui'
import {
  apiAdminTreehole, apiAdminApproveTreehole, apiAdminRejectTreehole, apiAdminHideTreehole,
} from '@/api'

const status = ref('pending')
const items = ref([])
const total = ref(0)
const pendingCount = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const saving = ref(false)

const dialog = ref(false)
const dialogTitle = ref('')
const reason = ref('')
const target = ref(null)
const action = ref('')

async function load(p = page.value) {
  page.value = p
  loading.value = true
  try {
    const data = await apiAdminTreehole({ status: status.value, page: p, page_size: pageSize })
    items.value = data.items || []
    total.value = data.total || 0
    pendingCount.value = data.pending_count || 0
  } finally {
    loading.value = false
  }
}

function statusType(s) {
  return { pending: 'warning', approved: 'success', rejected: 'danger', hidden: 'info' }[s] || 'info'
}

async function approve(p) {
  try {
    await apiAdminApproveTreehole(p.id)
    ElMessage.success(p.status === 'hidden' ? '已恢复展示' : '已通过审核')
    load()
  } catch (e) { /* toast 已统一 */ }
}

function openReject(p) {
  target.value = p
  action.value = 'reject'
  dialogTitle.value = '拒绝这条发言'
  reason.value = ''
  dialog.value = true
}

function openHide(p) {
  target.value = p
  action.value = 'hide'
  dialogTitle.value = '下架这条发言'
  reason.value = ''
  dialog.value = true
}

async function confirmAction() {
  if (!reason.value.trim()) return ElMessage.warning('请填写原因')
  saving.value = true
  try {
    if (action.value === 'reject') await apiAdminRejectTreehole(target.value.id, reason.value.trim())
    else await apiAdminHideTreehole(target.value.id, reason.value.trim())
    ElMessage.success(action.value === 'reject' ? '已拒绝' : '已下架')
    dialog.value = false
    load()
  } catch (e) { /* toast 已统一 */ } finally {
    saving.value = false
  }
}

onMounted(() => load(1))
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.tip { font-size: 12px; color: #94a3b8; }
.list { display: flex; flex-direction: column; gap: 12px; min-height: 120px; }
.empty-tip { padding: 40px; text-align: center; color: #94a3b8; font-size: 13px; }

.post {
  background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
  padding: 16px 18px;
}
.post-head { display: flex; align-items: center; gap: 10px; }
.code { font-size: 13px; font-weight: 600; color: #6d5a9e; }
.reports { font-size: 12px; color: #d97706; }
.grow { flex: 1; }
.meta { font-size: 12px; color: #94a3b8; }
.post-content { margin-top: 10px; font-size: 14px; line-height: 1.75; color: #1e293b; white-space: pre-wrap; word-break: break-word; }
.post-reason { margin-top: 8px; font-size: 12px; color: #b45309; }
.post-actions { margin-top: 12px; display: flex; gap: 8px; }

.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
