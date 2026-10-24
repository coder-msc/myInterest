// 微信小程序自定义 tabBar（原生组件）
// uni-app 不会编译本目录下的 .vue，只能放原生 wxml/wxss/js，编译时原样拷到产物目录。
// pages.json 里 tabBar.custom = true 时，微信要求必须有 custom-tab-bar/index 组件。
// tab 列表统一放在同目录的 tabs.json：这里用 require，H5 的 CustomTab.vue 用 import，
// 两端只有这一份数据源（pages.json 的 tabBar.list 是微信框架必需的配置，仍需同步）。
const TABS = require('./tabs.json')

Component({
  data: {
    current: '',
    list: TABS,
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
