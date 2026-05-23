<template>
  <div class="realtime-container">
    <div class="top-row">
      <div class="search-box">
        <input
          v-model="searchTerm"
          @input="handleSearchInput"
          @focus="showDropdown = true"
          @keyup.enter="performSearch"
          placeholder="输入基金代码或名称搜索"
          class="search-input"
        />
        <div v-if="showDropdown && searchResults.length > 0" class="search-dropdown-overlay" ref="dropdownRef">
          <div
            v-for="fund in searchResults"
            :key="fund.CODE"
            class="dropdown-item"
            :class="{ selected: isSelected(fund.CODE) }"
            @click="toggleSelectFund(fund)"
          >
            <span class="fund-code">{{ fund.CODE }}</span>
            <span class="fund-name">{{ fund.NAME }}</span>
          </div>
        </div>
      </div>
      <button class="btn btn-primary" @click="batchAddFunds" :disabled="selectedFunds.length === 0">
        添加基金
      </button>
      <div class="sort-box">
        <select v-model="sortBy" class="select-sort">
          <option value="changeDesc">收益率从高到低</option>
          <option value="todayProfitDesc">今日盈亏从高到低</option>
          <option value="todayProfitAsc">今日盈亏从低到高</option>
          <option value="totalProfitDesc">持有收益从高到低</option>
        </select>
      </div>
      <button class="btn btn-blue" @click="exportData">导出数据</button>
      <label class="btn btn-green" for="import-file">导入数据</label>
      <input id="import-file" class="hidden-file" type="file" accept="application/json" @change="importData" />
    </div>

    <!-- Tags Row -->
    <div class="selected-tags-row" v-if="selectedFunds.length > 0">
      <span v-for="fund in selectedFunds" :key="fund.CODE" class="selected-tag" @click="toggleSelectFund(fund)">
        {{ fund.NAME }} <span class="tag-close">x</span>
      </span>
    </div>

    <!-- Overview Box -->
    <div class="overview-box">
      <div class="overview-head">
        <div class="title-with-icon">📊 投资总览</div>
        <div class="meta-info">实时数据来自互联网，仅供参考。数据更新时间: {{ nowTime }}</div>
      </div>
      <div class="overview-grid" v-if="hasHoldings">
        <div class="overview-cell purple">
          <div class="cell-label">总市值</div>
          <div class="cell-val">¥{{ totalAsset.toFixed(2) }}</div>
        </div>
        <div class="overview-cell">
          <div class="cell-label">总成本</div>
          <div class="cell-val">¥{{ totalCost.toFixed(2) }}</div>
        </div>
        <div class="overview-cell">
          <div class="cell-label">总收益</div>
          <div class="cell-val" :class="profitTotalClass">{{ totalProfitTotal >= 0 ? '+' : '' }}¥{{ totalProfitTotal.toFixed(2) }}</div>
        </div>
        <div class="overview-cell">
          <div class="cell-label">收益率</div>
          <div class="cell-val" :class="profitTotalClass">{{ totalReturnRate >= 0 ? '+' : '' }}{{ totalReturnRate.toFixed(2) }}%</div>
        </div>
        <div class="overview-cell">
          <div class="cell-label">今日盈亏</div>
          <div class="cell-val" :class="profitTodayClass">{{ totalProfitToday >= 0 ? '+' : '' }}¥{{ totalProfitToday.toFixed(2) }}</div>
        </div>
        <div class="overview-cell">
          <div class="cell-label">今日收益</div>
          <div class="cell-val" :class="profitTodayClass">{{ todayReturnRate >= 0 ? '+' : '' }}{{ todayReturnRate.toFixed(2) }}%</div>
        </div>
      </div>
      <div v-else class="overview-grid empty-hint">暂未设置持仓</div>
    </div>

    <!-- Tabs -->
    <div class="content-tabs">
      <div class="ctab" :class="{active: activeTab==='holding'}" @click="activeTab='holding'">
        👜 持仓 <span class="badge" v-if="Object.keys(holdings).length">{{ Object.keys(holdings).length }}</span>
      </div>
      <div class="ctab" :class="{active: activeTab==='watch'}" @click="activeTab='watch'">
        👁️ 自选 <span class="badge watch" v-if="funds.length">{{ funds.length }}</span>
      </div>
      <div class="ctab" :class="{active: activeTab==='rebalance'}" @click="activeTab='rebalance'">⚖️ 再平衡管理</div>
      <div class="ctab" :class="{active: activeTab==='dividend'}" @click="activeTab='dividend'">📉 红利低波</div>
    </div>

    <!-- Card Grid -->
    <div class="fund-grid">
      <div v-for="fund in displayFunds" :key="fund.code" class="fund-item-card">
        <div class="card-head">
          <div class="c-title">{{ fund.name }}</div>
          <button class="btn-del" @click.stop="removeFund(fund.code)">删除</button>
        </div>
        <div class="c-tags">
          <span>{{ fund.code }}</span>
          <span class="tag red" v-if="holdings[fund.code]">持仓</span>
          <span class="tag pink">场外</span>
        </div>
        <div class="c-mid-tabs">
          <div
            class="c-tab"
            :class="{ active: true }"
          >
            📈 实时数据
          </div>
          <div
            class="c-tab"
            @click.stop="openFundDetail(fund)"
            title="打开基金详情页"
          >
            📊 基金详情
          </div>
        </div>

        <div class="c-hero">
          <div class="hero-chip" :class="getChangeClass(fund.gszzl)">{{ formatChange(fund.gszzl) }}</div>
          <div class="hero-chip" :class="getHoldingProfitTodayClass(fund)" v-if="holdings[fund.code]">
            {{ getHoldingProfitToday(fund) >= 0 ? '+' : '' }}¥{{ getHoldingProfitToday(fund).toFixed(2) }}
          </div>
          <!-- 有持仓：显示AI建议按钮/结果 -->
          <template v-if="holdings[fund.code]">
            <div
              v-if="adviceMap[fund.code]"
              class="hero-chip ai-advice-badge"
              :style="{ background: actionColor(adviceMap[fund.code].action_type) }"
              :title="adviceMap[fund.code].reason"
            >
              {{ adviceMap[fund.code].action }}
            </div>
            <button
              v-else
              class="hero-chip ai-btn"
              :disabled="adviceLoading[fund.code]"
              @click.stop="fetchAIAdvice(fund)"
            >
              {{ adviceLoading[fund.code] ? 'AI分析中...' : '🤖 AI建议' }}
            </button>
          </template>
          <!-- 无持仓：用规则兜底 -->
          <div v-else class="hero-chip advice-chip" :style="{ background: getFundAdvice(fund).color }">
            {{ getFundAdvice(fund).label }}
          </div>
        </div>

        <div class="c-holdings-area">
          <div class="c-h-head">
            <span class="c-h-title">👜 持仓信息 <span class="c-h-pen">📄 1笔</span></span>
            <div class="c-h-actions">
              <button class="btn-sm b-buy" @click.stop="openTradeModal(fund, 'buy')">买入</button>
              <button class="btn-sm b-sell" @click.stop="openTradeModal(fund, 'sell')">卖出</button>
            </div>
          </div>
          <div class="c-h-grid" v-if="holdings[fund.code]">
            <div class="grid-box">
              <div class="g-label">持有份额</div>
              <div class="g-val">{{ holdings[fund.code].share.toFixed(2) }}</div>
            </div>
            <div class="grid-box">
              <div class="g-label">平均成本</div>
              <div class="g-val">{{ holdings[fund.code].cost.toFixed(4) }}</div>
            </div>
            <div class="grid-box">
              <div class="g-label">当前市值</div>
              <div class="g-val">¥{{ getHoldingEstimatedAmount(fund).toFixed(2) }}</div>
            </div>
            <div class="grid-box">
              <div class="g-label">持仓成本</div>
              <div class="g-val">¥{{ getHoldingAmount(fund).toFixed(2) }}</div>
            </div>
            <div class="grid-box">
              <div class="g-label">收益金额</div>
              <div class="g-val" :class="getHoldingProfitTotalClass(fund)">
                {{ getHoldingProfitTotal(fund) >= 0 ? '+' : '' }}¥{{ getHoldingProfitTotal(fund).toFixed(2) }}
              </div>
            </div>
            <div class="grid-box">
              <div class="g-label">收益率</div>
              <div class="g-val" :class="getHoldingProfitTotalClass(fund)">
                {{ getHoldingAmount(fund) > 0 ? ((getHoldingProfitTotal(fund) / getHoldingAmount(fund)) * 100 >= 0 ? '+' : '') + ((getHoldingProfitTotal(fund) / getHoldingAmount(fund)) * 100).toFixed(2) + '%' : '0.00%' }}
              </div>
            </div>
          </div>
          <div class="c-h-grid empty" v-else>
            <button class="btn-sm b-buy" @click.stop="openHoldingModal(fund)">录入持仓</button>
          </div>
        </div>

        <div class="c-bottom-nav">
          <div class="bn-col">
            <div class="bn-label">单位净值</div>
            <div class="bn-val">{{ getDisplayNav(fund) }}</div>
          </div>
          <div class="bn-col">
            <div class="bn-label">估算值</div>
            <div class="bn-val" :class="getChangeClass(fund.gszzl)">{{ formatGsz(fund) }}</div>
          </div>
        </div>

        <div class="c-chart">
          <svg v-if="getFundMiniChart3m(fund).points.length > 1" viewBox="0 0 110 46" preserveAspectRatio="none" class="c-svg">
            <line class="c-axis" x1="20" y1="28" x2="106" y2="28"></line>
            <line class="c-axis" x1="20" y1="4" x2="20" y2="28"></line>
            <line
              v-for="tick in getFundMiniChart3m(fund).yTicks"
              :key="`grid-${fund.code}-${tick.y}`"
              class="c-grid"
              x1="20"
              :y1="tick.y"
              x2="106"
              :y2="tick.y"
            ></line>
            <path
              class="c-fill"
              :class="getFundMiniChart3m(fund).trendUp ? 'up' : 'down'"
              :d="getSparklineFill(getFundMiniChart3m(fund).points, 28)"
            ></path>
            <path
              class="c-line"
              :class="getFundMiniChart3m(fund).trendUp ? 'up' : 'down'"
              :d="getSparklinePath(getFundMiniChart3m(fund).points)"
            ></path>
            <text
              v-for="tick in getFundMiniChart3m(fund).yTicks"
              :key="`y-${fund.code}-${tick.y}`"
              class="c-y-label"
              x="18"
              :y="tick.y + 1"
              text-anchor="end"
            >{{ tick.label }}</text>
            <text
              v-for="tick in getFundMiniChart3m(fund).xTicks"
              :key="`x-${fund.code}-${tick.x}`"
              class="c-x-label"
              :x="tick.x"
              y="35"
              text-anchor="middle"
            >{{ tick.label }}</text>
          </svg>
          <div v-else class="spark-empty">近3个月暂无走势数据</div>
        </div>

        <div class="c-time">
          更新时间: {{ fund.gztime || '-' }} | 净值日期: {{ fund.jzrq || '-' }}
        </div>
      </div>
    </div>
    
<!-- Modals retained -->
    <div v-if="holdingModal.open" class="modal-overlay" @click.self="closeHoldingModal">
      <div class="modal-box">
        <div class="modal-tabs elegant-tabs">
          <button class="modal-tab" :class="{ active: modalTab === 'set' }" @click="modalTab = 'set'">设置持仓</button>
          <button class="modal-tab" :class="{ active: modalTab === 'trade' }" @click="modalTab = 'trade'">加减仓</button>
        </div>
        <div class="fund-modal-info">
          <span class="fund-name">{{ holdingModal.fund?.name }}</span>
          <span class="fund-code">#{{ holdingModal.fund?.code }}</span>
          <div class="fund-nav-info">
            <span>上一交易日净值：</span>
            <span class="nav-value">{{ holdingModal.fund?.dwjz || '-' }}</span>
            <span class="nav-date" v-if="holdingModal.fund?.jzrq">（{{ holdingModal.fund.jzrq }}）</span>
          </div>
        </div>

        <div v-if="modalTab === 'set'">
          <div class="form-group">
            <label>持有金额 (元)</label>
            <input v-model.number="holdingForm.amount" type="number" step="any" placeholder="请输入持有金额" class="modal-input" />
          </div>
          <div class="form-group">
            <label>买入日期</label>
            <input v-model="holdingForm.buyDate" type="date" class="modal-input" :max="todayDate" />
          </div>
          <div class="modal-actions">
            <button class="btn" @click="closeHoldingModal">取消</button>
            <button class="btn btn-green" @click="saveHolding" :disabled="!holdingForm.amount">保存</button>
          </div>
        </div>

        <div v-if="modalTab === 'trade'" class="elegant-trade-box">
          <div class="trade-toggle">
            <div
              class="trade-toggle-btn buy"
              :class="{ active: tradeForm.type === 'buy' }"
              @click="tradeForm.type = 'buy'"
            >
              加仓买入
            </div>
            <div
              class="trade-toggle-btn sell"
              :class="{ active: tradeForm.type === 'sell' }"
              @click="tradeForm.type = 'sell'"
            >
              减仓卖出
            </div>
          </div>

          <div class="form-group elegant-input-group">
            <label>交易净值</label>
            <div class="input-wrapper">
              <span class="prefix">¥</span>
              <input
                v-model.number="tradeForm.nav"
                type="number"
                step="any"
                placeholder="默认使用上一交易日净值"
                class="modal-input no-border"
              />
            </div>
          </div>

          <div class="form-group elegant-input-group">
            <label>{{ tradeForm.type === 'buy' ? '加仓金额' : '减仓金额' }}</label>
            <div class="input-wrapper">
              <span class="prefix">¥</span>
              <input
                v-model.number="tradeForm.amount"
                type="number"
                step="any"
                :placeholder="tradeForm.type === 'buy' ? '请输入加仓金额' : '请输入减仓金额'"
                class="modal-input no-border highlight"
              />
            </div>
            <div class="trade-inline-hint" v-if="tradeForm.amount && getTradeNav() > 0">
              <span>折算份额 {{ (tradeForm.amount / getTradeNav()).toFixed(2) }} 份</span>
              <span>交易后总份额 {{ getTradeResultShares().toFixed(2) }} 份</span>
              <span class="warning" v-if="getTradeResultShares() < 0">份额不足</span>
            </div>
          </div>

          <div class="modal-actions elegant-actions">
            <button class="elegant-btn-cancel" @click="closeHoldingModal">取消</button>
            <button
              class="elegant-btn-confirm"
              :class="tradeForm.type"
              @click="saveTrade"
              :disabled="!tradeForm.amount || tradeForm.amount <= 0 || getTradeResultShares() < 0"
            >
              确认{{ tradeForm.type === 'buy' ? '加仓' : '减仓' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { fundAPI } from '../services/api'

export default {
  name: 'FundRealtime',
  emits: ['view-detail'],
  setup(props, { emit }) {
    // ==================== 状态 ====================
    const funds = ref([])
    const holdings = ref({})  // { code: { share, cost } }
    const collapsedCodes = ref(new Set())
    const adviceMap = ref({})       // { [code]: { action, action_type, confidence, summary, reason, key_points } }
    const adviceLoading = ref({})   // { [code]: true/false }
    const refreshing = ref(false)
    const refreshMs = ref(30000)
    const searchTerm = ref('')
    const searchResults = ref([])
    const selectedFunds = ref([])
    const showDropdown = ref(false)
    const username = ref('guest')
    const nowTime = ref('--:--')
    const sortBy = ref('changeDesc')
    const activeTab = ref('holding')
    const dropdownRef = ref(null)
    const searchPanelRef = ref(null)
    const searchTimeoutRef = ref(null)
    const refreshTimer = ref(null)
    const timeTimer = ref(null)
    const searchLoading = ref(false)
    const todayDate = ref(new Date().toISOString().slice(0, 10))

    const normalizeFundCode = (code) => {
      const text = String(code || '').trim()
      if (/^\d+$/.test(text) && text.length < 6) {
        return text.padStart(6, '0')
      }
      return text
    }

    // 持仓弹窗
    const holdingModal = ref({ open: false, fund: null })
    const holdingForm = ref({ amount: '', buyDate: todayDate.value })
    const modalTab = ref('set')
    const tradeForm = ref({ type: 'buy', amount: '', nav: '' })

    // ==================== 计算属性 ====================
    const isTradingTime = computed(() => {
      const now = new Date()
      const day = now.getDay()
      if (day === 0 || day === 6) return false
      const h = now.getHours()
      const m = now.getMinutes()
      const minutes = h * 60 + m
      // 9:30 - 11:30, 13:00 - 15:00
      return (minutes >= 570 && minutes <= 690) || (minutes >= 780 && minutes <= 900)
    })

    const metricBySort = (fund, key) => {
      if (key === 'todayProfitDesc' || key === 'todayProfitAsc') return getHoldingProfitToday(fund)
      if (key === 'totalProfitDesc') return getHoldingProfitTotal(fund)
      return typeof fund.gszzl === 'number' ? fund.gszzl : parseFloat(fund.gszzl) || 0
    }

    const sortedFunds = computed(() => {
      const list = [...funds.value]
      list.sort((a, b) => {
        const aVal = metricBySort(a, sortBy.value)
        const bVal = metricBySort(b, sortBy.value)
        if (sortBy.value === 'todayProfitAsc') return aVal - bVal
        return bVal - aVal
      })
      return list
    })

    const displayFunds = computed(() => {
      if (activeTab.value === 'watch') return sortedFunds.value
      if (activeTab.value === 'holding') {
        return sortedFunds.value.filter(f => {
          const h = holdings.value[f.code]
          return !!(h && h.share > 0)
        })
      }
      if (activeTab.value === 'rebalance') {
        return sortedFunds.value.filter(f => {
          const h = holdings.value[f.code]
          if (!h || !h.share) return false
          const amount = getHoldingEstimatedAmount(f)
          if (!amount) return false
          const diffRatio = Math.abs(getHoldingProfitTotal(f) / amount)
          return diffRatio >= 0.08
        })
      }
      if (activeTab.value === 'dividend') {
        return sortedFunds.value.filter(f => /红利|低波|价值|股息|高股息/.test(f.name || ''))
      }
      return sortedFunds.value
    })

    const emptyTitle = computed(() => {
      if (activeTab.value === 'rebalance') return '暂无需要再平衡的基金'
      if (activeTab.value === 'dividend') return '暂无匹配“红利低波”主题的基金'
      return '暂无监控基金'
    })

    const emptyHint = computed(() => {
      if (activeTab.value === 'holding') return '请先添加基金并录入持仓金额'
      if (activeTab.value === 'rebalance') return '当前持仓波动处于合理范围'
      if (activeTab.value === 'dividend') return '请添加名称包含“红利 / 低波 / 股息”等关键词基金'
      return '在上方搜索框中添加基金开始监控'
    })

    const hasHoldings = computed(() => {
      return Object.keys(holdings.value).some(code => 
        funds.value.some(f => f.code === code)
      )
    })

    const totalAsset = computed(() => {
      let total = 0
      funds.value.forEach(fund => {
        const h = holdings.value[fund.code]
        if (h && h.share) {
          total += getHoldingEstimatedAmount(fund)
        }
      })
      return total
    })

    const totalProfitToday = computed(() => {
      let total = 0
      funds.value.forEach(fund => {
        const h = holdings.value[fund.code]
        if (h && h.share) {
          total += getHoldingProfitToday(fund)
        }
      })
      return total
    })

    const totalProfitTotal = computed(() => {
      let total = 0
      funds.value.forEach(fund => {
        const h = holdings.value[fund.code]
        if (h && h.share && h.cost) {
          total += getHoldingProfitTotal(fund)
        }
      })
      return total
    })

    const totalCost = computed(() => {
      let total = 0
      funds.value.forEach(fund => {
        total += getHoldingAmount(fund)
      })
      return total
    })

    const totalReturnRate = computed(() => {
      if (!totalCost.value) return 0
      return (totalProfitTotal.value / totalCost.value) * 100
    })

    const todayReturnRate = computed(() => {
      if (!totalCost.value) return 0
      return (totalProfitToday.value / totalCost.value) * 100
    })

    const profitTodayClass = computed(() => totalProfitToday.value >= 0 ? 'up' : 'down')
    const profitTotalClass = computed(() => totalProfitTotal.value >= 0 ? 'up' : 'down')

    // ==================== 方法 ====================
    const getChangeClass = (val) => {
      const num = typeof val === 'number' ? val : parseFloat(val)
      if (isNaN(num)) return ''
      return num > 0 ? 'up' : num < 0 ? 'down' : ''
    }

    const formatGsz = (fund) => {
      const gsz = fund.gsz || fund.dwjz
      return gsz ? parseFloat(gsz).toFixed(4) : '-'
    }

    const formatChange = (val) => {
      const num = typeof val === 'number' ? val : parseFloat(val)
      if (isNaN(num)) return '-'
      return (num >= 0 ? '+' : '') + num.toFixed(2) + '%'
    }

    // 持仓成本 = 平均成本 × 份额
    const getHoldingAmount = (fund) => {
      const h = holdings.value[fund.code]
      if (!h || !h.share) return 0
      const nav = parseFloat(h.cost) || 0
      return h.share * nav
    }

    // 获取最优净值：走势数据最新 > 今日实时估值 > fundgz 官方净值
    const getBestNav = (fund) => {
      const todayStr = new Date().toISOString().split('T')[0]
      const dwjz = parseFloat(fund.dwjz)    // fundgz 最新公布净值
      const gsz = parseFloat(fund.gsz)       // fundgz 实时估值
      const jzrq = fund.jzrq || ''           // fundgz 净值日期

      // 走势数据（pingzhongdata，通常比 fundgz 的 dwjz 更新）
      const trend = getFundTrendSeries(fund)
      let trendNav = 0
      let trendDate = ''
      if (trend.length > 0) {
        const latest = trend[trend.length - 1]
        trendNav = latest.nav
        trendDate = latest.date
      }

      // 1. 今日有实时估值（交易时段）→ 用估值
      if (gsz > 0 && fund.gztime && fund.gztime.slice(0, 10) === todayStr) {
        return gsz
      }

      // 2. 走势数据比 fundgz 的净值日期更新 → 用走势数据（实际净值已公布）
      if (trendNav > 0 && trendDate > jzrq) {
        return trendNav
      }

      // 3. fundgz 官方净值日期就是今天 → 用官方净值
      if (jzrq === todayStr && dwjz > 0) return dwjz

      // 4. 兜底：估值 > 官方净值 > 走势
      return gsz || dwjz || trendNav || 0
    }

    // 获取上一交易日净值（用于计算今日涨跌）
    const getPrevTradingNav = (fund) => {
      const trend = getFundTrendSeries(fund)
      if (trend.length >= 2) {
        // 如果最新净值日期是今天，用倒数第二个；否则用最后一个（即昨天）
        const todayStr = new Date().toISOString().split('T')[0]
        const last = trend[trend.length - 1]
        const prev = trend[trend.length - 2]
        if (last.date === todayStr && prev) return prev.nav
        return last.nav
      }
      return parseFloat(fund.dwjz) || 0
    }

    // 当前市值 = 最优净值 × 份额
    const getHoldingEstimatedAmount = (fund) => {
      const h = holdings.value[fund.code]
      if (!h || !h.share) return 0
      return h.share * getBestNav(fund)
    }

    // 今日收益 = 份额 × (今日净值 - 昨日净值)
    const getHoldingProfitToday = (fund) => {
      const h = holdings.value[fund.code]
      if (!h || !h.share) return 0
      const todayNav = getBestNav(fund)
      const prevNav = getPrevTradingNav(fund)
      if (prevNav <= 0) return 0
      return h.share * (todayNav - prevNav)
    }

    // 获取显示用单位净值（走势数据兜底）
    const getDisplayNav = (fund) => {
      const dwjz = parseFloat(fund.dwjz)
      if (dwjz > 0) {
        // 检查走势数据是否有更新的
        const trend = getFundTrendSeries(fund)
        if (trend.length > 0) {
          const latest = trend[trend.length - 1]
          if (latest && latest.date > (fund.jzrq || '')) {
            return latest.nav.toFixed(4)
          }
        }
        return dwjz.toFixed(4)
      }
      return '-'
    }

    const getHoldingProfitTotal = (fund) => {
      const h = holdings.value[fund.code]
      if (!h || !h.share || !h.cost) return 0
      return (getBestNav(fund) - h.cost) * h.share
    }

    const getHoldingProfitTodayClass = (fund) => getHoldingProfitToday(fund) >= 0 ? 'up' : 'down'
    const getHoldingProfitTotalClass = (fund) => getHoldingProfitTotal(fund) >= 0 ? 'up' : 'down'

    // 根据金额和净值计算份额
    const calculateShare = (amount, nav) => {
      const a = parseFloat(amount)
      const n = parseFloat(nav)
      if (isNaN(a) || isNaN(n) || n <= 0) return 0
      return a / n
    }

    const toggleCollapse = (code) => {
      const next = new Set(collapsedCodes.value)
      if (next.has(code)) {
        next.delete(code)
      } else {
        next.add(code)
      }
      collapsedCodes.value = next
      localStorage.setItem('realtime_collapsed', JSON.stringify([...next]))
    }

    const isSelected = (code) => selectedFunds.value.some(f => f.CODE === code)

    const toggleSelectFund = (fund) => {
      const exists = selectedFunds.value.find(f => f.CODE === fund.CODE)
      if (exists) {
        selectedFunds.value = selectedFunds.value.filter(f => f.CODE !== fund.CODE)
      } else {
        selectedFunds.value = [...selectedFunds.value, fund]
        // 选中后自动清空
        searchTerm.value = ''
        searchResults.value = []
        showDropdown.value = false
      }
    }

    const mapPortfolioHoldings = (portfolio = {}) => {
      const rawList = portfolio.stock_codes_new || portfolio.stock_codes || []
      if (!Array.isArray(rawList)) return []
      return rawList.slice(0, 10).map((item, idx) => {
        if (typeof item === 'string') {
          const code = item.includes('.') ? item.split('.').pop() : item
          return {
            code,
            name: `持仓股票${idx + 1}`,
            weight: '-',
            change: null
          }
        }
        return {
          code: item.code || item.original_code || `STK${idx + 1}`,
          name: item.name || `持仓股票${idx + 1}`,
          weight: item.ratio != null ? `${item.ratio}%` : '-',
          change: null
        }
      })
    }

    const mapFundDetailToRealtime = (detail, fallbackCode) => {
      const realtime = detail?.realtime_estimate || {}
      const basic = detail?.basic_info || {}
      const changeNum = Number(realtime.estimate_change)
      return {
        code: normalizeFundCode(realtime.fund_code || basic.fund_code || fallbackCode),
        name: realtime.name || basic.fund_name || fallbackCode,
        dwjz: realtime.net_worth,
        gsz: realtime.estimate_value,
        gztime: realtime.estimate_time,
        jzrq: realtime.net_worth_date,
        gszzl: Number.isFinite(changeNum) ? changeNum : 0,
        holdings: mapPortfolioHoldings(detail?.portfolio),
        netWorthTrend: Array.isArray(detail?.net_worth_trend) ? detail.net_worth_trend : [],
        totalReturnTrend: Array.isArray(detail?.total_return_trend) ? detail.total_return_trend : []
      }
    }

    const parseTrendPoint = (item) => {
      if (!item || typeof item !== 'object') return null
      const navRaw = item.net_worth ?? item.y ?? item.value
      const nav = Number(navRaw)
      if (!Number.isFinite(nav) || nav <= 0) return null

      let dateText = ''
      if (typeof item.date === 'string' && item.date) {
        dateText = item.date.slice(0, 10)
      } else if (item.x) {
        const ts = Number(item.x)
        if (Number.isFinite(ts)) {
          const d = new Date(ts)
          dateText = d.toISOString().slice(0, 10)
        }
      }
      if (!dateText) return null
      return { date: dateText, nav }
    }

    const getFundTrendSeries = (fund) => {
      // 估值卡片中的净值换算与迷你走势图统一使用净值走势，避免收益曲线导致形态异常
      if (!Array.isArray(fund?.netWorthTrend)) return []
      return fund.netWorthTrend
        .map(parseTrendPoint)
        .filter(Boolean)
        .sort((a, b) => a.date.localeCompare(b.date))
    }

    // ---- 加仓/卖出建议 ----
    const getFundAdvice = (fund) => {
      try {
        const trend = getFundTrendSeries(fund)
        if (!trend || trend.length < 10) return { label: '数据不足', color: '#94a3b8' }

        const nav = parseFloat(fund?.gsz) || parseFloat(fund?.dwjz) || 0
        if (nav <= 0) return { label: '数据不足', color: '#94a3b8' }

        const h = holdings.value[fund.code]
        const pRate = h && h.share > 0 && h.cost > 0
          ? ((nav - h.cost) / h.cost) * 100
          : 0

        // 区间位置
        const recent60 = trend.slice(-60)
        const vals = recent60.map(t => t.nav)
        const high = Math.max(...vals)
        const low = Math.min(...vals)
        const rangePct = high > low ? ((nav - low) / (high - low)) * 100 : 50

        // 趋势方向
        const recent10 = trend.slice(-10)
        const half = Math.floor(recent10.length / 2)
        const firstAvg = recent10.slice(0, half).reduce((s, t) => s + t.nav, 0) / half
        const secondAvg = recent10.slice(-half).reduce((s, t) => s + t.nav, 0) / half
        const trendPct = firstAvg > 0 ? ((secondAvg - firstAvg) / firstAvg) * 100 : 0

        let score = 0

        if (rangePct < 20) score += 3
        else if (rangePct < 35) score += 2
        else if (rangePct < 50) score += 1
        else if (rangePct > 85) score -= 2
        else if (rangePct > 65) score -= 1

        if (pRate < -15) score += 2
        else if (pRate < -5) score += 1
        else if (pRate > 20) score -= 3
        else if (pRate > 10) score -= 1

        if (trendPct < -2) score += 1
        else if (trendPct > 3) score -= 1

        if (score >= 3) return { label: '强烈加仓', color: '#16a34a' }
        if (score >= 1) return { label: '可加仓', color: '#22c55e' }
        if (score === 0) return { label: '持有观望', color: '#f59e0b' }
        if (score >= -2) return { label: '谨慎持有', color: '#f97316' }
        return { label: '建议减仓', color: '#ef4444' }
      } catch (e) {
        console.error('getFundAdvice error:', e)
        return { label: '--', color: '#94a3b8' }
      }
    }

    // ---- AI 持仓操作建议 ----
    const fetchAIAdvice = async (fund) => {
      const h = holdings.value[fund.code]
      if (!h || !h.share) return

      const code = fund.code
      adviceLoading.value = { ...adviceLoading.value, [code]: true }
      try {
        const response = await fundAPI.getPositionAdvice(code, {
          cost: h.cost,
          shares: h.share,
          purchase_date: h.buy_date || '',
          purchase_time: '15:00'
        })
        const data = response?.data
        if (data && !data.error) {
          adviceMap.value = { ...adviceMap.value, [code]: data }
        }
      } catch (e) {
        console.error('AI advice fetch error:', e)
      } finally {
        adviceLoading.value = { ...adviceLoading.value, [code]: false }
      }
    }

    const actionColor = (actionType) => {
      const map = { buy: '#16a34a', hold: '#f59e0b', sell: '#ef4444' }
      return map[actionType] || '#94a3b8'
    }

    const getFundNavByDate = (fund, dateStr) => {
      const trend = getFundTrendSeries(fund)
      if (!trend.length) return parseFloat(fund?.dwjz) || 0
      const target = String(dateStr || '').slice(0, 10)
      if (!target) return parseFloat(fund?.dwjz) || trend[trend.length - 1].nav || 0

      let matched = null
      for (const point of trend) {
        if (point.date <= target) {
          matched = point
        } else {
          break
        }
      }
      return matched?.nav || parseFloat(fund?.dwjz) || trend[trend.length - 1].nav || 0
    }

    const getFundSparklinePoints = (fund) => {
      const trend = getFundTrendSeries(fund)
      if (!trend.length) return []
      const recent = trend.slice(-24)
      const min = Math.min(...recent.map(p => p.nav))
      const max = Math.max(...recent.map(p => p.nav))
      const span = max - min || 1
      return recent.map((p, i) => ({
        x: (i / (recent.length - 1 || 1)) * 100,
        y: 26 - ((p.nav - min) / span) * 22
      }))
    }

    const getSparklinePath = (points) => {
      if (!points || points.length < 2) return ''
      return points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ')
    }

    const getSparklineFill = (points, baseY = 30) => {
      if (!points || points.length < 2) return ''
      const line = getSparklinePath(points)
      const firstX = points[0].x.toFixed(2)
      const lastX = points[points.length - 1].x.toFixed(2)
      return `${line} L${lastX},${baseY} L${firstX},${baseY} Z`
    }

    const openFundDetail = (fund) => {
      emit('view-detail', {
        code: fund.code,
        name: fund.name
      })
    }

    const getFundSparklinePoints3m = (fund) => {
      const trend = getFundTrendSeries(fund)
      if (!trend.length) return []

      const cutoff = new Date()
      cutoff.setMonth(cutoff.getMonth() - 3)
      const cutoffText = cutoff.toISOString().slice(0, 10)

      let series = trend.filter(p => p.date >= cutoffText)
      if (series.length < 2) {
        series = trend.slice(-24)
      }
      if (series.length < 2) return []

      const min = Math.min(...series.map(p => p.nav))
      const max = Math.max(...series.map(p => p.nav))
      const span = max - min || 1
      return series.map((p, i) => ({
        x: (i / (series.length - 1 || 1)) * 100,
        y: 26 - ((p.nav - min) / span) * 22
      }))
    }

    const getFundMiniChart3m = (fund) => {
      const trend = getFundTrendSeries(fund)
      if (!trend.length) {
        return { points: [], yTicks: [], xTicks: [], trendUp: false }
      }

      const cutoff = new Date()
      cutoff.setMonth(cutoff.getMonth() - 3)
      const cutoffText = cutoff.toISOString().slice(0, 10)
      let series = trend.filter(p => p.date >= cutoffText)
      if (series.length < 2) series = trend.slice(-24)
      if (series.length < 2) {
        return { points: [], yTicks: [], xTicks: [], trendUp: false }
      }

      const startNav = series[0].nav || 1
      const pctSeries = series.map(p => ({
        date: p.date,
        pct: ((p.nav - startNav) / startNav) * 100
      }))

      const rawMin = Math.min(...pctSeries.map(p => p.pct))
      const rawMax = Math.max(...pctSeries.map(p => p.pct))
      const pad = Math.max((rawMax - rawMin) * 0.12, 0.25)
      const min = rawMin - pad
      const max = rawMax + pad
      const span = max - min || 1

      const plotLeft = 20
      const plotRight = 106
      const plotTop = 4
      const plotBottom = 28
      const plotW = plotRight - plotLeft
      const plotH = plotBottom - plotTop

      const points = pctSeries.map((p, i) => ({
        x: plotLeft + (i / (pctSeries.length - 1 || 1)) * plotW,
        y: plotBottom - ((p.pct - min) / span) * plotH
      }))

      const yTickCount = 5
      const yTicks = Array.from({ length: yTickCount }, (_, i) => {
        const ratio = i / (yTickCount - 1)
        const y = plotBottom - ratio * plotH
        const val = min + ratio * span
        return {
          y,
          label: `${val.toFixed(2)}%`
        }
      })

      const xTickCount = 6
      const xTicks = Array.from({ length: xTickCount }, (_, i) => {
        const idx = Math.min(
          pctSeries.length - 1,
          Math.round((i / (xTickCount - 1 || 1)) * (pctSeries.length - 1))
        )
        return {
          x: points[idx].x,
          label: pctSeries[idx].date.slice(5)
        }
      })

      const trendUp = pctSeries[pctSeries.length - 1].pct >= pctSeries[0].pct
      return { points, yTicks, xTicks, trendUp }
    }

    const getTrendColorClass3m = (fund) => {
      const trend = getFundTrendSeries(fund)
      if (!trend.length) return 'down'

      const cutoff = new Date()
      cutoff.setMonth(cutoff.getMonth() - 3)
      const cutoffText = cutoff.toISOString().slice(0, 10)
      let series = trend.filter(p => p.date >= cutoffText)
      if (series.length < 2) series = trend.slice(-24)
      if (series.length < 2) return 'down'

      return series[series.length - 1].nav >= series[0].nav ? 'up' : 'down'
    }

    // 搜索基金
    const performSearch = async () => {
      const keyword = String(searchTerm.value || '').trim()
      if (!keyword) {
        searchResults.value = []
        return
      }
      try {
        searchLoading.value = true
        const res = await fundAPI.searchFunds(keyword)
        const list = res?.data?.data || []
        searchResults.value = list.map(item => ({
          CODE: item.fund_code || item.CODE || item.code,
          NAME: item.fund_name || item.NAME || item.name
        })).filter(item => item.CODE && item.NAME)
        showDropdown.value = true

        // 与顶部搜索一致：输入6位代码时，优先命中精确项并自动选择
        if (/^\d{6}$/.test(keyword)) {
          const exact = searchResults.value.find(item => item.CODE === keyword)
          if (exact) {
            selectedFunds.value = [exact]
          }
        }
      } catch (e) {
        console.error('搜索失败', e)
        searchResults.value = []
      } finally {
        searchLoading.value = false
      }
    }

    const handleSearchInput = () => {
      if (searchTimeoutRef.value) clearTimeout(searchTimeoutRef.value)
      if (!String(searchTerm.value || '').trim()) {
        searchResults.value = []
        return
      }
      searchTimeoutRef.value = setTimeout(() => performSearch(), 150)
    }

    // 通过后端接口获取基金数据
    const fetchFundData = async (code) => {
      try {
        const cachedRes = await fundAPI.getFundCompareData(code)
        return mapFundDetailToRealtime(cachedRes?.data || {}, code)
      } catch (e) {
        const res = await fundAPI.getFundDetail(code)
        return mapFundDetailToRealtime(res?.data || {}, code)
      }
    }

    // 从自选添加
    const addFundToRealtime = async (fundInfo) => {
      const code = normalizeFundCode(fundInfo.fund_code || fundInfo.code || fundInfo.CODE)
      if (!code) return
      
      // 已存在检查
      if (funds.value.some(f => normalizeFundCode(f.code) === code)) {
         return 
      }
      
      refreshing.value = true
      try {
        const data = await fetchFundData(code)
        funds.value = [data, ...funds.value]
        localStorage.setItem('realtime_funds', JSON.stringify(funds.value))
      } catch(e) {
          console.error(e)
      } finally {
          refreshing.value = false
      }
    }

    // 批量添加基金
    const batchAddFunds = async () => {
      // 允许直接输入6位代码后点“添加基金”
      if (selectedFunds.value.length === 0 && /^\d{6}$/.test(String(searchTerm.value || '').trim())) {
        await performSearch()
      }

      if (selectedFunds.value.length === 0) return
      refreshing.value = true
      
      try {
        const newFunds = []
        for (const f of selectedFunds.value) {
          const code = normalizeFundCode(f.CODE)
          if (funds.value.some(existing => normalizeFundCode(existing.code) === code)) continue
          try {
            const data = await fetchFundData(code)
            newFunds.push(data)
          } catch (e) {
            console.error(`添加基金 ${f.CODE} 失败`, e)
          }
        }
        
        if (newFunds.length > 0) {
          const updated = [...newFunds, ...funds.value]
          funds.value = updated
          localStorage.setItem('realtime_funds', JSON.stringify(updated))
        }
        
        selectedFunds.value = []
        searchTerm.value = ''
        searchResults.value = []
        showDropdown.value = false
        activeTab.value = 'watch'
      } catch (e) {
        console.error('批量添加失败', e)
      } finally {
        refreshing.value = false
      }
    }

    // 刷新所有基金
    const refreshAll = async () => {
      if (refreshing.value || funds.value.length === 0) return
      refreshing.value = true
      
      try {
        const updated = []
        for (const fund of funds.value) {
          try {
            const data = await fetchFundData(normalizeFundCode(fund.code))
            updated.push(data)
          } catch (e) {
            console.error(`刷新基金 ${fund.code} 失败`, e)
            updated.push(fund) // 保留旧数据
          }
        }
        
        funds.value = updated
        localStorage.setItem('realtime_funds', JSON.stringify(updated))
      } catch (e) {
        console.error('刷新失败', e)
      } finally {
        refreshing.value = false
        updateNowTime()
      }
    }

    // 删除基金
    const removeFund = (code) => {
      const targetCode = normalizeFundCode(code)
      funds.value = funds.value.filter(f => normalizeFundCode(f.code) !== targetCode)
      localStorage.setItem('realtime_funds', JSON.stringify(funds.value))

      // 同步清理该基金的持仓数据和AI建议缓存
      if (holdings.value[targetCode]) {
        const newHoldings = { ...holdings.value }
        delete newHoldings[targetCode]
        holdings.value = newHoldings
        localStorage.setItem('realtime_holdings', JSON.stringify(newHoldings))
      }
      if (adviceMap.value[targetCode]) {
        const newAdvice = { ...adviceMap.value }
        delete newAdvice[targetCode]
        adviceMap.value = newAdvice
      }

      if (activeTab.value !== 'watch' && displayFunds.value.length === 0) {
        activeTab.value = 'watch'
      }
    }

    // 持仓弹窗
    const openHoldingModal = (fund) => {
      holdingModal.value = { open: true, fund }
      const code = normalizeFundCode(fund.code)
      const h = holdings.value[code]
      // 如果有现有持仓，根据份额和净值计算金额
      if (h && h.share) {
        const nav = h.cost || parseFloat(fund.dwjz) || 1
        holdingForm.value = {
          amount: (h.share * nav).toFixed(2),
          buyDate: h.buy_date || fund.jzrq || todayDate.value
        }
      } else {
        holdingForm.value = { amount: '', buyDate: fund.jzrq || todayDate.value }
      }
      // 重置加减仓表单
      modalTab.value = h && h.share ? 'trade' : 'set'
      tradeForm.value = { type: 'buy', amount: '', nav: '' }
    }

    const openTradeModal = (fund, type) => {
      openHoldingModal(fund)
      modalTab.value = 'trade'
      tradeForm.value.type = type
    }

    const closeHoldingModal = () => {
      holdingModal.value = { open: false, fund: null }
    }

    const saveHolding = () => {
      const fund = holdingModal.value.fund
      if (!fund) return
      const code = normalizeFundCode(fund.code)
      
      const amount = parseFloat(holdingForm.value.amount)
      const buyDate = holdingForm.value.buyDate || fund.jzrq || todayDate.value
      const nav = getFundNavByDate(fund, buyDate)
      
      if (!amount || !nav || nav <= 0) {
        closeHoldingModal()
        return
      }
      
      const share = amount / nav
      
      const newHoldings = { ...holdings.value }
      newHoldings[code] = {
        share: share,
        cost: nav,
        buy_date: buyDate
      }
      
      holdings.value = newHoldings
      localStorage.setItem('realtime_holdings', JSON.stringify(newHoldings))
      closeHoldingModal()
    }

    const clearHolding = () => {
      const fund = holdingModal.value.fund
      if (!fund) return
      const code = normalizeFundCode(fund.code)
      
      const newHoldings = { ...holdings.value }
      delete newHoldings[code]
      holdings.value = newHoldings
      localStorage.setItem('realtime_holdings', JSON.stringify(newHoldings))
      closeHoldingModal()
    }

    // 获取交易净值（优先使用用户输入，否则使用上一交易日净值）
    const getTradeNav = () => {
      const inputNav = parseFloat(tradeForm.value.nav)
      if (inputNav > 0) return inputNav
      return parseFloat(holdingModal.value.fund?.dwjz) || 0
    }

    // 计算交易后总份额
    const getTradeResultShares = () => {
      const nav = getTradeNav()
      const amount = parseFloat(tradeForm.value.amount) || 0
      if (nav <= 0 || amount <= 0) return holdings.value[holdingModal.value.fund?.code]?.share || 0
      const tradeShares = amount / nav
      const currentShares = holdings.value[holdingModal.value.fund?.code]?.share || 0
      return tradeForm.value.type === 'buy' ? currentShares + tradeShares : currentShares - tradeShares
    }

    // 保存加减仓交易
    const saveTrade = () => {
      const fund = holdingModal.value.fund
      if (!fund) return
      const code = normalizeFundCode(fund.code)

      const amount = parseFloat(tradeForm.value.amount)
      const nav = getTradeNav()
      if (!amount || amount <= 0 || nav <= 0) return

      const tradeShares = amount / nav
      const h = holdings.value[code] || { share: 0, cost: 0 }
      const newHoldings = { ...holdings.value }

      if (tradeForm.value.type === 'buy') {
        // 加仓：计算新的总份额和加权平均成本
        const newTotalShares = h.share + tradeShares
        const newAvgCost = h.share > 0
          ? (h.share * h.cost + amount) / newTotalShares
          : nav
        newHoldings[code] = {
          share: newTotalShares,
          cost: newAvgCost
        }
      } else {
        // 减仓：份额减少，成本价不变
        const newTotalShares = h.share - tradeShares
        if (newTotalShares <= 0.01) {
          delete newHoldings[code]
        } else {
          newHoldings[code] = {
            share: newTotalShares,
            cost: h.cost
          }
        }
      }

      holdings.value = newHoldings
      localStorage.setItem('realtime_holdings', JSON.stringify(newHoldings))
      closeHoldingModal()
    }

    const saveRefreshMs = () => {
      localStorage.setItem('realtime_refresh_ms', refreshMs.value.toString())
      // 重启定时器
      startRefreshTimer()
    }

    const updateNowTime = () => {
      nowTime.value = new Date().toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    const exportData = () => {
      const payload = {
        funds: funds.value,
        holdings: holdings.value,
        exportedAt: new Date().toISOString()
      }
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `gofundbot-realtime-${new Date().toISOString().slice(0, 10)}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }

    const importData = async (event) => {
      const file = event?.target?.files?.[0]
      if (!file) return
      try {
        const text = await file.text()
        const parsed = JSON.parse(text)
        if (Array.isArray(parsed.funds)) {
          funds.value = parsed.funds
          localStorage.setItem('realtime_funds', JSON.stringify(parsed.funds))
        }
        if (parsed.holdings && typeof parsed.holdings === 'object') {
          holdings.value = parsed.holdings
          localStorage.setItem('realtime_holdings', JSON.stringify(parsed.holdings))
        }
        refreshAll()
      } catch (error) {
        console.error('导入失败', error)
      } finally {
        event.target.value = ''
      }
    }

    const startRefreshTimer = () => {
      if (refreshTimer.value) clearInterval(refreshTimer.value)
      refreshTimer.value = setInterval(() => {
        refreshAll()
      }, refreshMs.value)
    }

    // 点击外部关闭下拉框
    const handleClickOutside = (event) => {
      if (searchPanelRef.value && !searchPanelRef.value.contains(event.target) && dropdownRef.value && !dropdownRef.value.contains(event.target)) {
        showDropdown.value = false
      }
    }

    // ==================== 生命周期 ====================
    onMounted(() => {
      // 加载本地数据
      try {
        const savedFunds = JSON.parse(localStorage.getItem('realtime_funds') || '[]')
        if (Array.isArray(savedFunds) && savedFunds.length) {
          funds.value = savedFunds.map(item => ({
            ...item,
            code: normalizeFundCode(item.code)
          }))
          refreshAll()
        }
        
        const savedHoldings = JSON.parse(localStorage.getItem('realtime_holdings') || '{}')
        if (savedHoldings && typeof savedHoldings === 'object') {
          const fundCodes = new Set(funds.value.map(f => f.code))
          const normalizedHoldings = {}
          Object.entries(savedHoldings).forEach(([code, value]) => {
            const normalized = normalizeFundCode(code)
            if (fundCodes.has(normalized)) {  // 只保留基金列表中存在的持仓
              normalizedHoldings[normalized] = value
            }
          })
          holdings.value = normalizedHoldings
          // 回写清理后的数据
          if (Object.keys(normalizedHoldings).length !== Object.keys(savedHoldings).length) {
            localStorage.setItem('realtime_holdings', JSON.stringify(normalizedHoldings))
          }
        }
        
        const savedMs = parseInt(localStorage.getItem('realtime_refresh_ms') || '30000', 10)
        if (Number.isFinite(savedMs) && savedMs >= 5000) {
          refreshMs.value = savedMs
        }
        
        const savedCollapsed = JSON.parse(localStorage.getItem('realtime_collapsed') || '[]')
        if (Array.isArray(savedCollapsed)) {
          collapsedCodes.value = new Set(savedCollapsed)
        }
      } catch (e) {
        console.error('加载本地数据失败', e)
      }
      
      startRefreshTimer()
      updateNowTime()
      timeTimer.value = setInterval(updateNowTime, 60000)
      document.addEventListener('mousedown', handleClickOutside)
      const savedSortBy = localStorage.getItem('realtime_sort_by')
      if (savedSortBy) sortBy.value = savedSortBy
      const savedUser = localStorage.getItem('gofundbot_user')
      if (savedUser) username.value = savedUser
    })

    onUnmounted(() => {
      if (refreshTimer.value) clearInterval(refreshTimer.value)
      if (timeTimer.value) clearInterval(timeTimer.value)
      document.removeEventListener('mousedown', handleClickOutside)
    })

    watch(sortBy, (value) => {
      localStorage.setItem('realtime_sort_by', value)
    })

    return {
      funds,
      holdings,
      collapsedCodes,
      refreshing,
      refreshMs,
      searchTerm,
      searchResults,
      selectedFunds,
      username,
      nowTime,
      sortBy,
      activeTab,
      displayFunds,
      emptyTitle,
      emptyHint,
      addFundToRealtime,
      showDropdown,
      dropdownRef,
      searchPanelRef,
      searchLoading,
      todayDate,
      holdingModal,
      holdingForm,
      modalTab,
      tradeForm,
      isTradingTime,
      adviceMap,
      adviceLoading,
      fetchAIAdvice,
      actionColor,
      sortedFunds,
      hasHoldings,
      totalAsset,
      totalCost,
      totalProfitToday,
      totalProfitTotal,
      totalReturnRate,
      todayReturnRate,
      profitTodayClass,
      profitTotalClass,
      getChangeClass,
      formatGsz,
      formatChange,
      getBestNav,
      getDisplayNav,
      getHoldingAmount,
      getHoldingEstimatedAmount,
      getHoldingProfitToday,
      getHoldingProfitTotal,
      getHoldingProfitTodayClass,
      getHoldingProfitTotalClass,
      toggleCollapse,
      isSelected,
      toggleSelectFund,
      getFundNavByDate,
      getFundAdvice,
      getFundSparklinePoints,
      getFundSparklinePoints3m,
      getFundMiniChart3m,
      getTrendColorClass3m,
      getSparklinePath,
      getSparklineFill,
      openFundDetail,
      handleSearchInput,
      batchAddFunds,
      refreshAll,
      removeFund,
      openHoldingModal,
      openTradeModal,
      closeHoldingModal,
      saveHolding,
      clearHolding,
      saveRefreshMs,
      exportData,
      importData,
      calculateShare,
      getTradeNav,
      getTradeResultShares,
      saveTrade
    }
  }
}
</script>
<style scoped>
.realtime-container {
  background: #f5f6f8;
  padding: 16px;
  font-family: sans-serif;
  color: #333;
}
.top-row {
  display: flex;
  gap: 12px;
  align-items: center;
  background: #fff;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.search-box {
  flex: 1;
  position: relative;
}
.search-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  outline: none;
}
.search-input:focus { border-color: #6075ff; border-radius: 6px;}
.search-dropdown-overlay {
  position: absolute; top: 100%; left: 0; right: 0; background: #fff; z-index: 99;
  border: 1px solid #ddd; border-radius: 6px; max-height: 200px; overflow-y: auto; margin-top: 4px;
}
.dropdown-item { padding: 8px 12px; cursor: pointer; }
.dropdown-item:hover { background: #f0f0f0; }

.btn {
  padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer;
}
.btn-primary { background: #6075ff; color: #fff; }
.select-sort { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; }
.btn-blue { background: #1677ff; color: #fff; }
.btn-green { background: #52c41a; color: #fff; }
.hidden-file { display: none; }

.overview-box {
  background: #fff; padding: 16px; border-radius: 8px; margin-bottom: 16px;
}
.overview-head {
  display: flex; justify-content: space-between; margin-bottom: 16px; border-bottom: 1px solid #eee; padding-bottom: 12px;
}
.title-with-icon { font-weight: bold; font-size: 16px; }
.meta-info { font-size: 12px; color: #999; }
.overview-grid {
  display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; text-align: center;
}
.overview-cell.purple { background: #6b46c1; color: #fff; border-radius: 6px; padding: 12px 0;}
.overview-cell { padding: 12px 0; border: 1px solid #eee; border-radius: 6px; }
.cell-label { font-size: 13px; color: #666; margin-bottom: 4px; }
.overview-cell.purple .cell-label { color: #eee; }
.cell-val { font-size: 18px; font-weight: bold; }
.overview-cell.purple .cell-val { color: #fff; }

.content-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.ctab { padding: 6px 12px; background: #eee; border-radius: 16px; font-size: 14px; cursor: pointer; }
.ctab.active { background: #fff; color: #1677ff; font-weight: bold; }

.fund-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.fund-item-card { background: #fff; border-radius: 10px; padding: 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
.card-head { display: flex; justify-content: space-between; margin-bottom: 8px; }
.c-title { font-weight: bold; font-size: 15px; }
.btn-del { background: #ff4d4f; color: #fff; border: none; padding: 2px 8px; border-radius: 4px; font-size: 12px; cursor: pointer;}
.c-tags { display: flex; gap: 8px; font-size: 12px; color: #666; margin-bottom: 12px; }
.tag { padding: 2px 6px; border-radius: 4px; color: white;}
.tag.red { background: #ff4d4f; }
.tag.pink { background: #eb2f96; }

.c-mid-tabs { display: flex; border-bottom: 1px solid #eee; margin-bottom: 12px; }
.c-tab { flex: 1; text-align: center; padding: 8px 0; cursor: pointer; font-size: 13px; color: #666;}
.c-tab.active { color: #1677ff; border-bottom: 2px solid #1677ff; }
.c-tab:hover { color: #1677ff; background: #f7fbff; }

.c-hero { display: flex; justify-content: center; gap: 16px; margin-bottom: 16px; }
.hero-chip { padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 16px; }
.hero-chip.up { color: #f5222d; background: #fff1f0; }
.hero-chip.down { color: #52c41a; background: #f6ffed; }
.advice-chip { color: #fff !important; font-size: 13px !important; }
.ai-btn { background: linear-gradient(135deg, #667eea, #764ba2) !important; color: #fff !important; font-size: 12px !important; cursor: pointer; border: none; }
.ai-btn:hover:not(:disabled) { opacity: 0.85; transform: scale(1.02); }
.ai-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.ai-advice-badge { color: #fff !important; font-size: 12px !important; cursor: help; }

.c-holdings-area { background: #f8f9fc; border-radius: 8px; padding: 12px; margin-bottom: 16px; }
.c-h-head { display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 13px; font-weight: bold; align-items: center;}
.c-h-pen { color: #1677ff; font-weight: normal; margin-left: 8px; }
.btn-sm {
  border: none;
  padding: 6px 14px;
  border-radius: 999px;
  cursor: pointer;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.2px;
  transition: all 0.18s ease;
  box-shadow: 0 2px 8px rgba(17, 24, 39, 0.12);
}
.btn-sm:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(17, 24, 39, 0.16);
}
.btn-sm:active {
  transform: translateY(0);
}
.b-buy { background: linear-gradient(135deg, #2d8cff 0%, #1f6bff 100%); }
.b-sell { background: linear-gradient(135deg, #ffb347 0%, #ff8f1f 100%); margin-left: 8px; }

.c-h-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.grid-box { display: flex; justify-content: space-between; font-size: 12px; }
.g-label { color: #888; } .g-val { font-weight: bold; }
.g-val.up { color: #f5222d; } .g-val.down { color: #52c41a; }

.c-bottom-nav { display: flex; justify-content: space-around; margin-bottom: 8px; }
.bn-col { text-align: center; font-size: 13px;}
.bn-label { color: #888; margin-bottom: 4px;}
.bn-val { font-weight: bold; }
.bn-val.up { color: #f5222d; } .bn-val.down { color: #52c41a; }

.c-chart {
  height: 86px;
  margin-top: 4px;
  margin-bottom: 6px;
  border: 1px solid #f2dede;
  border-radius: 6px;
  background: #fff6f6;
  overflow: hidden;
}
.c-svg { width: 100%; height: 100%; }
.c-axis { stroke: #cfd7e5; stroke-width: 0.7; }
.c-grid { stroke: #e9edf5; stroke-width: 0.55; }
.c-fill { fill: rgba(245, 34, 45, 0.14); }
.c-fill.up { fill: rgba(245, 34, 45, 0.14); }
.c-fill.down { fill: rgba(82, 196, 26, 0.14); }
.c-line { fill: none; stroke: #ea4a4a; stroke-width: 0.85; }
.c-line.up { stroke: #ea4a4a; }
.c-line.down { stroke: #33a853; }
.c-y-label { fill: #7f8897; font-size: 3.1px; }
.c-x-label { fill: #8a93a3; font-size: 2.9px; }
.spark-empty { height: 100%; display: flex; align-items: center; justify-content: center; color: #9aa0aa; font-size: 12px; }

.c-time { text-align: center; color: #ccc; font-size: 11px; }

.modal-overlay { position: fixed; top:0; left:0; right:0; bottom:0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;}
.modal-box { background: #fff; padding: 20px; border-radius: 10px; width: 420px; }
.modal-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 14px;
}
.modal-tab {
  border: none;
  background: transparent;
  color: #6b7484;
  font-size: 14px;
  font-weight: 700;
  padding: 10px 0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}
.form-group { margin-bottom: 12px; } .modal-input { width: 100%; padding: 8px; box-sizing: border-box;}
.up { color: #f5222d !important; } .down { color: #52c41a !important; }

/* Elegant Modal Styles */
.elegant-tabs {
  background: #f4f6fb;
  border-radius: 8px;
  padding: 4px;
}
.elegant-tabs .modal-tab {
  background: transparent;
  color: #666;
  font-weight: 600;
  transition: all 0.2s;
  padding: 9px 0;
  border: none;
}
.elegant-tabs .modal-tab.active {
  background: #fff;
  color: #1677ff;
  box-shadow: 0 2px 6px rgba(22, 119, 255, 0.18);
  border-radius: 6px;
  font-weight: 700;
}
.elegant-trade-box {
  padding-top: 16px;
}
.trade-toggle {
  display: flex;
  background: #f4f7fb;
  border: 1px solid #e4e9f2;
  border-radius: 10px;
  margin-bottom: 20px;
  overflow: hidden;
  padding: 3px;
}
.trade-toggle-btn {
  flex: 1;
  text-align: center;
  padding: 9px 0;
  font-size: 13px;
  font-weight: 700;
  color: #7f8794;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 8px;
}
.trade-toggle-btn.buy.active {
  background: #e9f2ff;
  color: #1677ff;
  box-shadow: 0 2px 6px rgba(22, 119, 255, 0.22);
}
.trade-toggle-btn.sell.active {
  background: #fff3e8;
  color: #f57c00;
  box-shadow: 0 2px 6px rgba(245, 124, 0, 0.2);
}
.elegant-input-group label {
  font-size: 13px; color: #555; margin-bottom: 8px; font-weight: 600; display: block;
}
.elegant-input-group .input-wrapper {
  display: flex; align-items: center; background: #fff; border: 1px solid #d9d9d9; border-radius: 8px; padding: 0 16px; transition: all 0.3s;
}
.elegant-input-group .input-wrapper:focus-within {
  border-color: #1677ff; box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.1); background: #fafafa;
}
.elegant-input-group .prefix {
  color: #888; font-size: 16px; margin-right: 8px; font-weight: bold;
}
.elegant-input-group .modal-input.no-border {
  border: none; outline: none; box-shadow: none; font-size: 15px; padding: 12px 0; flex: 1; background: transparent; width: 100%; box-sizing: border-box;
}
.elegant-input-group .modal-input.highlight {
  font-weight: bold; color: #222; font-size: 16px;
}
.elegant-actions {
  margin-top: 24px; display: flex; gap: 12px; justify-content: flex-end; padding-top: 16px; border-top: 1px solid #f0f0f0;
}
.elegant-btn-cancel {
  background: #f0f2f5; color: #666; font-weight: bold; padding: 10px 24px; border-radius: 6px; border: none; cursor: pointer; transition: background 0.2s;
}
.elegant-btn-cancel:hover { background: #e5e8ea; }
.elegant-btn-confirm {
  font-weight: bold; color: #fff; border: none; padding: 10px 32px; border-radius: 6px; cursor: pointer; transition: opacity 0.2s;
}
.elegant-btn-confirm.buy { background: #1677ff; }
.elegant-btn-confirm.buy:hover { opacity: 0.85; }
.elegant-btn-confirm.sell { background: #f5222d; }
.elegant-btn-confirm.sell:hover { opacity: 0.85; }

.trade-inline-hint {
  margin-top: 8px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #667085;
}

.trade-inline-hint .warning {
  color: #f5222d;
  font-weight: 600;
}
</style>
