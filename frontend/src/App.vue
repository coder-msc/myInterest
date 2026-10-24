<script>
import { TOKEN_KEY } from './utils/config'
import { redirectToLogin } from './utils/request'

export default {
  onLaunch() {
    // 未登录走统一跳转（内含延迟与单飞），避免 launch 阶段 webview 未就绪时 reLaunch 超时
    if (!uni.getStorageSync(TOKEN_KEY)) redirectToLogin()
  },
}
</script>

<style>
/* ============================================================
   全局样式 · 纯牛马人生手札
   调色板与 design/纯牛马人生手札-PRD.html 保持一致：
   暖米底 + 陶土橙主色；家庭资产模块单独回到克制专业蓝
   ============================================================ */
page {
  --bg: #FBF7F2;
  --card: #FFFFFF;
  --ink: #2F2A26;
  --ink2: #6B625A;
  --ink3: #9C9187;
  --line: #EDE3D8;
  --line2: #F6EFE7;
  --brand: #D97742;
  --brand-d: #B85C2E;
  --brand-l: #FDF1E7;
  /* 选中态：比 --brand-l 更实一点，避免在米白底上看不出边界 */
  --brand-sel: #FBE3D1;
  --brand-bd: #E5A070;
  --gold: #E8A33D;
  --ok: #3F8F6D;
  --ok-l: #EAF5F0;
  --warn: #C9861F;
  --warn-l: #FDF4E3;
  --danger: #C0555F;
  --danger-l: #FBEEF0;
  --info: #5B7FA6;
  --info-l: #EEF3F8;

  background: var(--bg);
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', sans-serif;
  color: var(--ink);
  font-size: 28rpx;
}

/* #ifdef H5 */
/* H5 全端隐藏原生 TabBar，改用 CustomTab 组件；
   ≥768px 时 CustomTab 自身隐藏，改用 WebLayout 顶部导航 */
uni-tabbar, .uni-tabbar, .uni-tabbar-bottom, .custom-tab-bar { display: none !important; }
/* #endif */

.page { min-height: 100vh; padding: 24rpx; box-sizing: border-box; }

.card {
  background: var(--card);
  border-radius: 24rpx;
  padding: 32rpx;
  margin-bottom: 24rpx;
  border: 1rpx solid var(--line2);
  box-shadow: 0 2rpx 12rpx rgba(47, 42, 38, 0.04);
}

.btn-primary {
  background: var(--brand);
  color: #fff;
  border-radius: 44rpx;
  font-size: 30rpx;
  height: 88rpx;
  line-height: 88rpx;
  text-align: center;
  border: none;
}
.btn-primary::after { border: none; }
.btn-primary[disabled] { background: #DCC8B8; color: #fff; }

.btn-ghost {
  background: var(--line2);
  color: var(--ink2);
  border-radius: 44rpx;
  font-size: 28rpx;
  height: 80rpx;
  line-height: 80rpx;
  text-align: center;
  border: none;
}
.btn-ghost::after { border: none; }

/* 顶部 segment 切换（📅日历 / 📋记录 这一类） */
.segment {
  display: flex; background: var(--line2); border-radius: 9999rpx;
  padding: 6rpx; margin-bottom: 24rpx;
}
.seg-item {
  flex: 1; display: flex; align-items: center; justify-content: center;
  gap: 8rpx; height: 68rpx; border-radius: 9999rpx;
  color: var(--ink3); font-size: 28rpx;
}
.seg-item.on {
  background: #fff; color: var(--brand-d); font-weight: 600;
  box-shadow: 0 2rpx 8rpx rgba(47, 42, 38, 0.08);
}

/* 类型徽章（账本 / 旅游 / 大事件 / 日子 / 资产盘点） */
.chip {
  display: inline-block; font-size: 20rpx; padding: 4rpx 14rpx;
  border-radius: 8rpx; line-height: 1.6; font-weight: 500;
  background: var(--line2); color: var(--ink2);
}
.chip-ledger { background: var(--brand-l); color: var(--brand-d); }
.chip-trip { background: var(--ok-l); color: var(--ok); }
.chip-event { background: var(--info-l); color: var(--info); }
.chip-countdown { background: var(--warn-l); color: var(--warn); }
.chip-asset { background: #EEF3F8; color: #4A6C8C; }

/* 空状态：玩梗只出现在情绪位（数据位零玩梗） */
.empty {
  text-align: center; color: var(--ink3);
  padding: 100rpx 40rpx; font-size: 26rpx;
}
.empty-title { display: block; font-size: 30rpx; color: var(--ink2); margin-bottom: 16rpx; line-height: 1.7; }
.empty-sub { display: block; font-size: 24rpx; color: var(--ink3); line-height: 1.7; }

.loading-text { display: block; text-align: center; color: var(--ink3); padding: 100rpx 0; font-size: 26rpx; }

.section-title {
  font-size: 28rpx; font-weight: 600; color: var(--ink);
  margin: 8rpx 4rpx 20rpx;
  display: flex; align-items: center; justify-content: space-between;
}
.section-extra { font-size: 24rpx; color: var(--ink3); font-weight: 400; }

.text-muted { color: var(--ink3); font-size: 24rpx; }
.text-ok { color: var(--ok); font-weight: 600; }
.text-danger { color: var(--danger); font-weight: 600; }

/* 底部弹层通用 */
.sheet-mask {
  position: fixed; inset: 0; background: rgba(47, 42, 38, 0.42);
  z-index: 1000; display: flex; align-items: flex-end;
}
.sheet {
  width: 100%; background: #fff; border-radius: 32rpx 32rpx 0 0;
  padding: 36rpx 32rpx calc(36rpx + env(safe-area-inset-bottom));
  box-sizing: border-box; max-height: 88vh; overflow-y: auto;
}
.sheet-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 28rpx;
}
.sheet-title { font-size: 34rpx; font-weight: 700; color: var(--ink); }
.sheet-close { font-size: 36rpx; color: var(--ink3); padding: 0 8rpx; }

/* 表单 */
.field { padding: 20rpx 0; border-bottom: 1rpx solid var(--line2); }
.field:last-child { border-bottom: none; }
.f-label { display: block; font-size: 24rpx; color: var(--ink3); margin-bottom: 12rpx; }
.f-input {
  width: 100%; font-size: 30rpx; height: 48rpx; color: var(--ink);
  background: transparent;
}
.f-row { display: flex; align-items: center; gap: 16rpx; }

/* 市场徽章（保留原投资模块口径） */
.tag {
  display: inline-block; font-size: 20rpx; padding: 4rpx 16rpx;
  border-radius: 8rpx; line-height: 1.6; font-weight: 500;
}
.tag-a { background: #fef2f2; color: #dc2626; }
.tag-us { background: #eff6ff; color: #2563eb; }
.tag-hk { background: #ecfdf5; color: #059669; }
.tag-fund { background: #fffbeb; color: #d97706; }
.tag-bond { background: #f5f3ff; color: #7c3aed; }

.form-row {
  display: flex; align-items: center;
  padding: 24rpx 0; border-bottom: 1rpx solid var(--line2);
}
.form-label { width: 180rpx; color: var(--ink2); font-size: 28rpx; flex-shrink: 0; }
.form-input { flex: 1; font-size: 28rpx; text-align: right; }
</style>
