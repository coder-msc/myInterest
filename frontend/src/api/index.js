/** API 模块：与 PC 端 api/index.js 对齐 */
import { get, post, patch, del, put, upload } from '@/utils/request'

// ---------- 认证 ----------
// 密码登录体系已下线：邮箱验证码（登录/注册合一）+ 微信登录（仅小程序）
export const apiWxLogin = (code, nickname, avatar) =>
  post('/api/auth/wx-login', { code, nickname, avatar }, { auth: false })
export const apiMe = () => get('/api/auth/me')
export const apiLogout = () => post('/api/auth/logout')
// 邮箱验证码相关
export const apiSendCode = (channel, target, purpose) =>
  post('/api/auth/send-code', { channel, target, purpose }, { auth: false })
export const apiEmailLogin = (email, code) =>
  post('/api/auth/email-login', { email, code }, { auth: false })
export const apiBindEmail = (email, code) =>
  post('/api/auth/bind-email', { email, code })
// 个人资料 / 解绑邮箱 / 注销账户（对齐 eatWhat 账户设置）
export const apiUpdateProfile = (payload) => put('/api/auth/profile', payload)
export const apiUnbindEmail = () => post('/api/auth/unbind-email')
export const apiDeleteMe = () => del('/api/auth/me')

// ---------- 持仓 ----------
export const apiHoldings = (params = {}) => get('/api/holdings', params)
export const apiHoldingDetail = (id) => get(`/api/holdings/${id}`)
export const apiHolding = (id) => get(`/api/holdings/${id}`)
export const apiCreateHolding = (payload) => post('/api/holdings', payload)
export const apiUpdateHolding = (id, payload) => patch(`/api/holdings/${id}`, payload)
export const apiDeleteHolding = (id) => del(`/api/holdings/${id}`)

// ---------- 批次 ----------
export const apiLots = (holdingId) => get(`/api/holdings/${holdingId}/lots`)
export const apiCreateLot = (holdingId, payload) =>
  post(`/api/holdings/${holdingId}/lots`, payload)
export const apiCreateLotsBatch = (holdingId, lots) =>
  post(`/api/holdings/${holdingId}/lots/batch`, { lots })
export const apiUpdateLot = (lotId, payload) => patch(`/api/lots/${lotId}`, payload)
export const apiDeleteLot = (lotId) => del(`/api/lots/${lotId}`)

// ---------- 分红（v0.3 纯实时计算，无落表） ----------
export const apiDividends = (params = {}) => get('/api/dividends', params)
// 详情：后端从落表 id 改成 schedule_id + holding_id 组合 query params
export const apiDividendDetail = (scheduleId, holdingId) =>
  get('/api/dividends/detail', { schedule_id: scheduleId, holding_id: holdingId })

// ---------- 统计 / 日历 / 设置 ----------
export const apiSummary = () => get('/api/stats/summary')
export const apiEnhancedSummary = (params = {}) => get('/api/stats/enhanced-summary', params)
export const apiDashboardMetrics = () => get('/api/stats/dashboard-metrics')
export const apiSaveDashboardMetrics = (selected) => put('/api/stats/dashboard-metrics', { selected })
export const apiMonthlyTrend = (range = '12m', params = {}) => get('/api/stats/monthly-trend', { range, ...params })
export const apiByMarket = (params = {}) => get('/api/stats/by-market', params)
export const apiForecast = (params = {}) => get('/api/stats/forecast', params)
export const apiTopHoldings = (limit = 10, params = {}) => get('/api/stats/top-holdings', { limit, ...params })
export const apiYieldRanking = (params = {}) => get('/api/stats/yield-ranking', params)
export const apiHoldingStats = (id) => get(`/api/stats/holdings/${id}`)
export const apiCalendar = (year, month, params = {}) => get('/api/calendar', { year, month, ...params })

// ---------- 预案（用户端） ----------
export const apiUpcoming = () => get('/api/schedules/upcoming')
export const apiSchedules = (params) => get('/api/schedules', params)
export const apiSecurities = (params) => get('/api/schedules/securities', params)
export const apiSubmitSchedule = (payload) => post('/api/schedules', payload)

// ---------- 公告 / 反馈 ----------
export const apiAnnouncements = () => get('/api/announcements')
export const apiMyFeedback = () => get('/api/feedback/me')
export const apiCreateFeedback = (content) => post('/api/feedback', { content })

// ---------- 设置 ----------
export const apiSettings = () => get('/api/settings')
export const apiSaveSettings = (payload) => put('/api/settings', payload)
export const apiRates = (date) => get('/api/rates', date ? { date } : {})

// ---------- 账户管理 ----------
export const apiAccounts = () => get('/api/accounts')
export const apiAccountsMeta = (accounts_meta) => put('/api/accounts/meta', { accounts_meta })

// ================= 纯牛马人生手札 =================
// ---------- 手札流 ----------
export const apiJournalHome = (params = {}) => get('/api/journal/home', params)
export const apiJournalFeed = (params = {}) => get('/api/journal/feed', params)
export const apiJournalSearch = (q) => get('/api/journal/search', { q })
export const apiJournalCounts = () => get('/api/journal/counts')
export const apiJournalStats = () => get('/api/journal/stats')
export const apiJournalModules = () => get('/api/journal/modules')
export const apiRebuildIndex = () => post('/api/journal/rebuild-index')

// ---------- 账本 ----------
export const apiLedger = (params = {}) => get('/api/ledger', params)
export const apiLedgerStats = (params = {}) => get('/api/ledger/stats', params)
export const apiLedgerDetail = (id) => get(`/api/ledger/${id}`)
export const apiCreateLedger = (payload) => post('/api/ledger', payload)
export const apiUpdateLedger = (id, payload) => patch(`/api/ledger/${id}`, payload)
export const apiDeleteLedger = (id) => del(`/api/ledger/${id}`)
export const apiLedgerCategories = () => get('/api/ledger/categories')
export const apiAddLedgerCategory = (name, emoji) => post('/api/ledger/categories', { name, emoji })
export const apiDeleteLedgerCategory = (id) => del(`/api/ledger/categories/${id}`)

// ---------- 日子（倒计时） ----------
export const apiCountdowns = (params = {}) => get('/api/countdowns', params)
export const apiCountdown = (id) => get(`/api/countdowns/${id}`)
export const apiCountdownPreview = (id) => get(`/api/countdowns/${id}/preview`)
export const apiCreateCountdown = (payload) => post('/api/countdowns', payload)
export const apiUpdateCountdown = (id, payload) => patch(`/api/countdowns/${id}`, payload)
export const apiDeleteCountdown = (id) => del(`/api/countdowns/${id}`)

// ---------- 足迹 · 旅游 ----------
export const apiTrips = (params = {}) => get('/api/trips', params)
export const apiTrip = (id) => get(`/api/trips/${id}`)
export const apiCreateTrip = (payload) => post('/api/trips', payload)
export const apiUpdateTrip = (id, payload) => patch(`/api/trips/${id}`, payload)
export const apiDeleteTrip = (id) => del(`/api/trips/${id}`)

// ---------- 值得记 · 健康（周期 / 亲密 / 睡眠） ----------
export const apiHealthOverview = (month) => get('/api/health/overview', month ? { month } : {})
export const apiHealthCycle = () => get('/api/health/cycle')
export const apiCreateCycle = (payload) => post('/api/health/cycle', payload)
export const apiUpdateCycle = (id, payload) => patch(`/api/health/cycle/${id}`, payload)
export const apiDeleteCycle = (id) => del(`/api/health/cycle/${id}`)

export const apiIntimacy = (params = {}) => get('/api/health/intimacy', params)
export const apiCreateIntimacy = (payload) => post('/api/health/intimacy', payload)
export const apiUpdateIntimacy = (id, payload) => patch(`/api/health/intimacy/${id}`, payload)
export const apiDeleteIntimacy = (id) => del(`/api/health/intimacy/${id}`)

export const apiSleep = (params = {}) => get('/api/health/sleep', params)
export const apiCreateSleep = (payload) => post('/api/health/sleep', payload)
export const apiUpdateSleep = (id, payload) => patch(`/api/health/sleep/${id}`, payload)
export const apiDeleteSleep = (id) => del(`/api/health/sleep/${id}`)

// ---------- 值得记 · 待办 ----------
export const apiTodos = (params = {}) => get('/api/todos', params)
export const apiCreateTodo = (payload) => post('/api/todos', payload)
export const apiUpdateTodo = (id, payload) => patch(`/api/todos/${id}`, payload)
export const apiDeleteTodo = (id) => del(`/api/todos/${id}`)

// ---------- 足迹 · 大事件 ----------
export const apiEvents = (params = {}) => get('/api/events', params)
export const apiEvent = (id) => get(`/api/events/${id}`)
export const apiCreateEvent = (payload) => post('/api/events', payload)
export const apiUpdateEvent = (id, payload) => patch(`/api/events/${id}`, payload)
export const apiDeleteEvent = (id) => del(`/api/events/${id}`)

// ---------- 家庭资产 ----------
export const apiAssets = () => get('/api/assets')
export const apiAssetTrend = () => get('/api/assets/trend')
export const apiCreateAssetItem = (payload) => post('/api/assets/items', payload)
export const apiUpdateAssetItem = (id, payload) => patch(`/api/assets/items/${id}`, payload)
export const apiDeleteAssetItem = (id) => del(`/api/assets/items/${id}`)
export const apiTakeAssetSnapshot = () => post('/api/assets/snapshot')

// ---------- 媒体 ----------
export const apiUploadMedia = (filePath, ownerType = 'unanchored', ownerId = null) =>
  upload('/api/media/upload', filePath, {
    owner_type: ownerType,
    ...(ownerId ? { owner_id: String(ownerId) } : {}),
  })
export const apiUnanchoredMedia = () => get('/api/media/unanchored')
export const apiAttachMedia = (asset_ids, owner_type, owner_id) =>
  post('/api/media/attach', { asset_ids, owner_type, owner_id })
export const apiDeleteMedia = (id) => del(`/api/media/${id}`)

// ---------- 提醒中心 ----------
export const apiNotifications = (params = {}) => get('/api/notifications', params)
export const apiUnreadCount = () => get('/api/notifications/unread')
export const apiReadNotification = (id) => post(`/api/notifications/${id}/read`)
export const apiReadAllNotifications = () => post('/api/notifications/read-all')
export const apiDeleteNotification = (id) => del(`/api/notifications/${id}`)

// ---------- 回收站 / 导出 ----------
export const apiRecycleBin = () => get('/api/recycle-bin')
export const apiRestoreRecycle = (type, id) => post(`/api/recycle-bin/${type}/${id}/restore`)
export const apiExportFull = () => get('/api/export/full')

// ---------- 树洞（发现 · 公共频道） ----------
export const apiTreeholeFeed = (params = {}) => get('/api/treehole', params)
export const apiTreeholeMine = () => get('/api/treehole/mine')
export const apiTreeholeQuota = () => get('/api/treehole/quota')
export const apiCreateTreeholePost = (content) => post('/api/treehole', { content })
export const apiDeleteTreeholePost = (id) => del(`/api/treehole/${id}`)
export const apiReportTreeholePost = (id, reason) =>
  post(`/api/treehole/${id}/report`, { reason })
