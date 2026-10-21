/**
 * 「发现」工具集：全部为纯前端计算，不需要后端。
 * 新增一个工具 = 往 TOOLS 里加一条配置（fields + compute），
 * 列表页与详情页都自动生效，无需改模板。
 */

/** 金额：千分位 + 两位小数 */
export function money(n) {
  if (!isFinite(n)) return '—'
  return Number(n).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

/** 数字：最多一位小数，千分位 */
export function num(n, digits = 1) {
  if (!isFinite(n)) return '—'
  return Number(n).toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function n(v) {
  const x = Number(v)
  return isFinite(x) ? x : 0
}

/** 等额本息月供 */
function monthlyEqualInstallment(principal, monthRate, months) {
  if (months <= 0) return 0
  if (monthRate <= 0) return principal / months
  const p = Math.pow(1 + monthRate, months)
  return (principal * monthRate * p) / (p - 1)
}

/** 剩余本金（等额本息，按期数模拟） */
function balanceAfter(principal, monthRate, months, paidMonths) {
  const m = monthlyEqualInstallment(principal, monthRate, months)
  let bal = principal
  for (let i = 0; i < paidMonths && i < months; i++) {
    const interest = bal * monthRate
    bal = bal - (m - interest)
  }
  return Math.max(0, bal)
}

/** 个税月度税率表（速算扣除数） */
function monthlyBracket(taxable) {
  const brackets = [
    [3000, 0.03, 0], [12000, 0.1, 210], [25000, 0.2, 1410],
    [35000, 0.25, 2660], [55000, 0.3, 4410], [80000, 0.35, 7160],
    [Infinity, 0.45, 15160],
  ]
  for (const b of brackets) {
    if (taxable <= b[0]) return b
  }
  return brackets[brackets.length - 1]
}

function monthlyTax(taxable) {
  const [, rate, deduct] = monthlyBracket(taxable)
  return Math.max(0, taxable * rate - deduct)
}

/** 年度综合所得税率表（速算扣除数） */
function annualTax(taxable) {
  const brackets = [
    [36000, 0.03, 0], [144000, 0.1, 2520], [300000, 0.2, 16920],
    [420000, 0.25, 31920], [660000, 0.3, 52920], [960000, 0.35, 85920],
    [Infinity, 0.45, 181920],
  ]
  for (const [cap, rate, deduct] of brackets) {
    if (taxable <= cap) return Math.max(0, taxable * rate - deduct)
  }
  return 0
}

/** 经济补偿月数：满一年 1 个月，满半年不满一年按 1 年，不满半年按 0.5 个月 */
function severanceMonths(years) {
  if (years <= 0) return 0
  const full = Math.floor(years)
  const rest = years - full
  if (rest >= 0.5) return full + 1
  return rest > 0 ? full + 0.5 : full
}

export const TOOL_GROUPS = [
  { key: 'work', label: '工作', emoji: '💼', desc: '把工资折算成你真正付出的时间' },
  { key: 'money', label: '钱', emoji: '💰', desc: '月供、到手、还要攒多久' },
  { key: 'life', label: '生活', emoji: '🏠', desc: '别让房租吃掉全部底气' },
]

export const TOOLS = {
  /* ---------------- 工作 ---------------- */
  hourly: {
    key: 'hourly',
    name: '工作性价比',
    emoji: '⏱️',
    group: 'work',
    desc: '扣掉通勤和加班，你的真实时薪是多少',
    note: '按「到手收入」计算。通勤只算往返时间，加班按实际投入小时数计入。',
    fields: [
      { key: 'income', label: '月到手收入', type: 'number', default: 12000, suffix: '元' },
      { key: 'days', label: '每月工作天数', type: 'number', default: 22, suffix: '天' },
      { key: 'hours', label: '每天在岗小时', type: 'number', default: 8, suffix: '小时' },
      { key: 'commute', label: '每天通勤往返', type: 'number', default: 60, suffix: '分钟' },
      { key: 'ot', label: '每月加班', type: 'number', default: 20, suffix: '小时' },
      { key: 'selfCost', label: '每月工作自费', type: 'number', default: 600, suffix: '元', hint: '通勤、外卖、咖啡等因上班产生的开销' },
    ],
    compute(v) {
      const income = n(v.income)
      const days = n(v.days)
      const hours = n(v.hours)
      const commuteH = (n(v.commute) / 60) * days
      const ot = n(v.ot)
      const selfCost = n(v.selfCost)

      const totalHours = days * hours + ot + commuteH
      const net = income - selfCost
      const realHourly = totalHours > 0 ? net / totalHours : 0
      const nominalHourly = days * hours > 0 ? income / (days * hours) : 0
      const gap = nominalHourly > 0 ? (1 - realHourly / nominalHourly) * 100 : 0
      const yearlyHours = totalHours * 12
      const yearlyDays = yearlyHours / 8

      let verdict = ''
      if (realHourly < 20) verdict = '这个数字，比奶茶店的时薪还低。'
      else if (realHourly < 40) verdict = '正常打工人水平，别细想。'
      else if (realHourly < 80) verdict = '还行，时间卖得不算亏。'
      else verdict = '这个时薪，已经赢过大部分人了。'

      return {
        primary: { label: '真实时薪', value: `¥${money(realHourly)}`, tone: 'brand' },
        rows: [
          { label: '名义时薪（不算通勤加班）', value: `¥${money(nominalHourly)}` },
          { label: '时薪缩水', value: `${num(gap)}%` },
          { label: '每月真实投入', value: `${num(totalHours)} 小时` },
          { label: '一年在工作上', value: `${num(yearlyHours, 0)} 小时 · 约 ${num(yearlyDays, 0)} 个工作日` },
          { label: '每月工作自费', value: `¥${money(selfCost)}` },
        ],
        verdict,
      }
    },
  },

  overtime: {
    key: 'overtime',
    name: '加班费折算',
    emoji: '🌙',
    group: 'work',
    desc: '算算你这个月加班该拿多少，公司又给了多少',
    note: '法定折算：日薪 = 月薪 ÷ 21.75，时薪 = 日薪 ÷ 8。工作日 1.5 倍、休息日 2 倍、法定节假日 3 倍。',
    fields: [
      { key: 'salary', label: '月薪', type: 'number', default: 12000, suffix: '元' },
      { key: 'type', label: '加班类型', type: 'select', default: 'workday', options: [
        { value: 'workday', label: '工作日 1.5 倍' },
        { value: 'weekend', label: '休息日 2 倍' },
        { value: 'holiday', label: '法定节假日 3 倍' },
      ] },
      { key: 'hours', label: '加班时长', type: 'number', default: 20, suffix: '小时' },
      { key: 'paid', label: '实际拿到 / 折算', type: 'number', default: 0, suffix: '元', hint: '公司用调休或补贴抵掉的金额，没有就填 0' },
    ],
    compute(v) {
      const salary = n(v.salary)
      const hours = n(v.hours)
      const paid = n(v.paid)
      const rate = v.type === 'holiday' ? 3 : v.type === 'weekend' ? 2 : 1.5
      const dayPay = salary / 21.75
      const hourPay = dayPay / 8
      const should = hourPay * rate * hours
      const gap = should - paid
      const verdict = gap > 0
        ? `公司少给了 ¥${money(gap)}，够你吃 ${Math.max(1, Math.floor(gap / 30))} 顿像样的饭。`
        : '该给的都给了，这家公司还算讲究。'
      return {
        primary: { label: '应得加班费', value: `¥${money(should)}`, tone: 'brand' },
        rows: [
          { label: '小时工资', value: `¥${money(hourPay)}` },
          { label: '加班倍率', value: `${rate} 倍` },
          { label: '加班时长', value: `${num(hours)} 小时` },
          { label: '实际拿到', value: `¥${money(paid)}` },
          { label: '差额', value: gap > 0 ? `少给 ¥${money(gap)}` : gap < 0 ? `多给 ¥${money(-gap)}` : '刚好给足' },
        ],
        verdict,
      }
    },
  },

  leave: {
    key: 'leave',
    name: '请假成本',
    emoji: '🏖️',
    group: 'work',
    desc: '请一天假到底亏多少，值不值得',
    note: '按 21.75 天折算日薪，另计入全勤奖与绩效影响（可填 0）。',
    fields: [
      { key: 'salary', label: '月薪', type: 'number', default: 12000, suffix: '元' },
      { key: 'days', label: '请假天数', type: 'number', default: 1, suffix: '天' },
      { key: 'bonus', label: '全勤奖', type: 'number', default: 300, suffix: '元' },
      { key: 'perf', label: '绩效扣减', type: 'number', default: 0, suffix: '元' },
    ],
    compute(v) {
      const salary = n(v.salary)
      const days = n(v.days)
      const dayPay = salary / 21.75
      const lost = dayPay * days + n(v.bonus) + n(v.perf)
      const hours = lost / (dayPay / 8)
      const verdict = days <= 0
        ? '不请假，那没事。'
        : days > 5
          ? '这已经不是请假，是给自己放了个假。'
          : '该休就休，人不是机器。'
      return {
        primary: { label: '这一天假的实际成本', value: `¥${money(lost)}`, tone: 'brand' },
        rows: [
          { label: '日薪', value: `¥${money(dayPay)}` },
          { label: '请假天数', value: `${num(days)} 天` },
          { label: '全勤奖损失', value: `¥${money(n(v.bonus))}` },
          { label: '绩效扣减', value: `¥${money(n(v.perf))}` },
          { label: '折算成工时', value: `${num(hours)} 小时` },
        ],
        verdict,
      }
    },
  },

  commute: {
    key: 'commute',
    name: '通勤年账',
    emoji: '🚇',
    group: 'work',
    desc: '一年有多少时间被消耗在路上',
    note: '按往返路程计算，折算工作日以 8 小时/天 计。',
    fields: [
      { key: 'oneway', label: '单程时间', type: 'number', default: 45, suffix: '分钟' },
      { key: 'days', label: '每月通勤天数', type: 'number', default: 22, suffix: '天' },
      { key: 'years', label: '还要通勤多少年', type: 'number', default: 20, suffix: '年' },
    ],
    compute(v) {
      const oneway = n(v.oneway)
      const days = n(v.days)
      const years = n(v.years)
      const daily = oneway * 2
      const monthly = (daily * days) / 60
      const yearly = monthly * 12
      const workdays = yearly / 8
      const total = yearly * years
      const verdict = yearly >= 500
        ? `一年 ${num(yearly, 0)} 小时，相当于多上班 ${num(workdays, 0)} 天。`
        : '通勤还算轻，珍惜。'
      return {
        primary: { label: '每年在路上', value: `${num(yearly, 0)} 小时`, tone: 'brand' },
        rows: [
          { label: '每天往返', value: `${num(daily, 0)} 分钟` },
          { label: '每月', value: `${num(monthly, 0)} 小时` },
          { label: '折合工作日', value: `${num(workdays, 1)} 天/年` },
          { label: `未来 ${num(years, 0)} 年合计`, value: `${num(total, 0)} 小时` },
          { label: `未来 ${num(years, 0)} 年折合`, value: `${num(total / 8, 0)} 个工作日` },
        ],
        verdict,
      }
    },
  },

  leaveCost: {
    key: 'leaveCost',
    name: '离职成本',
    emoji: '🚪',
    group: 'work',
    desc: '裸辞之前，先算算公司该给你多少',
    note: '经济补偿按 N 计算（满 1 年 1 个月，满半年不满 1 年按 1 年，不满半年按 0.5 个月）；未休年假按日薪 200% 额外折算。劳动法规定补偿基数有 3 倍社平工资封顶，此处未设上限。',
    fields: [
      { key: 'salary', label: '离职前月薪', type: 'number', default: 12000, suffix: '元' },
      { key: 'years', label: '工作年限', type: 'number', default: 3, suffix: '年', hint: '不满一年可以填小数，如 0.7' },
      { key: 'notice', label: '是否给代通知金', type: 'select', default: 'yes', options: [
        { value: 'yes', label: '未提前 30 天通知（N+1）' },
        { value: 'no', label: '提前 30 天通知（N）' },
      ] },
      { key: 'leave', label: '未休年假', type: 'number', default: 5, suffix: '天' },
    ],
    compute(v) {
      const salary = n(v.salary)
      const years = n(v.years)
      const leave = n(v.leave)
      const months = severanceMonths(years)
      const severance = months * salary
      const notice = v.notice === 'yes' ? salary : 0
      const daily = salary / 21.75
      const leavePay = leave * daily * 2
      const total = severance + notice + leavePay
      const totalMonths = salary > 0 ? total / salary : 0

      return {
        primary: { label: '应得合计', value: `¥${money(total)}`, tone: 'info' },
        rows: [
          { label: `经济补偿（N=${num(months, 1)}）`, value: `¥${money(severance)}` },
          { label: '代通知金', value: notice ? `¥${money(notice)}` : '不需要' },
          { label: '未休年假折算（额外 200%）', value: `¥${money(leavePay)}` },
          { label: '折合几个月工资', value: `${num(totalMonths, 1)} 个月` },
        ],
        verdict: totalMonths >= 3
          ? '这笔钱够你体面地找下一份工作。'
          : '不算多，辞职前先把下一份定下来。',
      }
    },
  },

  raise: {
    key: 'raise',
    name: '涨薪跑赢通胀没',
    emoji: '📈',
    group: 'work',
    desc: '涨的那点钱，到底是真的涨了还是没涨',
    note: '实际涨幅 =（1+名义涨幅）÷（1+通胀率）-1，反映购买力变化。',
    fields: [
      { key: 'before', label: '涨薪前月薪', type: 'number', default: 10000, suffix: '元' },
      { key: 'after', label: '涨薪后月薪', type: 'number', default: 12000, suffix: '元' },
      { key: 'inflation', label: '年通胀率', type: 'number', default: 2.5, suffix: '%' },
    ],
    compute(v) {
      const before = n(v.before)
      const after = n(v.after)
      const inflation = n(v.inflation) / 100
      const nominal = before > 0 ? (after - before) / before : 0
      const real = (1 + nominal) / (1 + inflation) - 1
      const diff = after - before
      const doubleYears = nominal > 0 ? Math.log(2) / Math.log(1 + nominal) : Infinity

      return {
        primary: {
          label: '实际购买力变化',
          value: `${real >= 0 ? '+' : ''}${num(real * 100)}%`,
          tone: real <= 0 ? 'danger' : real < 0.03 ? 'warn' : 'ok',
        },
        rows: [
          { label: '名义涨幅', value: `+${num(nominal * 100)}%` },
          { label: '每月多拿', value: `¥${money(diff)}` },
          { label: '一年实际多拿（扣通胀）', value: `¥${money(diff * 12 * (1 - inflation))}` },
          { label: '按此速度工资翻倍', value: isFinite(doubleYears) ? `${num(doubleYears)} 年` : '—' },
        ],
        verdict: real <= 0
          ? '名义涨了，实际没涨，甚至还倒退了。'
          : real < 0.03
            ? '涨幅刚够抵消通胀，等于原地踏步。'
            : '跑赢了通胀，这涨薪是真的。',
      }
    },
  },

  /* ---------------- 钱 ---------------- */
  mortgage: {
    key: 'mortgage',
    name: '房贷计算',
    emoji: '🏠',
    group: 'money',
    desc: '月供、总利息，以及提前还款能省多少',
    note: '商业贷款通用算法；提前还款按「减少月供、期限不变」重算。',
    fields: [
      { key: 'principal', label: '贷款总额', type: 'number', default: 1000000, suffix: '元' },
      { key: 'rate', label: '年利率', type: 'number', default: 3.0, suffix: '%' },
      { key: 'years', label: '贷款年限', type: 'number', default: 30, suffix: '年' },
      { key: 'method', label: '还款方式', type: 'select', default: 'equal', options: [
        { value: 'equal', label: '等额本息' },
        { value: 'principal', label: '等额本金' },
      ] },
      { key: 'prepay', label: '提前还款金额', type: 'number', default: 0, suffix: '元', hint: '不提前还款填 0' },
      { key: 'prepayYear', label: '第几年提前还', type: 'number', default: 0, suffix: '年' },
    ],
    compute(v) {
      const P = n(v.principal)
      const rate = n(v.rate) / 100 / 12
      const years = n(v.years)
      const months = Math.round(years * 12)
      const prepay = n(v.prepay)
      const prepayYear = n(v.prepayYear)
      const isEqual = v.method !== 'principal'

      let monthly = 0
      let totalInterest = 0
      let monthlyText = ''

      if (isEqual) {
        monthly = monthlyEqualInstallment(P, rate, months)
        totalInterest = monthly * months - P
        monthlyText = `¥${money(monthly)}`
      } else {
        const principalPart = months > 0 ? P / months : 0
        const first = principalPart + P * rate
        totalInterest = P * rate * (months + 1) / 2
        monthlyText = `¥${money(first)} 起，逐月递减 ¥${money(principalPart * rate)}`
      }

      const rows = [
        { label: '还款月数', value: `${months} 期` },
        { label: '总利息', value: `¥${money(totalInterest)}` },
        { label: '本息合计', value: `¥${money(P + totalInterest)}` },
      ]

      // 提前还款：计算剩余本金后按剩余期限重算，得到节省的利息
      if (isEqual && prepay > 0 && prepayYear > 0 && prepayYear < years) {
        const paid = Math.round(prepayYear * 12)
        const bal = balanceAfter(P, rate, months, paid)
        const newBal = Math.max(0, bal - prepay)
        const remain = months - paid
        const newMonthly = monthlyEqualInstallment(newBal, rate, remain)
        const newTotalInterest = newMonthly * remain - newBal
        const paidInterest = monthly * paid - (P - bal)
        const saved = totalInterest - paidInterest - newTotalInterest
        rows.push({ label: '提前还款时剩余本金', value: `¥${money(bal)}` },
          { label: '还款后月供', value: `¥${money(newMonthly)}` },
          { label: '节省利息', value: `¥${money(saved)}` })
      }

      const verdict = totalInterest > P
        ? '利息比本金还多，这就是三十年。'
        : totalInterest > P * 0.5
          ? '利息不算少，能提前还一点是一点。'
          : '利率友好，压力可控。'

      return {
        primary: {
          label: isEqual ? '每月月供' : '首月月供',
          value: monthlyText,
          tone: 'info',
        },
        rows,
        verdict,
      }
    },
  },

  salary: {
    key: 'salary',
    name: '税前税后',
    emoji: '🧾',
    group: 'money',
    desc: '税前写着多少，到手到底多少',
    note: '按个人缴纳部分估算：养老 8%、医疗 2%、失业 0.5%，公积金比例可调；个税按月度税率表速算。',
    fields: [
      { key: 'gross', label: '税前月薪', type: 'number', default: 15000, suffix: '元' },
      { key: 'base', label: '社保公积金基数', type: 'number', default: 15000, suffix: '元', hint: '多数公司按税前工资，也有按最低基数' },
      { key: 'fund', label: '公积金个人比例', type: 'number', default: 7, suffix: '%' },
    ],
    compute(v) {
      const gross = n(v.gross)
      const base = n(v.base) || gross
      const fundRate = n(v.fund) / 100
      const social = base * (0.08 + 0.02 + 0.005)
      const fund = base * fundRate
      const taxable = Math.max(0, gross - social - fund - 5000)
      const tax = monthlyTax(taxable)
      const net = gross - social - fund - tax
      const ratio = gross > 0 ? (net / gross) * 100 : 0

      return {
        primary: { label: '到手', value: `¥${money(net)}`, tone: 'ok' },
        rows: [
          { label: '五险个人部分', value: `¥${money(social)}` },
          { label: '公积金个人部分', value: `¥${money(fund)}` },
          { label: '个人所得税', value: `¥${money(tax)}` },
          { label: '到手比例', value: `${num(ratio)}%` },
          { label: '一年到手', value: `¥${money(net * 12)}` },
        ],
        verdict: ratio < 70
          ? '扣掉的这一大块，都在为将来的你打工。'
          : '到手比例还不错。',
      }
    },
  },

  savings: {
    key: 'savings',
    name: '攒够要多久',
    emoji: '🎯',
    group: 'money',
    desc: '目标还差多少，还要几个月',
    note: '年化收益按简单月复利估算，填 0 即纯靠存。',
    fields: [
      { key: 'target', label: '目标金额', type: 'number', default: 100000, suffix: '元' },
      { key: 'current', label: '已有存款', type: 'number', default: 20000, suffix: '元' },
      { key: 'monthly', label: '每月能存', type: 'number', default: 3000, suffix: '元' },
      { key: 'rate', label: '年化收益', type: 'number', default: 0, suffix: '%' },
    ],
    compute(v) {
      const target = n(v.target)
      const current = n(v.current)
      const monthly = n(v.monthly)
      const r = n(v.rate) / 100 / 12
      const gap = Math.max(0, target - current)

      let months = 0
      if (gap <= 0) months = 0
      else if (monthly <= 0 && r <= 0) months = Infinity
      else if (r <= 0) months = Math.ceil(gap / monthly)
      else {
        // 逐月模拟，最多 1200 个月
        let bal = current
        while (bal < target && months < 1200) {
          bal = bal * (1 + r) + monthly
          months++
        }
      }

      let when = '—'
      if (isFinite(months) && months > 0) {
        const d = new Date()
        d.setMonth(d.getMonth() + months)
        when = `${d.getFullYear()} 年 ${d.getMonth() + 1} 月`
      } else if (months === 0) {
        when = '已经到了'
      }

      return {
        primary: {
          label: months === 0 ? '目标已达成' : isFinite(months) ? '还需要' : '按当前存法',
          value: months === 0 ? '🎉' : isFinite(months) ? `${months} 个月` : '存不到',
          tone: 'brand',
        },
        rows: [
          { label: '还差', value: `¥${money(gap)}` },
          { label: '预计达成', value: when },
          { label: '目标进度', value: `${num(target > 0 ? Math.min(100, (current / target) * 100) : 100)}%` },
          { label: '总投入本金', value: isFinite(months) ? `¥${money(monthly * months)}` : '—' },
        ],
        verdict: months === 0
          ? '目标已经达成，可以看看下一个了。'
          : !isFinite(months)
            ? '每月能存的钱是 0，先解决这个。'
            : months > 60
              ? '五年以上，慢慢来，别急。'
              : '这个节奏，够得着。',
      }
    },
  },

  runway: {
    key: 'runway',
    name: '离职续航',
    emoji: '🔋',
    group: 'money',
    desc: '裸辞之后，你的存款能撑几个月',
    note: '不含利息与通胀；副业收入按每月固定值估算。',
    fields: [
      { key: 'saving', label: '可动用存款', type: 'number', default: 50000, suffix: '元' },
      { key: 'cost', label: '每月支出', type: 'number', default: 6000, suffix: '元' },
      { key: 'side', label: '副业月收入', type: 'number', default: 0, suffix: '元' },
    ],
    compute(v) {
      const saving = n(v.saving)
      const cost = n(v.cost)
      const side = n(v.side)
      const netBurn = cost - side
      const months = netBurn > 0 ? saving / netBurn : Infinity

      let until = '—'
      if (isFinite(months)) {
        const d = new Date()
        d.setMonth(d.getMonth() + Math.floor(months))
        until = `${d.getFullYear()} 年 ${d.getMonth() + 1} 月`
      }

      return {
        primary: {
          label: '能撑',
          value: isFinite(months) ? `${num(months)} 个月` : '无限',
          tone: months >= 6 ? 'ok' : months >= 3 ? 'warn' : 'danger',
        },
        rows: [
          { label: '每月净消耗', value: `¥${money(Math.max(0, netBurn))}` },
          { label: '存款耗尽', value: until },
          { label: '建议安全垫（6 个月）', value: `¥${money(cost * 6)}` },
          { label: '当前缺口', value: `¥${money(Math.max(0, cost * 6 - saving))}` },
        ],
        verdict: !isFinite(months)
          ? '副业已经覆盖支出，你自由了。'
          : months < 3
            ? '不到三个月，别冲动。'
            : months < 6
              ? '能撑一阵，但简历要开始投了。'
              : '底气够，可以慢慢挑。',
      }
    },
  },

  savingProgress: {
    key: 'savingProgress',
    name: '年度攒钱进度',
    emoji: '🏦',
    group: 'money',
    desc: '今年的钱存下来多少，离目标还差多少',
    note: '自动读取你在「账本」里记的今年收入与支出，结余视为存款；没有记账时用手动填写。',
    source: 'ledger',
    fields: [
      { key: 'target', label: '今年想存', type: 'number', default: 60000, suffix: '元' },
      { key: 'saved', label: '已存（无记账时填）', type: 'number', default: 0, suffix: '元', hint: '有账本记录时自动读取，不用填' },
    ],
    compute(v, ctx) {
      const target = n(v.target)
      const ledger = ctx && ctx.ledger
      const saved = ledger ? Math.max(0, ledger.net) : n(v.saved)
      const progress = target > 0 ? (saved / target) * 100 : (saved > 0 ? 100 : 0)
      const remain = Math.max(0, target - saved)
      const monthsPassed = new Date().getMonth() + 1
      const avg = ledger && ledger.months > 0
        ? ledger.net / ledger.months
        : saved / monthsPassed
      const forecast = avg * 12

      const rows = [
        { label: '已存', value: `¥${money(saved)}` },
        { label: '还差', value: `¥${money(remain)}` },
        { label: '月均结余', value: `¥${money(avg)}` },
        { label: '按当前节奏到年底', value: `¥${money(forecast)}` },
      ]
      if (ledger) {
        rows.push({ label: '账本数据（今年）', value: `收入 ¥${money(ledger.income)} · 支出 ¥${money(ledger.expense)}` })
      }

      let tone = 'warn'
      if (target <= 0 || progress >= 100 || forecast >= target) tone = 'ok'
      else if (avg <= 0) tone = 'danger'

      return {
        primary: { label: '年度目标进度', value: `${num(Math.min(progress, 999), 0)}%`, tone },
        rows,
        verdict: progress >= 100
          ? '目标已经完成，剩下的都是惊喜。'
          : avg <= 0
            ? '今年还没存下钱，先看看账本里的支出。'
            : forecast >= target
              ? '按现在的节奏，年底能达成。'
              : `按现在的节奏，年底差 ¥${money(target - forecast)}。`,
      }
    },
  },

  insurance: {
    key: 'insurance',
    name: '五险一金明细',
    emoji: '🩺',
    group: 'money',
    desc: '每月扣的社保公积金，到底去哪了',
    note: '个人比例：养老 8%、医疗 2%、失业 0.5%、公积金可选；公司比例按常见口径估算（养老 16%、医疗 9.5%、失业 0.5%、工伤 0.2%、生育 0.8%）。各地略有差异。',
    fields: [
      { key: 'base', label: '缴费基数', type: 'number', default: 15000, suffix: '元', hint: '通常等于月薪，也可能按最低基数' },
      { key: 'fund', label: '公积金比例', type: 'number', default: 7, suffix: '%', hint: '个人与公司同比例，常见 5%~12%' },
    ],
    compute(v) {
      const base = n(v.base)
      const fundRate = n(v.fund) / 100
      const pension = base * 0.08
      const medical = base * 0.02
      const unemployment = base * 0.005
      const fund = base * fundRate
      const personal = pension + medical + unemployment + fund
      const company = base * (0.16 + 0.095 + 0.005 + 0.002 + 0.008 + fundRate)
      const account = pension + fund * 2

      return {
        primary: { label: '每月个人扣款', value: `¥${money(personal)}`, tone: 'info' },
        rows: [
          { label: '养老（个人 8%）', value: `¥${money(pension)}` },
          { label: '医疗（个人 2%）', value: `¥${money(medical)}` },
          { label: '失业（个人 0.5%）', value: `¥${money(unemployment)}` },
          { label: `公积金（个人 ${num(n(v.fund), 0)}%）`, value: `¥${money(fund)}` },
          { label: '公司为你额外缴', value: `¥${money(company)}` },
          { label: '每月进你账户', value: `¥${money(account)}` },
        ],
        verdict: n(v.fund) >= 12
          ? '公积金顶格缴，这待遇不错。'
          : n(v.fund) >= 7
            ? '公积金中等偏上，能提就提。'
            : '公积金比例偏低，相当于变相降薪。',
      }
    },
  },

  bonusTax: {
    key: 'bonusTax',
    name: '年终奖个税',
    emoji: '🧨',
    group: 'money',
    desc: '单独计税还是并入综合所得，哪个更省',
    note: '单独计税政策延续至 2027 年 12 月 31 日。年度应纳税所得额 = 年收入 - 6 万 - 三险一金 - 专项附加扣除。',
    fields: [
      { key: 'bonus', label: '年终奖', type: 'number', default: 30000, suffix: '元' },
      { key: 'annualTaxable', label: '年度应纳税所得额', type: 'number', default: 100000, suffix: '元', hint: '不算年终奖的部分，不知道可填工资×12 粗略值' },
    ],
    compute(v) {
      const bonus = n(v.bonus)
      const annual = n(v.annualTaxable)
      const [, rate, deduct] = monthlyBracket(bonus / 12)
      const alone = Math.max(0, bonus * rate - deduct)
      const combined = Math.max(0, annualTax(annual + bonus) - annualTax(annual))
      const gap = combined - alone

      return {
        primary: {
          label: gap >= 0 ? '建议单独计税' : '建议并入综合所得',
          value: `省 ¥${money(Math.abs(gap))}`,
          tone: 'ok',
        },
        rows: [
          { label: '单独计税税额', value: `¥${money(alone)}` },
          { label: '并入综合所得税额', value: `¥${money(combined)}` },
          { label: '奖金对应税率', value: `${num(rate * 100, 0)}%` },
          { label: '税后到手（较优方式）', value: `¥${money(bonus - Math.min(alone, combined))}` },
        ],
        verdict: gap > 0
          ? '单独计税更划算，申报时记得勾这个选项。'
          : gap < 0
            ? '并进工资更划算，别多交这笔税。'
            : '两种方式税额一样，随便选。',
      }
    },
  },

  /* ---------------- 生活 ---------------- */
  rent: {
    key: 'rent',
    name: '房租收入比',
    emoji: '🏘️',
    group: 'life',
    desc: '你每个月有多少是在给房东打工',
    note: '按到手收入计算，不含水电物业。',
    fields: [
      { key: 'rent', label: '月租金', type: 'number', default: 3000, suffix: '元' },
      { key: 'income', label: '月到手收入', type: 'number', default: 12000, suffix: '元' },
    ],
    compute(v) {
      const rent = n(v.rent)
      const income = n(v.income)
      const ratio = income > 0 ? (rent / income) * 100 : 0
      let level = ''
      let tone = 'ok'
      if (ratio < 20) { level = '轻松，住得没压力'; tone = 'ok' }
      else if (ratio < 30) { level = '正常区间'; tone = 'ok' }
      else if (ratio < 40) { level = '有压力，其他开销要省'; tone = 'warn' }
      else { level = '已超过警戒线，房东比你过得好'; tone = 'danger' }

      return {
        primary: { label: '房租占收入', value: `${num(ratio)}%`, tone },
        rows: [
          { label: '每月房租', value: `¥${money(rent)}` },
          { label: '一年房租', value: `¥${money(rent * 12)}` },
          { label: '相当于', value: `${num(rent * 12 / (income || 1))} 个月收入` },
          { label: '每月可支配余额', value: `¥${money(income - rent)}` },
        ],
        verdict: level,
      }
    },
  },

  retire: {
    key: 'retire',
    name: '退休倒计时',
    emoji: '🌇',
    group: 'life',
    desc: '还要干多少年，退休的钱够了没',
    note: '用「4% 法则」估算退休所需本金（年支出 × 25），存款按年化收益月复利增长，不含通胀。',
    fields: [
      { key: 'age', label: '现在的年龄', type: 'number', default: 30, suffix: '岁' },
      { key: 'retireAge', label: '计划退休年龄', type: 'number', default: 60, suffix: '岁' },
      { key: 'saving', label: '现有存款', type: 'number', default: 200000, suffix: '元' },
      { key: 'monthlySave', label: '每月能存', type: 'number', default: 3000, suffix: '元' },
      { key: 'cost', label: '退休后月支出', type: 'number', default: 6000, suffix: '元' },
      { key: 'rate', label: '年化收益', type: 'number', default: 3, suffix: '%' },
    ],
    compute(v) {
      const age = n(v.age)
      const retireAge = n(v.retireAge)
      const saving = n(v.saving)
      const monthly = n(v.monthlySave)
      const cost = n(v.cost)
      const r = n(v.rate) / 100 / 12
      const years = Math.max(0, retireAge - age)
      const months = Math.round(years * 12)
      const growth = Math.pow(1 + r, months)
      const atRetire = saving * growth + (r > 0 ? monthly * ((growth - 1) / r) : monthly * months)
      const need = cost * 12 * 25
      const gap = Math.max(0, need - atRetire)
      const needMonthly = gap > 0 && months > 0
        ? (r > 0 ? (gap * r) / (growth - 1) : gap / months)
        : 0
      const coverage = need > 0 ? atRetire / need : 1

      return {
        primary: {
          label: '距离退休',
          value: `${num(years, 0)} 年`,
          tone: coverage >= 1 ? 'ok' : coverage >= 0.6 ? 'warn' : 'danger',
        },
        rows: [
          { label: '退休时预计存款', value: `¥${money(atRetire)}` },
          { label: '退休所需本金（25 倍年支出）', value: `¥${money(need)}` },
          { label: gap > 0 ? '还差' : '已覆盖', value: `¥${money(gap > 0 ? gap : atRetire - need)}` },
          { label: '想补上缺口每月要多存', value: gap > 0 ? `¥${money(needMonthly)}` : '不用' },
          { label: '预计退休年份', value: `${new Date().getFullYear() + Math.round(years)} 年` },
        ],
        verdict: coverage >= 1
          ? '按这个节奏，到点就能走。'
          : coverage >= 0.6
            ? '差一截，但还有时间调整。'
            : '照现在这样，退休只是个传说。',
      }
    },
  },

  kids: {
    key: 'kids',
    name: '养娃要多少钱',
    emoji: '🍼',
    group: 'life',
    desc: '从出生到大学毕业，粗略算一笔',
    note: '按你所在的养育方式估算，不含通胀、不含补习班与留学。实际支出通常比这个数字更高。',
    fields: [
      { key: 'baby', label: '0-3 岁每月', type: 'number', default: 3000, suffix: '元' },
      { key: 'school', label: '4-18 岁每月', type: 'number', default: 2000, suffix: '元' },
      { key: 'college', label: '大学每年', type: 'number', default: 30000, suffix: '元' },
    ],
    compute(v) {
      const baby = n(v.baby) * 36
      const school = n(v.school) * 12 * 15
      const college = n(v.college) * 4
      const total = baby + school + college

      return {
        primary: { label: '养到大学毕业', value: `¥${money(total)}`, tone: 'info' },
        rows: [
          { label: '0-3 岁（36 个月）', value: `¥${money(baby)}` },
          { label: '4-18 岁（15 年）', value: `¥${money(school)}` },
          { label: '大学 4 年', value: `¥${money(college)}` },
          { label: '平均每月', value: `¥${money(total / 264)}` },
        ],
        verdict: total > 1000000
          ? '这还没算补习班和买房，先深呼吸。'
          : total > 600000
            ? '一笔不小的数目，早点开始准备。'
            : '按朴素养法算，压力相对可控。',
      }
    },
  },
}

/** 按分组整理，供列表页渲染 */
export function groupedTools() {
  return TOOL_GROUPS.map(g => ({
    ...g,
    tools: Object.values(TOOLS).filter(t => t.group === g.key),
  }))
}
