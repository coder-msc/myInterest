<template>
  <div>
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索用户名 / 邮箱 / ID" style="width: 220px" clearable
                @keyup.enter="onFilterChange" @clear="onFilterChange" />
      <el-select v-model="status" placeholder="全部状态" clearable style="width: 120px" @change="onFilterChange">
        <el-option label="正常" value="active" />
        <el-option label="已封禁" value="banned" />
      </el-select>
      <el-select v-model="role" placeholder="全部角色" clearable style="width: 130px" @change="onFilterChange">
        <el-option label="普通用户" value="user" />
        <el-option label="管理员" value="admin" />
        <el-option label="超级管理员" value="super_admin" />
      </el-select>
      <el-button type="primary" @click="onFilterChange">查询</el-button>
      <span v-if="!canOperate" class="text-muted hint">封禁 / 解封仅超级管理员可操作</span>
    </div>

    <div class="card">
      <el-table :data="list" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="nickname" label="昵称" width="120" />
        <el-table-column prop="email" label="邮箱(脱敏)" width="180" />
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="row.role === 'user' ? 'info' : 'warning'" size="small">
              {{ row.role === 'super_admin' ? '超管' : row.role === 'admin' ? '管理员' : '用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="持仓 / 分红" width="110" align="center">
          <template #default="{ row }">{{ row.holding_count }} / {{ row.dividend_count }}</template>
        </el-table-column>
        <el-table-column label="累计分红" width="120" align="right">
          <template #default="{ row }">{{ fmtCNY(row.total_dividend_cny) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="160">
          <template #default="{ row }">{{ row.created_at?.slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最近登录" width="160">
          <template #default="{ row }">{{ row.last_login_at?.slice(0, 16) || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status === 'active' ? '正常' : '已封禁' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewData(row)">查看数据</el-button>
            <el-button v-if="canOperate && row.status === 'active' && row.role === 'user'"
                       link type="danger" @click="ban(row)">封禁</el-button>
            <el-button v-if="canOperate && row.status === 'banned'"
                       link type="success" @click="unban(row)">解封</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination background layout="total, prev, pager, next"
                       :total="total" :page-size="pageSize" :current-page="page"
                       @current-change="onPage" />
      </div>
    </div>

    <!-- 用户数据只读查看 -->
    <el-dialog v-model="dataDlg" :title="`用户数据（只读）· ${viewing?.username}`" width="720">
      <div v-loading="dataLoading">
        <div v-if="viewUser" class="ud-user">
          <span>{{ viewUser.email || '-' }}</span>
          <span>注册 {{ viewUser.created_at?.slice(0, 10) }}</span>
          <span>最近登录 {{ viewUser.last_login_at?.slice(0, 16) || '-' }}</span>
        </div>
        <div v-if="viewUser" class="ud-summary">
          共 {{ userHoldings.length }} 个持仓 · {{ userDividends.length }} 笔分红
        </div>
        <div v-if="!userHoldings.length" class="empty-tip">该用户暂无持仓数据</div>
        <div v-for="h in userHoldings" :key="h.id" class="ud-card">
          <div class="ud-head">
            <span class="badge"
                  :style="{ background: (marketMap[h.market]?.color || '#64748b') + '14', color: marketMap[h.market]?.color || '#64748b' }">
              {{ marketMap[h.market]?.label || h.market }}
            </span>
            <b>{{ h.name }}</b><span class="text-muted">{{ h.code }}</span>
          </div>
          <div class="ud-grid">
            <span>持仓 {{ h.shares_now }} 股</span>
            <span>批次 {{ h.lot_count }}</span>
            <span>分红 {{ dividendCountOf(h.id) }} 笔</span>
            <span class="text-emerald">累计 {{ fmtCNY(h.total_dividend) }}</span>
          </div>
        </div>
      </div>
      <p class="text-muted" style="font-size: 12px; margin-top: 12px">
        管理员对用户业务数据仅只读访问，本次查看已记录操作日志
      </p>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  ElButton, ElDialog, ElInput, ElMessage, ElMessageBox, ElOption, ElPagination,
  ElSelect, ElTable, ElTableColumn, ElTag, vLoading,
} from '@/utils/admin-ui'
import { apiAdminUsers, apiAdminUserData, apiAdminBanUser, apiAdminUnbanUser } from '@/api'
import { marketMap, fmtCNY } from '@/utils/constants'
import { userStore } from '@/store/user'

const canOperate = computed(() => userStore.user?.role === 'super_admin')

const list = ref([])
const loading = ref(false)
const keyword = ref('')
const status = ref('')
const role = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)

const dataDlg = ref(false)
const dataLoading = ref(false)
const viewUser = ref(null)
const userHoldings = ref([])
const userDividends = ref([])
const viewing = ref(null)

// 按持仓统计分红笔数（后端持仓行只返回金额汇总）
const dividendCountMap = computed(() => {
  const map = {}
  for (const d of userDividends.value) {
    map[d.holding_id] = (map[d.holding_id] || 0) + 1
  }
  return map
})
function dividendCountOf(holdingId) { return dividendCountMap.value[holdingId] || 0 }

function onFilterChange() {
  page.value = 1
  load()
}
function onPage(p) {
  page.value = p
  load()
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    if (status.value) params.status = status.value
    if (role.value) params.role = role.value
    const data = await apiAdminUsers(params)
    list.value = data.items || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

async function viewData(row) {
  viewing.value = row
  dataDlg.value = true
  dataLoading.value = true
  viewUser.value = null
  userHoldings.value = []
  userDividends.value = []
  try {
    const data = await apiAdminUserData(row.id)
    viewUser.value = data.user || null
    userHoldings.value = data.holdings || []
    userDividends.value = data.dividends || []
  } finally {
    dataLoading.value = false
  }
}

async function ban(row) {
  try {
    await ElMessageBox.confirm(`确认封禁用户「${row.username}」？封禁后无法登录`, '封禁确认', { type: 'warning' })
    await apiAdminBanUser(row.id)
    ElMessage.success('已封禁')
    load()
  } catch (e) { /* 取消或 toast 已统一 */ }
}

async function unban(row) {
  try {
    await apiAdminUnbanUser(row.id)
    ElMessage.success('已解封')
    load()
  } catch (e) { /* toast 已统一 */ }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.hint { font-size: 12px; color: #d97706; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.ud-user { display: flex; gap: 16px; font-size: 12px; color: #64748b; margin-bottom: 8px; }
.ud-summary { font-size: 13px; color: #334155; margin-bottom: 12px; }
.ud-card { border: 1px solid #f1f5f9; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.ud-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ud-grid { display: flex; gap: 16px; font-size: 13px; color: #475569; }
.empty-tip { color: #94a3b8; text-align: center; padding: 24px 0; font-size: 13px; }
.pager { display: flex; justify-content: flex-end; padding-top: 16px; }
.text-muted { color: #64748b; }
</style>
