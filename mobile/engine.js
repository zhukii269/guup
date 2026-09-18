/**
 * 手机版量化交易与数据引擎 (Pure Client-Side Quant Engine)
 * 100% 还原 Python 版 StockDataProvider 与 IntervalCalculator 的核心逻辑
 * 直接在移动端请求腾讯金融行情接口 (原生支持 CORS)，零服务器依赖
 */

const MobileQuantEngine = (function() {
  // 默认 22 只主流行业/主题 ETF 观察池
  const DEFAULT_SECTOR_ETFS = [
    { sector: "金融科技", code: "sz159851", desc: "金融科技ETF", close: 0.603, prev_close: 0.589, pct_change: 2.38, tag: "强势共振", tag_color: "#f59e0b", reason_summary: "金融科技领涨放量" },
    { sector: "人工智能", code: "sz159819", desc: "人工智能ETF", close: 1.762, prev_close: 1.714, pct_change: 2.80, tag: "观望持仓", tag_color: "#3b82f6", reason_summary: "多周期均线多头趋势" },
    { sector: "半导体芯片", code: "sz159995", desc: "芯片ETF", close: 1.152, prev_close: 1.114, pct_change: 3.41, tag: "观望持仓", tag_color: "#3b82f6", reason_summary: "突破放量进攻形态" },
    { sector: "半导体设备", code: "sz159516", desc: "半导体设备ETF", close: 0.729, prev_close: 0.703, pct_change: 3.70, tag: "观望持仓", tag_color: "#3b82f6", reason_summary: "领涨共振多头" },
    { sector: "通信技术", code: "sh515880", desc: "通信ETF", close: 0.704, prev_close: 0.686, pct_change: 2.62, tag: "蓄势回调", tag_color: "#64748b", reason_summary: "回踩MA5支撑强固" },
    { sector: "消费电子", code: "sz159997", desc: "电子ETF", close: 2.114, prev_close: 2.059, pct_change: 2.67, tag: "观望持仓", tag_color: "#3b82f6", reason_summary: "趋势健康温和放量" },
    { sector: "动漫游戏", code: "sz159869", desc: "游戏ETF", close: 1.080, prev_close: 1.071, pct_change: 0.84, tag: "蓄势回调", tag_color: "#64748b", reason_summary: "盘整筑底蓄势" },
    { sector: "计算机软件", code: "sh512720", desc: "计算机ETF", close: 1.134, prev_close: 1.114, pct_change: 1.80, tag: "即将满足", tag_color: "#10b981", reason_summary: "量能温和放大准备共振" },
    { sector: "新能源车", code: "sh515030", desc: "新能源车ETF", close: 1.503, prev_close: 1.483, pct_change: 1.35, tag: "蓄势回调", tag_color: "#64748b", reason_summary: "MA20生命线上方震荡" },
    { sector: "光伏新能源", code: "sh515790", desc: "光伏ETF", close: 0.815, prev_close: 0.793, pct_change: 2.77, tag: "蓄势回调", tag_color: "#64748b", reason_summary: "低位超跌反弹修复" },
    { sector: "医药生物", code: "sh512010", desc: "医药ETF", close: 0.373, prev_close: 0.372, pct_change: 0.27, tag: "防守持有", tag_color: "#64748b", reason_summary: "低位筑底震荡" },
    { sector: "A股创新药", code: "sz159992", desc: "创新药ETF", close: 0.835, prev_close: 0.830, pct_change: 0.60, tag: "观望持仓", tag_color: "#3b82f6", reason_summary: "生命线支撑强固" },
    { sector: "港股创新药", code: "sz159567", desc: "港股创新药ETF", close: 0.682, prev_close: 0.680, pct_change: 0.29, tag: "防守持有", tag_color: "#64748b", reason_summary: "窄幅蓄势待放量" },
    { sector: "恒生医疗", code: "sh513060", desc: "恒生医疗ETF", close: 0.571, prev_close: 0.565, pct_change: 1.06, tag: "蓄势回调", tag_color: "#64748b", reason_summary: "底部抬高稳步修复" },
    { sector: "恒生互联网", code: "sh513330", desc: "恒生互联网ETF", close: 0.346, prev_close: 0.341, pct_change: 1.47, tag: "即将满足", tag_color: "#10b981", reason_summary: "站上拼均线" },
    { sector: "大金融证券", code: "sh512880", desc: "证券ETF", close: 1.057, prev_close: 1.042, pct_change: 1.44, tag: "防守持有", tag_color: "#64748b", reason_summary: "大金融护盘平稳" },
    { sector: "国防军工", code: "sh512660", desc: "军工ETF", close: 1.160, prev_close: 1.142, pct_change: 1.58, tag: "观望持仓", tag_color: "#3b82f6", reason_summary: "区间震荡反弹" },
    { sector: "人形机器人", code: "sh562500", desc: "机器人ETF", close: 0.934, prev_close: 0.916, pct_change: 1.97, tag: "即将满足", tag_color: "#10b981", reason_summary: "多头突破临界点" },
    { sector: "有色金属", code: "sh512400", desc: "有色金属ETF", close: 1.732, prev_close: 1.708, pct_change: 1.41, tag: "防守持有", tag_color: "#64748b", reason_summary: "大宗商品周期震荡" },
    { sector: "煤炭周期", code: "sh515220", desc: "煤炭ETF", close: 1.249, prev_close: 1.258, pct_change: -0.72, tag: "防守持有", tag_color: "#64748b", reason_summary: "高股息防御风格" },
    { sector: "电力绿电", code: "sz159611", desc: "电力ETF", close: 1.040, prev_close: 1.037, pct_change: 0.29, tag: "防守持有", tag_color: "#64748b", reason_summary: "绿电稳健防御" },
    { sector: "红利低波", code: "sh515180", desc: "红利ETF", close: 1.409, prev_close: 1.411, pct_change: -0.14, tag: "防守持有", tag_color: "#64748b", reason_summary: "红利低波防御" }
  ];

  const STORAGE_KEY_WATCHLIST = "stock_master_mobile_watchlist";
  const STORAGE_KEY_PORTFOLIO = "stock_master_mobile_portfolio";
  const STORAGE_KEY_THEME = "stock_master_mobile_theme";

  // 代码规范化
  function normalizeSymbol(raw) {
    if (!raw) return "sh515880";
    let s = String(raw).trim().toLowerCase();
    if (/^\d{6}$/.test(s)) {
      if (s.startsWith("6") || s.startsWith("9") || s.startsWith("688")) {
        return "sh" + s;
      } else if (s.startsWith("0") || s.startsWith("3") || s.startsWith("159") || s.startsWith("12") || s.startsWith("16") || s.startsWith("399")) {
        return "sz" + s;
      } else if (s === "000001") {
        return "sh000001";
      } else {
        return "sh" + s;
      }
    }
    if (s.startsWith("sh") || s.startsWith("sz")) return s;
    return "sh" + s;
  }

  // 获取实时行情 (通过腾讯接口，支持 CORS)
  async function getRealtimeQuote(symbol) {
    const fullSym = normalizeSymbol(symbol);
    const url = `https://qt.gtimg.cn/q=${fullSym}`;
    try {
      const resp = await fetch(url);
      const text = await resp.text();
      const match = text.match(/="([^"]+)"/);
      if (match && match[1]) {
        const p = match[1].split("~");
        if (p.length > 35) {
          const current = parseFloat(p[3]) || 0;
          const prevClose = parseFloat(p[4]) || current;
          const change = parseFloat(p[31]) || (current - prevClose);
          const pctChange = parseFloat(p[32]) || ((current - prevClose) / prevClose * 100);
          return {
            symbol: fullSym,
            code: fullSym.slice(2),
            name: p[1] || "ETF",
            current: current,
            prev_close: prevClose,
            open: parseFloat(p[5]) || current,
            high: parseFloat(p[33]) || current,
            low: parseFloat(p[34]) || current,
            change: Math.round(change * 1000) / 1000,
            pct_change: Math.round(pctChange * 100) / 100,
            volume: parseFloat(p[6]) || 0,
            amount: parseFloat(p[37]) || 0,
            date: p[30] ? p[30].slice(0, 8) : "",
            time: p[30] ? p[30].slice(8) : ""
          };
        }
      }
    } catch (e) {
      console.warn("getRealtimeQuote failed:", e);
    }
    return {
      symbol: fullSym,
      code: fullSym.slice(2),
      name: fullSym,
      current: 1.0,
      prev_close: 1.0,
      open: 1.0,
      high: 1.0,
      low: 1.0,
      change: 0,
      pct_change: 0,
      volume: 0,
      amount: 0
    };
  }

  // 获取日K线历史数据 (直接调用腾讯前复权主节点，支持 CORS)
  async function getDailyKlines(symbol, limit = 600) {
    const fullSym = normalizeSymbol(symbol);
    const url = `https://ifzq.gtimg.cn/appstock/app/newfqkline/get?param=${fullSym},day,,,${limit},qfq`;
    try {
      const resp = await fetch(url);
      const data = await resp.json();
      if (data && data.data && data.data[fullSym]) {
        const stockData = data.data[fullSym];
        const rawBars = stockData.qfqday || stockData.day || [];
        const name = stockData.qt && stockData.qt[fullSym] ? stockData.qt[fullSym][1] : fullSym;

        let prevClose = null;
        const klines = rawBars.map(item => {
          const date = item[0];
          const open = parseFloat(item[1]);
          const close = parseFloat(item[2]);
          const high = parseFloat(item[3]);
          const low = parseFloat(item[4]);
          const volume = parseFloat(item[5]) * 100; // 手转股
          const amount = item[8] ? parseFloat(item[8]) * 10000 : 0;
          const turnover = item[7] ? parseFloat(item[7]) : 0;

          let pct_change = 0.0;
          if (prevClose !== null && prevClose > 0) {
            pct_change = Math.round(((close - prevClose) / prevClose * 100) * 100) / 100;
          }
          prevClose = close;

          return {
            date,
            open,
            close,
            high,
            low,
            volume,
            amount,
            turnover,
            pct_change
          };
        });

        // 注入所有量化技术指标与买卖信号
        addMovingAverages(klines);
        addEmas(klines);
        addBoll(klines);
        addVolumeMovingAverages(klines);
        addMacd(klines);
        addKdj(klines);
        addRsi(klines);
        addSignals(klines);

        return {
          symbol: fullSym,
          code: fullSym.slice(2),
          name: name,
          klines: klines
        };
      }
    } catch (e) {
      console.error("getDailyKlines error for " + fullSym, e);
    }
    return { symbol: fullSym, code: fullSym.slice(2), name: fullSym, klines: [] };
  }

  // 计算均线 MA5, 10, 20, 30, 60
  function addMovingAverages(klines) {
    const closes = klines.map(k => k.close);
    for (let i = 0; i < klines.length; i++) {
      for (const period of [5, 10, 20, 30, 60]) {
        if (i + 1 >= period) {
          let sum = 0;
          for (let j = i + 1 - period; j <= i; j++) sum += closes[j];
          klines[i][`ma${period}`] = Math.round((sum / period) * 1000) / 1000;
        } else {
          klines[i][`ma${period}`] = null;
        }
      }
    }
  }

  // 计算 EMA 5, 13, 30
  function addEmas(klines) {
    const closes = klines.map(k => k.close);
    for (const period of [5, 13, 30]) {
      const mult = 2 / (period + 1);
      let ema = 0.0;
      for (let i = 0; i < klines.length; i++) {
        const c = closes[i];
        if (i === 0) ema = c;
        else ema = (c - ema) * mult + ema;
        klines[i][`ema${period}`] = Math.round(ema * 1000) / 1000;
      }
    }
  }

  // 计算布林带 BOLL (20, 2)
  function addBoll(klines, period = 20, k = 2) {
    const closes = klines.map(k => k.close);
    for (let i = 0; i < klines.length; i++) {
      if (i + 1 < period) {
        klines[i].boll_mid = null;
        klines[i].boll_upper = null;
        klines[i].boll_lower = null;
        klines[i].boll_width = null;
      } else {
        let sum = 0;
        for (let j = i + 1 - period; j <= i; j++) sum += closes[j];
        const mid = sum / period;
        let vSum = 0;
        for (let j = i + 1 - period; j <= i; j++) vSum += Math.pow(closes[j] - mid, 2);
        const std = Math.sqrt(vSum / period);
        const upper = mid + k * std;
        const lower = mid - k * std;
        const width = mid > 0 ? (upper - lower) / mid : 0;
        klines[i].boll_mid = Math.round(mid * 1000) / 1000;
        klines[i].boll_upper = Math.round(upper * 1000) / 1000;
        klines[i].boll_lower = Math.round(lower * 1000) / 1000;
        klines[i].boll_width = Math.round(width * 10000) / 10000;
      }
    }
  }

  // 计算成交量均线
  function addVolumeMovingAverages(klines) {
    const vols = klines.map(k => k.volume);
    for (let i = 0; i < klines.length; i++) {
      for (const period of [5, 10]) {
        if (i + 1 >= period) {
          let sum = 0;
          for (let j = i + 1 - period; j <= i; j++) sum += vols[j];
          klines[i][`vol_ma${period}`] = Math.round(sum / period);
        } else {
          klines[i][`vol_ma${period}`] = null;
        }
      }
    }
  }

  // 计算 MACD (12, 26, 9)
  function addMacd(klines, short = 12, long = 26, mid = 9) {
    let emaShort = 0.0;
    let emaLong = 0.0;
    let dea = 0.0;

    for (let i = 0; i < klines.length; i++) {
      const close = klines[i].close;
      let dif = 0.0;
      if (i === 0) {
        emaShort = close;
        emaLong = close;
        dif = 0.0;
        dea = 0.0;
      } else {
        emaShort = emaShort * (short - 1) / (short + 1) + close * 2 / (short + 1);
        emaLong = emaLong * (long - 1) / (long + 1) + close * 2 / (long + 1);
        dif = emaShort - emaLong;
        dea = dea * (mid - 1) / (mid + 1) + dif * 2 / (mid + 1);
      }
      const macdBar = (dif - dea) * 2;
      klines[i].dif = Math.round(dif * 1000) / 1000;
      klines[i].dea = Math.round(dea * 1000) / 1000;
      klines[i].macd = Math.round(macdBar * 1000) / 1000;
    }
  }

  // 计算 KDJ (9, 3, 3)
  function addKdj(klines, n = 9, m1 = 3, m2 = 3) {
    let kVal = 50.0;
    let dVal = 50.0;

    for (let i = 0; i < klines.length; i++) {
      const startIdx = Math.max(0, i - n + 1);
      let hn = -Infinity;
      let ln = Infinity;
      for (let j = startIdx; j <= i; j++) {
        if (klines[j].high > hn) hn = klines[j].high;
        if (klines[j].low < ln) ln = klines[j].low;
      }
      if (hn === -Infinity) hn = klines[i].high;
      if (ln === Infinity) ln = klines[i].low;

      let rsv = 50.0;
      if (hn !== ln) {
        rsv = (klines[i].close - ln) / (hn - ln) * 100.0;
      }
      kVal = (m1 - 1) / m1 * kVal + 1 / m1 * rsv;
      dVal = (m2 - 1) / m2 * dVal + 1 / m2 * kVal;
      const jVal = 3 * kVal - 2 * dVal;

      klines[i].k = Math.round(kVal * 1000) / 1000;
      klines[i].d = Math.round(dVal * 1000) / 1000;
      klines[i].j = Math.round(jVal * 1000) / 1000;
    }
  }

  // 计算 RSI(6)
  function addRsi(klines, period = 6) {
    if (!klines || klines.length === 0) return;
    const gains = [];
    const losses = [];
    for (let i = 0; i < klines.length; i++) {
      if (i === 0) {
        klines[i].rsi6 = 50.0;
        continue;
      }
      const change = klines[i].close - klines[i - 1].close;
      const gain = Math.max(0, change);
      const loss = Math.max(0, -change);

      let avgGain = 0;
      let avgLoss = 0;
      if (i <= period) {
        gains.push(gain);
        losses.push(loss);
        avgGain = gains.reduce((a, b) => a + b, 0) / gains.length;
        avgLoss = losses.reduce((a, b) => a + b, 0) / losses.length;
      } else {
        avgGain = (gains[gains.length - 1] * (period - 1) + gain) / period;
        avgLoss = (losses[losses.length - 1] * (period - 1) + loss) / period;
        gains.push(avgGain);
        losses.push(avgLoss);
      }
      if (avgLoss === 0) {
        klines[i].rsi6 = 100.0;
      } else {
        const rs = avgGain / avgLoss;
        klines[i].rsi6 = Math.round((100.0 - (100.0 / (1.0 + rs))) * 100) / 100;
      }
    }
  }

  // 注入量化决策信号 (B, S1, S2, S3, S4, S7)
  function addSignals(klines) {
    if (!klines || klines.length < 30) return;

    let inPosition = false;
    let buyIndex = -1;
    let buyPrice = 0.0;
    let buyHighest = 0.0;
    let s3Triggered = false;

    for (let i = 0; i < klines.length; i++) {
      const bar = klines[i];
      bar.signal_type = null;
      bar.signal_name = null;
      bar.signal_reason = null;
      bar.signal_position = null;

      if (i < 20) continue;

      const prevBar = klines[i - 1];
      const prev2Bar = klines[i - 2];
      const prev3Bar = klines[i - 3];

      const ma5 = bar.ma5;
      const prevMa5 = prevBar.ma5;
      const volMa5 = bar.vol_ma5 || bar.volume;

      const dif = bar.dif || 0;
      const dea = bar.dea || 0;
      const prevDif = prevBar.dif || 0;
      const prevDea = prevBar.dea || 0;

      const macdBar = bar.macd || 0;
      const prevMacd = prevBar.macd || 0;
      const prev2Macd = prev2Bar.macd || 0;
      const prev3Macd = prev3Bar.macd || 0;

      const kVal = bar.k || 50.0;
      const dVal = bar.d || 50.0;
      const jVal = bar.j || 50.0;
      const prevK = prevBar.k || 50.0;
      const prevD = prevBar.d || 50.0;
      const prevJ = prevBar.j || 50.0;

      const candleBody = Math.abs(bar.close - bar.open);
      const upperShadow = bar.high - Math.max(bar.open, bar.close);

      // ==========================================
      // 模式 A: 未持仓状态，寻找买入信号 (B)
      // ==========================================
      if (!inPosition) {
        // 1. MA5 止跌
        const condMa5Up = (ma5 !== null) && (prevMa5 !== null) && (ma5 >= prevMa5 - 1e-5);

        // 2. MACD 动能验证 (绿柱缩短或红柱放大)
        const condMacdGreenShrink = (macdBar <= 0) && (prevMacd <= 0) && (Math.abs(macdBar) < Math.abs(prevMacd)) && (Math.abs(prevMacd) <= Math.abs(prev2Macd));
        const condMacdRedExpand = (macdBar >= 0) && ((prevMacd <= 0 || prev2Macd <= 0) || (prev2Macd >= 0 && macdBar > prevMacd && prevMacd >= prev2Macd));
        const condMacdTrend = condMacdGreenShrink || condMacdRedExpand;

        // 3. MACD 金叉附近判定 + DIF 主动上行
        const universalDifUp = dif > prevDif;

        // 场景 A: 绿柱末期
        let scenarioA = false;
        if (macdBar <= 0) {
          let greenWavePeak = 0.0;
          let j = i;
          while (j >= 0 && klines[j].macd <= 0) {
            greenWavePeak = Math.max(greenWavePeak, Math.abs(klines[j].macd));
            j--;
          }
          if (greenWavePeak > 0) {
            scenarioA = Math.abs(macdBar) <= 0.35 * greenWavePeak;
          }
        }

        // 场景 B: 红柱初期 (前两根)
        const scenarioB = (macdBar >= 0) && (prevMacd <= 0 || prev2Macd <= 0);
        const condMacdGoldClose = (scenarioA || scenarioB) && universalDifUp;

        // 4. KDJ 多头 (K > D)
        const condKdjBull = kVal > dVal;

        // 5. 过滤高位脉冲放量诱多
        const start60 = Math.max(0, i - 60 + 1);
        let highest60 = -Infinity;
        let lowest60 = Infinity;
        for (let j = start60; j <= i; j++) {
          if (klines[j].high > highest60) highest60 = klines[j].high;
          if (klines[j].low < lowest60) lowest60 = klines[j].low;
        }
        const range60 = Math.max(0.001, highest60 - lowest60);
        const posRatio60 = (bar.close - lowest60) / range60;

        const start15 = Math.max(0, i - 15 + 1);
        let lowest15 = Infinity;
        for (let j = start15; j <= i; j++) {
          if (klines[j].low < lowest15) lowest15 = klines[j].low;
        }
        const gainFromRecentLow = lowest15 > 0 ? (bar.close - lowest15) / lowest15 : 0;

        const isHighPosition = (posRatio60 >= 0.65) || (gainFromRecentLow >= 0.15);
        const isVolumeSurgeUp = isHighPosition && (bar.pct_change >= 3.0) && (bar.volume >= 1.3 * volMa5);

        if (condMa5Up && condMacdTrend && condMacdGoldClose && condKdjBull && (!isVolumeSurgeUp)) {
          bar.signal_type = "B";
          bar.signal_name = "买入: 5日线+MACD+KDJ共振";
          bar.signal_position = "标准建仓 / 试错开仓";
          const reasonExtra = (bar.pct_change >= 3.0 && bar.volume >= 1.3 * volMa5) ? "底部放量突破确认" : "满足共振条件";
          bar.signal_reason = `MA5止跌(${ma5.toFixed(3)})，MACD金叉附近(场景A/B+DIF主动上行)，KDJ多头(K>D)，${reasonExtra}`;

          inPosition = true;
          s3Triggered = false;
          buyIndex = i;
          buyPrice = bar.close;
          buyHighest = bar.high;
          continue;
        }
      }
      // ==========================================
      // 模式 B: 持仓状态，评估卖出信号 (S)
      // ==========================================
      else {
        const profitPct = buyPrice > 0 ? (bar.close - buyPrice) / buyPrice : 0;
        buyHighest = Math.max(buyHighest, bar.high);

        // 0. 放量大涨(>=5%)且上影线占全天振幅>=10% (S7 最高优先级止盈)
        const isVolumeSurgeUpS7 = (bar.pct_change >= 5.0) && (bar.volume >= 1.3 * volMa5);
        const dayRange = Math.max(0.001, bar.high - bar.low);
        const shadowRatio = upperShadow / dayRange;

        if (isVolumeSurgeUpS7 && (shadowRatio >= 0.10)) {
          bar.signal_type = "S7";
          bar.signal_name = "止盈: 放量大涨带上影";
          bar.signal_position = "止盈清仓 / 锁定利润";
          bar.signal_reason = `持仓期间放量大涨(+${bar.pct_change.toFixed(2)}% >=5%)且上影线占振幅${(shadowRatio * 100).toFixed(0)}%(>=10%)，冲高锁定利润`;
          inPosition = false;
          s3Triggered = false;
          continue;
        }

        // 1. S4: 指标止损 (MACD绿柱重新放大>0.001 或 跌破10日线且MA5下拐)
        const condMacdReExpand = (macdBar < 0) && (prevMacd < 0) && (Math.abs(macdBar) - Math.abs(prevMacd) > 0.001);
        const ma10 = bar.ma10 || ma5;
        const ma5DropRatio = (prevMa5 && ma5 && prevMa5 > 0) ? (prevMa5 - ma5) / prevMa5 : 0;
        const macdBullExpanding = (macdBar > 0) && (macdBar >= prevMacd);
        const maBreakDown = (ma10 !== null) && (bar.close < ma10);
        const ma5SignificantDown = (ma5DropRatio >= 0.005 && maBreakDown) || (ma5 < prevMa5 * 0.995 && maBreakDown);
        const condMaTurnDown = (ma5 !== null) && (prevMa5 !== null) && ma5SignificantDown && (!macdBullExpanding);

        if (condMacdReExpand || condMaTurnDown) {
          bar.signal_type = "S4";
          bar.signal_name = "止损: 指标走坏";
          bar.signal_position = "100% 严格止损";
          const reasonDetail = condMacdReExpand ? "MACD绿柱重新放大(>0.001)" : "破位10日线且MA5下拐";
          bar.signal_reason = `触发指标止损(${reasonDetail})，必须严格离场防范套牢`;
          inPosition = false;
          s3Triggered = false;
          continue;
        }

        // 2. S1: 强势/弱势分级止盈 (DIF 0轴线上线下分级)
        const recent3dJs = [];
        for (let j = Math.max(0, i - 3); j <= i; j++) recent3dJs.push(klines[j].j || 50.0);
        const kdjExactDeath = (prevK >= prevD) && (kVal < dVal);
        const kdjNearDeath = (jVal < prevJ) && (kVal >= dVal) && (kVal - dVal <= 2.5) && (kVal - dVal <= 0.45 * (prevK - prevD));
        const kdjDeathOrNear = kdjExactDeath || kdjNearDeath;
        const dFilterPassed = dVal >= 50;

        let s1Triggered = false;
        let s1Reason = "";

        if (dif < 0) {
          // 场景 1: DIF < 0 弱势反弹
          const hasJOverbought = recent3dJs.some(v => v >= 80);
          if (hasJOverbought && kdjDeathOrNear && dFilterPassed) {
            s1Triggered = true;
            const detail = kdjExactDeath ? "正式死叉" : `预判死叉(间距仅${(kVal - dVal).toFixed(2)})`;
            s1Reason = `0轴下方弱势反弹，J值高位(>80)回落，KDJ(${detail})，快速落袋为安`;
          }
        } else {
          // 场景 2: DIF >= 0 强势行情
          const hasJExtreme = recent3dJs.some(v => v >= 100);
          const condJ100Death = hasJExtreme && kdjExactDeath && dFilterPassed;
          const condRedShrink3d = (macdBar >= 0) && (prevMacd > 0) && (prev2Macd > 0) && (prev3Macd > 0) &&
                                  (macdBar < prevMacd) && (prevMacd < prev2Macd) && (prev2Macd < prev3Macd);
          const condMacdDeath = (prevMacd > 0) && (macdBar <= 0) && (prevDif >= prevDea) && (dif <= dea);

          if (condJ100Death) {
            s1Triggered = true;
            s1Reason = "0轴上方强势行情，J值冲破100极端超买后KDJ正式死叉(K<D)，高位锁定利润";
          } else if (condRedShrink3d) {
            s1Triggered = true;
            s1Reason = "0轴上方强势行情，MACD红柱连续3日逐根缩短，提前锁定利润";
          } else if (condMacdDeath) {
            s1Triggered = true;
            s1Reason = "0轴上方强势行情，MACD正式死叉(DIF下穿DEA)，兜底无条件清仓";
          }
        }

        if (s1Triggered) {
          bar.signal_type = "S1";
          bar.signal_name = "止盈: 强势/弱势分级止盈";
          bar.signal_position = "止盈清仓 / 锁定利润";
          bar.signal_reason = s1Reason;
          inPosition = false;
          s3Triggered = false;
          continue;
        }

        // 3. S2: 放量长上影线
        const volumeBurst = bar.volume >= 1.5 * volMa5;
        const longUpper = upperShadow >= 2.0 * Math.max(0.001, candleBody);
        const recentUp = (prevBar.pct_change > 0 && prev2Bar.pct_change > 0) || (profitPct >= 0.03);
        if (volumeBurst && longUpper && recentUp) {
          bar.signal_type = "S2";
          bar.signal_name = "止盈: 放量长上影线";
          bar.signal_position = "减仓 / 锁定利润";
          bar.signal_reason = `高位放量(${(bar.volume / volMa5).toFixed(1)}倍均量)收长上影线，主力抛压强烈`;
          inPosition = false;
          s3Triggered = false;
          continue;
        }

        // 4. S3: 盈利>=5% 首次减仓 50%
        if (profitPct >= 0.05 && (!s3Triggered)) {
          bar.signal_type = "S3";
          bar.signal_name = "止盈: 目标落袋50%";
          bar.signal_position = "减仓50% / 保留50%底仓";
          bar.signal_reason = `持仓盈利达到 ${(profitPct * 100).toFixed(2)}%，首次触及5%目标止盈点，减仓50%锁定利润，保留50%底仓`;
          s3Triggered = true;
          continue;
        }
      }
    }
  }

  // 获取观察池列表与分类状态
  async function getWatchPool() {
    let customList = [];
    try {
      const saved = localStorage.getItem(STORAGE_KEY_WATCHLIST);
      if (saved) customList = JSON.parse(saved);
    } catch (e) {}

    const listToLoad = (customList && customList.length > 0) ? customList : DEFAULT_SECTOR_ETFS;

    // 并发拉取各标的的 K 线数据并判别状态
    const promises = listToLoad.map(async (item) => {
      const code = item.code || item.symbol;
      const data = await getDailyKlines(code, 80);
      const klines = data.klines || [];
      const quote = await getRealtimeQuote(code);

      if (klines.length === 0) {
        const cur = (quote && quote.current > 0) ? quote.current : (item.close || 1.0);
        const prev = (quote && quote.prev_close > 0) ? quote.prev_close : (item.prev_close || cur);
        const chg = (quote && typeof quote.change === 'number') ? quote.change : (cur - prev);
        const pct = (quote && typeof quote.pct_change === 'number') ? quote.pct_change : (prev > 0 ? (cur - prev) / prev * 100 : 0);
        return {
          sector: item.sector || "ETF",
          name: item.desc || item.name || (quote && quote.name) || code,
          code: code,
          symbol: code,
          current: cur,
          close: cur,
          price: cur,
          prev_close: prev,
          open: (quote && quote.open) || cur,
          high: (quote && quote.high) || cur,
          low: (quote && quote.low) || cur,
          change: Math.round(chg * 1000) / 1000,
          pct_change: Math.round(pct * 100) / 100,
          tag: "继续观望",
          tag_color: "#64748b",
          tag_group: "观望",
          sort_priority: 10,
          reason_summary: "等待更多交易数据确认",
          latest_bar: null
        };
      }

      const bar = klines[klines.length - 1];
      const todaySig = bar.signal_type;

      let inPos = false;
      let hasS3Holding = false;
      let buyCostPrice = bar.close;
      let buyDate = "";

      for (let j = klines.length - 2; j >= 0; j--) {
        const sig = klines[j].signal_type;
        if (sig === "B" || sig === "B1") {
          inPos = true;
          buyCostPrice = klines[j].close;
          buyDate = klines[j].date;
          break;
        } else if (sig === "S1" || sig === "S2" || sig === "S4" || sig === "S7") {
          inPos = false;
          hasS3Holding = false;
          break;
        } else if (sig === "S3") {
          inPos = true;
          hasS3Holding = true;
          // S3 只是卖出半仓，持仓成本必须继续向前追溯至真正的建仓买点 B，绝不能重置成本与收益率！
          continue;
        }
      }

      let tag = "继续观望";
      let tagColor = "#64748b";
      let tagGroup = "观望";
      let sortPriority = 10;
      let reasonSummary = "当前形态震荡蓄势，未触发共振买点";

      if (todaySig === "B" || todaySig === "B1") {
        tag = "尾盘买入";
        tagColor = "#dc2626"; // 鲜艳大红 (买入专用)
        tagGroup = "买入";
        sortPriority = 100;
        reasonSummary = "日K多指标共振确认，统一尾盘(14:30~14:50)建仓";
      } else if (["S1", "S2", "S7", "S4"].includes(todaySig)) {
        tag = "今天卖出";
        tagColor = "#16a34a"; // 鲜艳大绿 (卖出专用)
        tagGroup = "卖出";
        sortPriority = 95;
        reasonSummary = "触发分级止盈/止损卖点，建议平仓";
      } else if (todaySig === "S3") {
        tag = "减半止盈";
        tagColor = "#f59e0b"; // 醒目琥珀金 (减仓50%专用)
        tagGroup = "减仓";
        sortPriority = 90;
        reasonSummary = "盈利触及5%，止盈减半(保留50%底仓)";
      } else if (inPos) {
        if (hasS3Holding) {
          tag = "持仓(50%底仓)";
          tagColor = "#f97316";
          tagGroup = "持有";
          sortPriority = 80;
          reasonSummary = "盈利已锁定50%，留50%底仓观察";
        } else {
          tag = "观望持仓";
          tagColor = "#ea580c";
          tagGroup = "持有";
          sortPriority = 75;
          reasonSummary = "多头趋势保持良好，继续持有观察";
        }
      } else {
        // 评估是否“即将满足”
        const prev = klines[klines.length - 2];
        const ma5 = bar.ma5;
        const prevMa5 = prev ? prev.ma5 : null;
        const c1 = ma5 !== null && prevMa5 !== null && ma5 >= prevMa5 - 1e-5;
        const c2 = bar.dif > (prev ? prev.dif : 0);
        const c3 = bar.k > bar.d;
        const score = (c1 ? 1 : 0) + (c2 ? 1 : 0) + (c3 ? 1 : 0);
        if (score >= 2) {
          tag = "即将满足";
          tagColor = "#2563eb";
          tagGroup = "即将满足";
          sortPriority = 60;
          reasonSummary = "部分关键技术指标转多，密切留意尾盘共振";
        }
      }

      const prevCloseVal = (quote && quote.prev_close > 0) ? quote.prev_close : (klines.length > 1 ? klines[klines.length - 2].close : bar.close);
      const curPriceVal = (quote && quote.current > 0) ? quote.current : bar.close;
      const highVal = (quote && quote.high > 0) ? quote.high : (bar.high || curPriceVal);
      const lowVal = (quote && quote.low > 0) ? quote.low : (bar.low || curPriceVal);
      const openVal = (quote && quote.open > 0) ? quote.open : (bar.open || curPriceVal);
      const chgVal = (quote && typeof quote.change === 'number') ? quote.change : (bar.change || (curPriceVal - prevCloseVal));
      const pctChgVal = (quote && typeof quote.pct_change === 'number') ? quote.pct_change : (bar.pct_change || (prevCloseVal > 0 ? (curPriceVal - prevCloseVal) / prevCloseVal * 100 : 0));

      return {
        sector: item.sector || "ETF板块",
        name: item.desc || item.name || data.name || (quote && quote.name) || code,
        code: code,
        symbol: code,
        current: curPriceVal,
        close: curPriceVal,
        price: curPriceVal,
        prev_close: prevCloseVal,
        open: openVal,
        high: highVal,
        low: lowVal,
        change: Math.round(chgVal * 1000) / 1000,
        pct_change: Math.round(pctChgVal * 100) / 100,
        tag: tag,
        tag_color: tagColor,
        tag_group: tagGroup,
        sort_priority: sortPriority,
        reason_summary: reasonSummary,
        cost_price: inPos ? buyCostPrice : 0,
        buy_cost_price: inPos ? buyCostPrice : 0,
        buy_date: buyDate,
        has_s3_holding: hasS3Holding,
        is_s3_today: (todaySig === "S3"),
        signal_type: todaySig,
        latest_bar: bar
      };
    });

    const results = await Promise.all(promises);
    // 按优先级降序排序 (买入 > 卖出 > 持有 > 即将满足 > 观望)
    results.sort((a, b) => b.sort_priority - a.sort_priority);
    return results;
  }

  // 搜索股票/ETF (支持本地ETF池即时检索 + 在线智能联想)
  async function searchStock(keyword) {
    if (!keyword) return [];
    const qRaw = keyword.trim().toLowerCase();
    const localMatches = [];

    // 优先匹配本地 22 只主流 ETF 池与自定义自选池
    for (const item of DEFAULT_SECTOR_ETFS) {
      const code = item.code.toLowerCase();
      const desc = item.desc.toLowerCase();
      const sector = (item.sector || "").toLowerCase();
      if (code.includes(qRaw) || desc.includes(qRaw) || sector.includes(qRaw)) {
        localMatches.push({
          symbol: item.code,
          code: item.code.slice(2),
          name: item.desc,
          market: item.code.slice(0, 2).toUpperCase()
        });
      }
    }

    const q = encodeURIComponent(keyword.trim());
    const url = `https://smartbox.gtimg.cn/s3/?t=all&q=${q}`;

    return new Promise((resolve) => {
      const script = document.createElement("script");
      const callbackName = "v_hint";
      script.src = url;
      const timeout = setTimeout(() => {
        try { document.body.removeChild(script); } catch (e) {}
        resolve(localMatches.slice(0, 8));
      }, 1800);

      script.onload = () => {
        clearTimeout(timeout);
        try {
          const raw = window[callbackName] || "";
          const items = raw.split("^");
          const results = [...localMatches];
          for (const it of items) {
            const p = it.split("~");
            if (p.length >= 3) {
              const mkt = p[0];
              const code = p[1];
              const name = p[2];
              const sym = mkt + code;
              if (!results.some(x => x.symbol === sym)) {
                results.push({
                  symbol: sym,
                  code: code,
                  name: name,
                  market: mkt.toUpperCase()
                });
              }
            }
          }
          document.body.removeChild(script);
          resolve(results.slice(0, 8));
        } catch (e) {
          resolve(localMatches.slice(0, 8));
        }
      };
      script.onerror = () => {
        clearTimeout(timeout);
        try { document.body.removeChild(script); } catch (e) {}
        resolve(localMatches.slice(0, 8));
      };
      document.body.appendChild(script);
    });
  }

  // 区间涨跌统计
  function calculateInterval(klines, startDateStr, endDateStr) {
    if (!klines || klines.length === 0) return null;
    const filtered = klines.filter(k => k.date >= startDateStr && k.date <= endDateStr);
    if (filtered.length === 0) return null;

    const startBar = filtered[0];
    const endBar = filtered[filtered.length - 1];
    const startPrice = startBar.open;
    const endPrice = endBar.close;
    const changeVal = Math.round((endPrice - startPrice) * 1000) / 1000;
    const pctChange = startPrice > 0 ? Math.round(((changeVal / startPrice) * 100) * 100) / 100 : 0;

    let maxPrice = -Infinity;
    let minPrice = Infinity;
    let totalVol = 0;
    for (const b of filtered) {
      if (b.high > maxPrice) maxPrice = b.high;
      if (b.low < minPrice) minPrice = b.low;
      totalVol += b.volume;
    }

    return {
      start_date: startBar.date,
      end_date: endBar.date,
      start_price: startPrice,
      end_price: endPrice,
      change_val: changeVal,
      pct_change: pctChange,
      max_price: maxPrice,
      min_price: minPrice,
      total_volume: totalVol,
      bar_count: filtered.length
    };
  }

  function calculateIntervalByPreset(klines, presetKey) {
    if (!klines || klines.length === 0) return null;
    const totalCount = klines.length;
    let count = 20;
    if (presetKey === "1w") count = 5;
    else if (presetKey === "1m") count = 20;
    else if (presetKey === "3m") count = 60;
    else if (presetKey === "6m") count = 120;
    else if (presetKey === "1y") count = 240;
    else if (presetKey === "all") count = totalCount;

    const startIdx = Math.max(0, totalCount - count);
    const sub = klines.slice(startIdx);
    if (sub.length === 0) return null;

    return calculateInterval(klines, sub[0].date, sub[sub.length - 1].date);
  }

  const STORAGE_KEY_TOTAL_POS_CAPITAL = "stock_master_total_pos_capital";

  // 模拟持仓数据与资金管理器 (Paper Portfolio Manager)
  const PortfolioManager = {
    getData: function() {
      let data = {
        total_capital: 100000,
        total_pos_capital: 100000,
        available_cash: 50000,
        positions: {}, // symbol -> { symbol, name, hands, cost_price, buy_date }
        trades: []
      };
      try {
        const saved = localStorage.getItem(STORAGE_KEY_PORTFOLIO);
        if (saved) data = Object.assign(data, JSON.parse(saved));
      } catch (e) {}

      try {
        const savedPosCap = localStorage.getItem(STORAGE_KEY_TOTAL_POS_CAPITAL);
        if (savedPosCap) {
          const num = parseFloat(savedPosCap);
          if (!isNaN(num) && num > 0) data.total_pos_capital = num;
        }
      } catch (e) {}

      // 移动端老持仓种子数据恢复与锁定校验 (确保 5 只老持仓手数与成本绝不丢失)
      const seedVer = localStorage.getItem('stock_master_mobile_seed_v5');
      if (!data.positions || Object.keys(data.positions).length === 0 || seedVer !== 'v5_clean_locked_holdings') {
        const seeds = {
          '159992': { symbol: '159992', code: '159992', name: '创新药', hands: 17, cost_price: 0.830, buy_date: '2026-09-15' },
          '159819': { symbol: '159819', code: '159819', name: '人工智能', hands: 10, cost_price: 1.723, buy_date: '2026-09-15' },
          '159995': { symbol: '159995', code: '159995', name: '芯片', hands: 15, cost_price: 1.124, buy_date: '2026-09-15' },
          '159516': { symbol: '159516', code: '159516', name: '半导体设备', hands: 23, cost_price: 0.706, buy_date: '2026-09-15' },
          '159997': { symbol: '159997', code: '159997', name: '电子', hands: 8, cost_price: 2.067, buy_date: '2026-09-15' }
        };
        const cleanPositions = {};
        Object.keys(seeds).forEach(k => {
          cleanPositions[k] = Object.assign({}, seeds[k]);
        });
        if (data.positions && typeof data.positions === 'object') {
          Object.keys(data.positions).forEach(k => {
            if (!cleanPositions[k] && data.positions[k] && data.positions[k].hands > 0 && data.positions[k].buy_date > '2026-09-15' && data.positions[k].hands !== 15) {
              cleanPositions[k] = data.positions[k];
            }
          });
        }
        data.positions = cleanPositions;
        localStorage.setItem('stock_master_mobile_seed_v5', 'v5_clean_locked_holdings');
        this.saveData(data);
      }

      if (!data.total_pos_capital) data.total_pos_capital = 100000;
      return data;
    },
    saveData: function(data) {
      try {
        localStorage.setItem(STORAGE_KEY_PORTFOLIO, JSON.stringify(data));
      } catch (e) {}
    },
    getTotalPosCapital: function() {
      // 持仓预算不再由用户手动修改，而是根据用户输入的可用现金买入自动计算！
      const data = this.getData();
      const curCash = data.available_cash || 0;
      return Math.max(100, curCash);
    },
    setTotalPosCapital: function(amount) {
      // 兼容接口，若传入则同步更新为现金
      return this.setAvailableCash(amount);
    },
    deposit: function(amount = 10000) {
      const data = this.getData();
      data.total_capital += amount;
      data.available_cash += amount;
      this.saveData(data);
      return data;
    },
    reset: function(total = 100000) {
      const data = {
        total_capital: total,
        total_pos_capital: total,
        available_cash: total,
        positions: {},
        trades: []
      };
      this.saveData(data);
      return data;
    },
    setAvailableCash: function(amount) {
      const data = this.getData();
      data.available_cash = Math.max(0, parseFloat(amount) || 0);
      this.saveData(data);
      return data;
    },
    addAvailableCash: function(delta) {
      const data = this.getData();
      const cur = data.available_cash || 0;
      data.available_cash = Math.max(0, cur + (parseFloat(delta) || 0));
      this.saveData(data);
      return data;
    },
    setHolding: function(symbol, name, hands, costPrice) {
      const data = this.getData();
      if (!data.positions) data.positions = {};
      const s = String(symbol).trim().toLowerCase();
      data.positions[s] = {
        symbol: s,
        code: s.replace(/^[a-z]+/, ''),
        name: name || s,
        hands: Math.max(1, parseInt(hands, 10) || 1),
        cost_price: Math.max(0.001, parseFloat(costPrice) || 1.0),
        buy_date: new Date().toISOString().slice(0, 10)
      };
      this.saveData(data);
      return data;
    },
    removeHolding: function(symbol) {
      const data = this.getData();
      const s = String(symbol).trim().toLowerCase();
      if (data.positions && data.positions[s]) {
        delete data.positions[s];
        this.saveData(data);
      }
      return data;
    },
    computePaperPortfolioAllocations: function(poolData) {
      const isSettled = isMobileSettlementAfter1450();
      const portData = this.getData();
      const currentAvailableCash = portData.available_cash || 0;
      const pool = (poolData && poolData.length > 0) ? poolData : [];

      let totalPositionMarketVal = 0;
      let totalPositionCost = 0;
      let totalSettleCash = 0;
      let totalClosedProfit = 0;
      let totalTodayPnl = 0;

      const activeCandidates = [];
      const itemStates = [];
      const mapBySymbol = {};

      const recordedPositions = portData.positions || {};

      pool.forEach(item => {
        const sym = item.symbol || item.code || '';
        const itemCodeClean = sym.replace(/^(sh|sz)/i, '').toLowerCase();
        let curPrice = (typeof item.current === 'number' && item.current > 0) ? item.current : (item.close || 1.0);
        let prevClose = (typeof item.prev_close === 'number' && item.prev_close > 0) ? item.prev_close : (typeof item.close === 'number' && item.close > 0 ? item.close : curPrice);

        const tagText = (item.tag || item.reason_summary || '').trim();
        const isCallback = tagText.includes('回调') || tagText.includes('空仓');
        const isBuyToday = !isCallback && (tagText.includes('尾盘买入') || tagText.includes('今天买入') || tagText.includes('今日买点'));
        const isS3Today = !isCallback && (
          item.signal_type === 'S3' ||
          item.is_s3_today ||
          tagText.includes('减半') ||
          tagText.includes('减仓50%') ||
          (item.reason_summary && item.reason_summary.includes('减仓50%'))
        );
        const isSellToday = !isCallback && !isS3Today && (tagText.includes('今天卖出') || tagText.includes('今日卖点'));

        const recordedPos = recordedPositions[itemCodeClean] || recordedPositions[sym.toLowerCase()];
        const hasExistingHolding = Boolean(recordedPos && recordedPos.hands > 0);

        const isHolding = hasExistingHolding && !isCallback && !isBuyToday && !isSellToday && !isS3Today;
        const isPending = !isCallback && !isBuyToday && !isSellToday && !isHolding && !isS3Today && tagText.includes('即将满足');

        let costPrice = curPrice;
        if (hasExistingHolding && recordedPos.cost_price > 0) {
          costPrice = recordedPos.cost_price;
        } else {
          const bp = (typeof item.buy_cost_price === 'number' && item.buy_cost_price > 0) ? item.buy_cost_price : (item.cost_price || item.buy_price);
          if (typeof bp === 'number' && bp > 0) {
            costPrice = bp;
          } else if (isBuyToday) {
            costPrice = curPrice;
          } else if (isHolding || isS3Today) {
            costPrice = prevClose > 0 ? (prevClose * (1 - (item.pct_change || 0) * 0.01 * 0.5)) : curPrice;
          } else if (isSellToday) {
            costPrice = prevClose > 0 ? (prevClose * 0.985) : (curPrice * 0.985);
          }
        }

        const score = typeof item.score === 'number' ? item.score : 3;
        const trendMult = (item.dif || 0) > 0 ? 1.3 : 1.0;
        const confMult = score >= 4 ? 1.5 : (score === 3 ? 1.0 : 0.7);
        const weight = Math.max(0.5, score * trendMult * confMult);

        const stateObj = {
          item,
          sym,
          itemCodeClean,
          name: item.name || sym,
          code: item.code || sym,
          sector: item.sector || 'ETF',
          tag: item.tag || '',
          tag_color: item.tag_color || '#3b82f6',
          reason_summary: item.reason_summary || '',
          curPrice,
          prevClose,
          costPrice,
          score,
          weight,
          isBuyToday,
          isHolding,
          isSellToday,
          isS3Today,
          isPending,
          isCallback,
          isSettled,
          hasExistingHolding,
          recordedPos,
          isLockedHolding: false,
          allocatedShares: 0,
          allocatedHands: 0,
          allocatedCost: 0,
          soldHands: 0,
          soldShares: 0,
          plannedSoldHands: 0,
          plannedRemainHands: 0,
          plannedHands: 0,
          settleVal: 0,
          realizedProfit: 0,
          marketVal: 0,
          pnl: 0,
          pnlPct: 0,
          todayPnl: 0,
          insufficientCash: false
        };

        itemStates.push(stateObj);
        mapBySymbol[itemCodeClean] = stateObj;
        mapBySymbol[sym.toLowerCase()] = stateObj;
        mapBySymbol[sym] = stateObj;
      });

      // 补充检查：若用户持仓库中已有标的未出现在行情池 pool 中，主动纳入统计
      Object.keys(recordedPositions).forEach(k => {
        const p = recordedPositions[k];
        if (p && p.hands > 0 && !mapBySymbol[k]) {
          const symCode = (p.code || p.symbol || k).toLowerCase();
          const cleanCode = symCode.replace(/^(sh|sz)/i, '');
          const curPrice = p.cost_price || 1.0;
          const stateObj = {
            item: {
              code: cleanCode,
              symbol: symCode,
              name: p.name || cleanCode,
              sector: '持仓标的',
              close: curPrice,
              current: curPrice,
              prev_close: curPrice,
              tag: '持仓中',
              status_desc: '持仓中',
              pct_change: 0.0
            },
            sym: symCode,
            itemCodeClean: cleanCode,
            name: p.name || cleanCode,
            code: cleanCode,
            sector: '持仓标的',
            tag: '持仓中',
            tag_color: '#3b82f6',
            reason_summary: '固化持仓标的',
            curPrice: curPrice,
            prevClose: curPrice,
            costPrice: p.cost_price || curPrice,
            score: 3,
            weight: 3,
            isBuyToday: false,
            isHolding: true,
            isSellToday: false,
            isS3Today: false,
            isPending: false,
            isCallback: false,
            isSettled,
            hasExistingHolding: true,
            recordedPos: p,
            isLockedHolding: true,
            allocatedShares: p.hands * 100,
            allocatedHands: p.hands,
            allocatedCost: p.hands * 100 * (p.cost_price || curPrice),
            soldHands: 0,
            soldShares: 0,
            plannedSoldHands: 0,
            plannedRemainHands: 0,
            plannedHands: 0,
            settleVal: 0,
            realizedProfit: 0,
            marketVal: 0,
            pnl: 0,
            pnlPct: 0,
            todayPnl: 0,
            insufficientCash: false
          };
          itemStates.push(stateObj);
          mapBySymbol[cleanCode] = stateObj;
          mapBySymbol[symCode] = stateObj;
        }
      });

      // 阶段一：老持仓手数与成本 100% 固化锁定
      let oldHoldingCost = 0;
      itemStates.forEach(state => {
        const isOldHoldingCandidate = state.hasExistingHolding && (state.isHolding || state.isS3Today || (!state.isSellToday && !state.isBuyToday));
        if (isOldHoldingCandidate) {
          const lockedHands = (state.recordedPos && state.recordedPos.hands > 0) ? state.recordedPos.hands : 0;
          if (lockedHands <= 0) return;

          if (state.isS3Today) {
            if (isSettled) {
              const soldHands = Math.max(1, Math.floor(lockedHands * 0.5));
              const remainHands = Math.max(0, lockedHands - soldHands);
              state.allocatedHands = remainHands;
              state.allocatedShares = remainHands * 100;
              state.allocatedCost = state.allocatedShares * state.costPrice;
              state.origHands = lockedHands;
              state.plannedSoldHands = soldHands;
              state.plannedRemainHands = remainHands;
              state.soldHands = soldHands;
              state.soldShares = soldHands * 100;

              const sellPrice = (state.item && state.item.high > 0) ? state.item.high : state.curPrice;
              const settleVal = state.soldShares * sellPrice;
              const realizedProfit = settleVal - (state.soldShares * state.costPrice);
              state.settleVal = settleVal;
              state.realizedProfit = realizedProfit;

              totalSettleCash += settleVal;
              totalClosedProfit += realizedProfit;
            } else {
              const planSold = Math.max(1, Math.floor(lockedHands * 0.5));
              state.allocatedHands = lockedHands;
              state.allocatedShares = lockedHands * 100;
              state.allocatedCost = state.allocatedShares * state.costPrice;
              state.origHands = lockedHands;
              state.plannedSoldHands = planSold;
              state.plannedRemainHands = Math.max(0, lockedHands - planSold);
              state.soldHands = 0;
              state.soldShares = 0;
            }
          } else {
            state.allocatedHands = lockedHands;
            state.allocatedShares = lockedHands * 100;
            state.allocatedCost = state.allocatedShares * state.costPrice;
          }

          state.isLockedHolding = true;
          oldHoldingCost += state.allocatedCost;
          activeCandidates.push(state);
        } else if (state.isSellToday && state.hasExistingHolding) {
          const origHands = (state.recordedPos && state.recordedPos.hands > 0) ? state.recordedPos.hands : 0;
          if (origHands <= 0) return;

          const sellPrice = (state.item && state.item.high > 0) ? state.item.high : state.curPrice;
          if (isSettled) {
            state.allocatedHands = 0;
            state.allocatedShares = 0;
            state.allocatedCost = 0;
            state.soldHands = origHands;
            state.soldShares = origHands * 100;
            const cost = state.soldShares * state.costPrice;
            const settleVal = state.soldShares * sellPrice;
            const profit = settleVal - cost;
            state.settleVal = settleVal;
            state.realizedProfit = profit;
            state.profit = profit;

            totalSettleCash += settleVal;
            totalClosedProfit += profit;
          } else {
            state.allocatedHands = origHands;
            state.allocatedShares = origHands * 100;
            state.allocatedCost = state.allocatedShares * state.costPrice;
            state.origHands = origHands;
            state.plannedSoldHands = origHands;
            state.soldHands = 0;
            state.soldShares = 0;
            oldHoldingCost += state.allocatedCost;
            activeCandidates.push(state);
          }
        }
      });

      // 阶段二：新买入标的仅消耗【剩余可用现金】
      const availableCashForNewBuys = Math.max(0, currentAvailableCash - oldHoldingCost + totalSettleCash);
      const buyCandidates = itemStates.filter(s => s.isBuyToday);

      if (buyCandidates.length > 0) {
        if (isSettled) {
          const totalBuyWeight = buyCandidates.reduce((acc, c) => acc + c.weight, 0);
          let remainCashForBuys = availableCashForNewBuys;

          buyCandidates.forEach(cand => {
            const portion = totalBuyWeight > 0 ? (cand.weight / totalBuyWeight) : (1 / buyCandidates.length);
            const targetBudget = availableCashForNewBuys * portion;
            const hands = Math.floor(targetBudget / cand.costPrice / 100);
            if (hands >= 1 && remainCashForBuys >= (hands * 100 * cand.costPrice)) {
              cand.allocatedHands = hands;
              cand.allocatedShares = hands * 100;
              cand.allocatedCost = cand.allocatedShares * cand.costPrice;
              remainCashForBuys -= cand.allocatedCost;
            } else {
              cand.allocatedHands = 0;
              cand.allocatedShares = 0;
              cand.allocatedCost = 0;
              cand.insufficientCash = true;
              cand.plannedHands = Math.max(1, Math.round(targetBudget / cand.costPrice / 100));
            }
          });

          buyCandidates.sort((a, b) => b.weight - a.weight);
          buyCandidates.forEach(cand => {
            const oneHandCost = cand.costPrice * 100;
            if (remainCashForBuys >= oneHandCost) {
              const extraHands = Math.floor(remainCashForBuys / oneHandCost);
              if (extraHands > 0) {
                cand.allocatedHands += extraHands;
                cand.allocatedShares = cand.allocatedHands * 100;
                const extraCost = extraHands * 100 * cand.costPrice;
                cand.allocatedCost += extraCost;
                remainCashForBuys -= extraCost;
                cand.insufficientCash = false;
              }
            }
          });

          buyCandidates.forEach(cand => {
            if (cand.allocatedHands > 0) {
              activeCandidates.push(cand);
              if (!cand.hasExistingHolding) {
                this.setHolding(cand.sym, cand.name || cand.sym, cand.allocatedHands, cand.costPrice);
              }
            }
          });
        } else {
          buyCandidates.forEach(cand => {
            const estPortion = Math.min(0.35, Math.max(0.10, cand.weight / 15));
            const estBudget = Math.max(cand.costPrice * 100, (availableCashForNewBuys > 0 ? availableCashForNewBuys : currentAvailableCash * 0.2) * estPortion);
            const calc = calculateSharesAndAmount(estBudget, cand.costPrice);
            cand.plannedHands = Math.max(1, calc.hands);
            cand.plannedShares = cand.plannedHands * 100;
            cand.allocatedHands = 0;
            cand.allocatedShares = 0;
            cand.allocatedCost = 0;
            cand.marketVal = 0;
            if (availableCashForNewBuys < (cand.costPrice * 100)) {
              cand.insufficientCash = true;
            }
          });
        }
      }

      // 阶段三：统计市值与盈亏
      activeCandidates.forEach(cand => {
        const mVal = cand.allocatedShares * cand.curPrice;
        const holdPnl = mVal - cand.allocatedCost;
        const totalStockPnl = holdPnl + (cand.realizedProfit || 0);
        const totalStockCost = cand.allocatedCost + ((cand.soldShares || 0) * cand.costPrice);
        const pnlPct = totalStockCost > 0 ? (totalStockPnl / totalStockCost * 100) : 0;
        const prevClose = (cand.prevClose && cand.prevClose > 0)
          ? cand.prevClose
          : (cand.item && cand.item.prev_close > 0 ? cand.item.prev_close : (cand.item && cand.item.current ? (cand.item.current - (cand.item.change || 0)) : cand.costPrice));
        const sellPrice = (cand.item && cand.item.high > 0) ? cand.item.high : cand.curPrice;
        const todayPnl = cand.isBuyToday
          ? ((cand.curPrice - cand.costPrice) * cand.allocatedShares)
          : ((cand.curPrice - prevClose) * cand.allocatedShares + (cand.isS3Today && isSettled ? ((sellPrice - prevClose) * (cand.soldShares || 0)) : 0));
        const todayPct = prevClose > 0 ? ((cand.curPrice - prevClose) / prevClose * 100) : (cand.item ? (cand.item.pct_change || 0) : 0);

        cand.marketVal = mVal;
        cand.pnl = totalStockPnl;
        cand.pnlPct = pnlPct;
        cand.todayPnl = todayPnl;
        cand.todayPct = todayPct;
        cand.prevClose = prevClose;

        totalPositionMarketVal += mVal;
        totalPositionCost += cand.allocatedCost;
        totalTodayPnl += todayPnl;
      });

      if (isSettled) {
        itemStates.forEach(state => {
          if (state.isSellToday && state.soldShares > 0) {
            const sellPrice = (state.item && state.item.high > 0) ? state.item.high : state.curPrice;
            const prevClose = (state.prevClose && state.prevClose > 0)
              ? state.prevClose
              : (state.item && state.item.prev_close > 0 ? state.item.prev_close : (state.curPrice));
            const todaySoldPnl = (sellPrice - prevClose) * state.soldShares;
            const todayPct = prevClose > 0 ? ((sellPrice - prevClose) / prevClose * 100) : (state.item ? (state.item.pct_change || 0) : 0);

            state.todayPnl = todaySoldPnl;
            state.todayPct = todayPct;
            state.prevClose = prevClose;

            totalTodayPnl += todaySoldPnl;
          }
        });
      }

      // 阶段四：资产守恒与现金流
      const realAvailableCash = Math.max(0, currentAvailableCash - totalPositionCost + totalSettleCash);
      const currentTotalAssets = realAvailableCash + totalPositionMarketVal;
      const effectiveTotalCapital = Math.max(currentAvailableCash, totalPositionCost + realAvailableCash - totalClosedProfit);
      const totalPnl = (totalPositionMarketVal - totalPositionCost) + totalClosedProfit;
      const totalPnlPct = effectiveTotalCapital > 0 ? (totalPnl / effectiveTotalCapital * 100) : (totalPositionCost > 0 ? (totalPnl / totalPositionCost * 100) : 0);

      return {
        isSettled,
        totalPosCapital: effectiveTotalCapital,
        totalCapital: effectiveTotalCapital,
        availableCash: currentAvailableCash,
        realAvailableCash,
        availableCashForNewBuys,
        currentTotalAssets,
        totalPositionMarketVal,
        totalPositionCost,
        totalSettleCash,
        totalClosedProfit,
        totalTodayPnl,
        totalPnl,
        totalPnlPct,
        activeCandidates,
        itemStates,
        mapBySymbol
      };
    }
  };

  // 14:50结算时间窗口判定
  function isMobileSettlementAfter1450() {
    const now = new Date();
    const day = now.getDay();
    const timeNum = now.getHours() * 100 + now.getMinutes();
    if (day === 0 || day === 6) return true;
    if (timeNum >= 915 && timeNum < 1450) return false;
    return true;
  }

  function calculateSharesAndAmount(budget, price) {
    if (!price || price <= 0 || !budget || budget <= 0) {
      return { shares: 0, hands: 0, actual: 0 };
    }
    const rawShares = budget / price;
    const hands = Math.floor(rawShares / 100);
    const shares = hands * 100;
    const actual = shares * price;
    return { shares, hands, actual };
  }

  return {
    normalizeSymbol,
    getRealtimeQuote,
    getDailyKlines,
    getWatchPool,
    searchStock,
    calculateInterval,
    calculateIntervalByPreset,
    isMobileSettlementAfter1450,
    computePaperPortfolioAllocations: function(poolData) {
      return PortfolioManager.computePaperPortfolioAllocations(poolData);
    },
    PortfolioManager,
    DEFAULT_SECTOR_ETFS,
    STORAGE_KEY_WATCHLIST,
    STORAGE_KEY_THEME
  };
})();

if (typeof window !== "undefined") {
  window.MobileQuantEngine = MobileQuantEngine;
}
