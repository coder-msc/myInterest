// 微信小程序自定义 tabBar（原生组件）
// uni-app 不会编译本目录下的 .vue，只能放原生 wxml/wxss/js，编译时原样拷到产物目录。
// pages.json 里 tabBar.custom = true 时，微信要求必须有 custom-tab-bar/index 组件。
// 注意：本目录被 uni-app 原样拷进产物，不参与打包，因此这里不能 require('./tabs.json')
// —— 微信原生运行时不支持加载 JSON 模块，会导致自定义 tabBar 整体不渲染（底部栏空白）。
// 所以列表在此内联；H5 端 CustomTab.vue 读的是同目录 tabs.json，
// 以及 pages.json 的 tabBar.list，三处改动需同步。
const TABS = [
  { path: '/pages/journal/journal', label: '手札', emoji: '🏠' },
  { path: '/pages/ledger/ledger', label: '账本', emoji: '💰' },
  { path: '/pages/worth/worth', label: '值得记', emoji: '🎯' },
  { path: '/pages/discover/discover', label: '发现', emoji: '🔍' },
  { path: '/pages/mine/mine', label: '我的', emoji: '👤' },
]

Component({
  data: {
    current: '',
    list: TABS,
    // 页面里打开弹层/对话框时置 true，由 utils/tabbar.js 通过 setData 控制
    maskHidden: false,
  },
  methods: {
    // 按页面栈同步高亮
    syncCurrent() {
      const pages = getCurrentPages()
      const page = pages[pages.length - 1]
      if (page && page.route) this.setData({ current: '/' + page.route })
    },
    switchTab(e) {
      const path = e.currentTarget.dataset.path
      if (!path || path === this.data.current) return
      // 切换中再点直接忽略，避免连点触发多次 switchTab
      if (this._busy) return
      this._busy = true
      // 先置高亮：部分基础库下 pageLifetimes.show 触发时机不稳定
      this.setData({ current: path })
      wx.switchTab({
        url: path,
        fail: () => {
          // 兜底：tabBar 配置异常时仍能跳过去（会清空页面栈）
          wx.reLaunch({ url: path })
        },
        complete: () => { this._busy = false },
      })
    },
  },
  // 挂载/渲染完成/页面显示三个时机各同步一次，避免基础库差异导致高亮丢失
  attached() { this.syncCurrent() },
  ready() { this.syncCurrent() },
  pageLifetimes: {
    show() { this.syncCurrent() },
  },
})
