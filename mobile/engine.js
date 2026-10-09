/**
 * 手机版量化交易与数据引擎 (Pure Client-Side Quant Engine)
 * 100% 还原 Python 版 StockDataProvider 与 IntervalCalculator 的核心逻辑
 * 直接在移动端请求腾讯金融行情接口 (原生支持 CORS)，零服务器依赖
 */

const MobileQuantEngine = (function() {
  // 默认 23 只主流行业/主题 ETF 观察池 (4档量化共振分级)
  const DEFAULT_SECTOR_ETFS = [
    { sector: "动漫游戏", code: "sz159869", desc: "游戏ETF", close: 1.038, prev_close: 1.041, change: -0.003, pct_change: -0.29, tag: "60分4档买入", tag_color: "#b91c1c", reason_summary: "60分4档全仓共振(超跌拔起/量价突破)，建议100%全仓出击", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "A股创新药", code: "sz159992", desc: "创新药ETF", close: 0.872, prev_close: 0.872, change: 0.0, pct_change: 0.0, tag: "60分4档买入", tag_color: "#b91c1c", reason_summary: "60分4档全仓共振(超跌拔起/量价突破)，建议100%全仓出击", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "大金融证券", code: "sh512880", desc: "证券ETF", close: 1.029, prev_close: 1.031, change: -0.002, pct_change: -0.19, tag: "60分4档买入", tag_color: "#b91c1c", reason_summary: "60分4档全仓共振(超跌拔起/量价突破)，建议100%全仓出击", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "新能源车", code: "sh515030", desc: "新能源车ETF", close: 1.456, prev_close: 1.458, change: -0.002, pct_change: -0.14, tag: "60分3档买入", tag_color: "#dc2626", reason_summary: "60分3档重仓共振(站上MA5收红)，建议75%重仓建仓", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "光伏新能源", code: "sh515790", desc: "光伏ETF", close: 0.776, prev_close: 0.778, change: -0.002, pct_change: -0.26, tag: "60分3档买入", tag_color: "#dc2626", reason_summary: "60分3档重仓共振(站上MA5收红)，建议75%重仓建仓", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "通信技术", code: "sh515880", desc: "通信ETF", close: 0.626, prev_close: 0.627, change: -0.001, pct_change: -0.16, tag: "60分2档买入", tag_color: "#ea580c", reason_summary: "60分2档标准共振(三指标金叉)，建议50%半仓稳健建仓", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "国防军工", code: "sh512660", desc: "军工ETF", close: 1.160, prev_close: 1.142, change: 0.018, pct_change: 1.58, tag: "60分4档买入", tag_color: "#b91c1c", reason_summary: "60分4档全仓共振(超跌拔起/量价突破)，建议100%全仓出击", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "煤炭周期", code: "sh515220", desc: "煤炭ETF", close: 1.249, prev_close: 1.258, change: -0.009, pct_change: -0.72, tag: "60分4档买入", tag_color: "#b91c1c", reason_summary: "60分4档全仓共振(超跌拔起/量价突破)，建议100%全仓出击", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "创业板", code: "sz159915", desc: "创业板ETF", close: 3.064, prev_close: 3.053, change: 0.011, pct_change: 0.36, tag: "60分4档买入", tag_color: "#b91c1c", reason_summary: "60分4档全仓共振(超跌拔起/量价突破)，建议100%全仓出击", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "红利低波", code: "sh515180", desc: "红利ETF", close: 1.409, prev_close: 1.411, change: -0.002, pct_change: -0.14, tag: "60分4档买入", tag_color: "#b91c1c", reason_summary: "60分4档全仓共振(超跌拔起/量价突破)，建议100%全仓出击", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "港股互联网", code: "sz159792", desc: "港股通互联网ETF", close: 0.532, prev_close: 0.516, change: 0.016, pct_change: 3.10, tag: "30分3档买入", tag_color: "#dc2626", reason_summary: "30分3档重仓共振(站上MA5收红)，建议75%重仓建仓", trade_rule: "T+0", optimal_period: "30min" },
    { sector: "港股创新药", code: "sz159567", desc: "港股创新药ETF", close: 0.682, prev_close: 0.680, change: 0.002, pct_change: 0.29, tag: "观望持仓", tag_color: "#ea580c", reason_summary: "30分多头趋势保持良好，继续持有观察", trade_rule: "T+0", optimal_period: "30min" },
    { sector: "有色金属", code: "sh512400", desc: "有色金属ETF", close: 1.732, prev_close: 1.708, change: 0.024, pct_change: 1.41, tag: "观望持仓", tag_color: "#ea580c", reason_summary: "60分多头趋势保持良好，继续持有观察", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "恒生医疗", code: "sh513060", desc: "恒生医疗ETF", close: 0.571, prev_close: 0.565, change: 0.006, pct_change: 1.06, tag: "观望持仓", tag_color: "#ea580c", reason_summary: "30分多头趋势保持良好，继续持有观察", trade_rule: "T+0", optimal_period: "30min" },
    { sector: "人形机器人", code: "sh562500", desc: "机器人ETF", close: 0.934, prev_close: 0.916, change: 0.018, pct_change: 1.97, tag: "即将满足", tag_color: "#2563eb", reason_summary: "60分关键指标转多，密切留意共振", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "计算机软件", code: "sh512720", desc: "计算机ETF", close: 1.134, prev_close: 1.114, change: 0.020, pct_change: 1.80, tag: "蓄势回调", tag_color: "#94a3b8", reason_summary: "60分探底寻支撑，密切观察", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "电力绿电", code: "sz159611", desc: "电力ETF", close: 1.040, prev_close: 1.037, change: 0.003, pct_change: 0.29, tag: "蓄势回调", tag_color: "#94a3b8", reason_summary: "60分探底寻支撑，密切观察", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "人工智能", code: "sz159819", desc: "人工智能ETF", close: 1.762, prev_close: 1.714, change: 0.048, pct_change: 2.80, tag: "蓄势回调", tag_color: "#94a3b8", reason_summary: "60分探底寻支撑，密切观察", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "半导体芯片", code: "sz159995", desc: "芯片ETF", close: 1.152, prev_close: 1.114, change: 0.038, pct_change: 3.41, tag: "蓄势回调", tag_color: "#94a3b8", reason_summary: "60分探底寻支撑，密切观察", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "半导体设备", code: "sz159516", desc: "半导体设备ETF", close: 0.729, prev_close: 0.703, change: 0.026, pct_change: 3.70, tag: "蓄势回调", tag_color: "#94a3b8", reason_summary: "60分探底寻支撑，密切观察", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "消费电子", code: "sz159997", desc: "电子ETF", close: 2.114, prev_close: 2.059, change: 0.055, pct_change: 2.67, tag: "蓄势回调", tag_color: "#94a3b8", reason_summary: "60分探底寻支撑，密切观察", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "金融科技", code: "sz159851", desc: "金融科技ETF", close: 0.603, prev_close: 0.589, change: 0.014, pct_change: 2.38, tag: "蓄势回调", tag_color: "#94a3b8", reason_summary: "60分探底寻支撑，密切观察", trade_rule: "T+1", optimal_period: "60min" },
    { sector: "科创50", code: "sh588000", desc: "科创50ETF", close: 1.616, prev_close: 1.617, change: -0.001, pct_change: -0.06, tag: "蓄势回调", tag_color: "#94a3b8", reason_summary: "60分探底寻支撑，密切观察", trade_rule: "T+1", optimal_period: "60min" }
  ];

  const STORAGE_KEY_WATCHLIST = "stock_master_mobile_watchlist";
  const STORAGE_KEY_PORTFOLIO = "stock_master_mobile_portfolio";
  const STORAGE_KEY_THEME = "stock_master_mobile_theme";

  // 代码规范化
  function normalizeSymbol(raw) {
    if (!raw) return "sh515880";
    let s = String(raw).trim().toLowerCase();
    if (/^\d{6}$/.test(s)) {
      if (s.startsWith("6") || s.startsWith("9") || s.startsWith("688") || s.startsWith("588") || s.startsWith("51")) {
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

  // 获取 60 分钟 K 线历史数据 (调用腾讯 mkline 接口，原生支持 CORS)
  async function get60MinKlines(symbol, limit = 320) {
    const fullSym = normalizeSymbol(symbol);
    const url = `https://ifzq.gtimg.cn/appstock/app/kline/mkline?param=${fullSym},m60,,${limit}`;
    try {
      const resp = await fetch(url);
      const data = await resp.json();
      if (data && data.data && data.data[fullSym]) {
        const stockData = data.data[fullSym];
        const rawBars = stockData.m60 || [];
        const name = (stockData.qt && stockData.qt[fullSym] && stockData.qt[fullSym][1]) ? stockData.qt[fullSym][1] : fullSym;

        let prevClose = null;
        const klines = [];
        for (let i = 0; i < rawBars.length; i++) {
          const item = rawBars[i];
          if (!item || item.length < 6) continue;
          const dtStr = String(item[0]);
          let dPart = dtStr;
          let tPart = "";
          let dtFmt = dtStr;
          if (dtStr.length >= 12) {
            dPart = `${dtStr.slice(0, 4)}-${dtStr.slice(4, 6)}-${dtStr.slice(6, 8)}`;
            tPart = `${dtStr.slice(8, 10)}:${dtStr.slice(10, 12)}`;
            dtFmt = `${dPart} ${tPart}`;
          } else if (dtStr.length >= 8) {
            dPart = `${dtStr.slice(0, 4)}-${dtStr.slice(4, 6)}-${dtStr.slice(6, 8)}`;
            dtFmt = dPart;
          }

          const open = parseFloat(item[1]);
          const close = parseFloat(item[2]);
          const high = parseFloat(item[3]);
          const low = parseFloat(item[4]);
          const volume = parseFloat(item[5]) * 100;
          const amount = item[7] ? parseFloat(item[7]) * 10000 : 0;

          let pct_change = 0.0;
          if (prevClose !== null && prevClose > 0) {
            pct_change = Math.round(((close - prevClose) / prevClose * 100) * 100) / 100;
          }
          prevClose = close;

          klines.push({
            date: dtFmt,
            day_date: dPart,
            time: tPart,
            datetime: dtFmt,
            open,
            close,
            high,
            low,
            volume,
            amount,
            pct_change
          });
        }

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
      console.error("get60MinKlines error for " + fullSym, e);
    }
    return { symbol: fullSym, code: fullSym.slice(2), name: fullSym, klines: [] };
  }

  // 智能识别ETF交易制度 (T+0 vs T+1)
  function isT0Symbol(symbol, name = '') {
    if (!symbol) return false;
    const sym = String(symbol).toLowerCase().trim();
    const code = sym.startsWith('sh') || sym.startsWith('sz') ? sym.slice(2) : sym;
    const nameStr = String(name || '');
    const t0Keywords = ['港股', '恒生', '中概', '纳指', '纳斯达克', '标普', '日经', '德国', '黄金', '白银', '豆粕', '有色期货', '大宗商品', '海外', '境外', '美股', '道琼斯', '亚太', '东证', '国债', '转债', '货币'];
    if (t0Keywords.some(k => nameStr.includes(k))) return true;
    if (sym.startsWith('sh')) {
      if (code.startsWith('513') || code.startsWith('518') || code.startsWith('511')) return true;
    }
    if (sym.startsWith('sz')) {
      const t0SzCodes = new Set(['159567', '159792', '159740', '159920', '159941', '159934', '159937', '159830', '159834', '159980', '159985', '159981']);
      if (t0SzCodes.has(code)) return true;
      if ((code.startsWith('1595') || code.startsWith('1597')) && ['港', '恒', '美', '海外', '科技'].some(w => nameStr.includes(w))) return true;
    }
    return false;
  }

  // 获取 30 分钟 K 线历史数据 (调用腾讯 mkline 接口，原生支持 CORS)
  async function get30MinKlines(symbol, limit = 320) {
    const fullSym = normalizeSymbol(symbol);
    const url = `https://ifzq.gtimg.cn/appstock/app/kline/mkline?param=${fullSym},m30,,${limit}`;
    try {
      const resp = await fetch(url);
      const data = await resp.json();
      if (data && data.data && data.data[fullSym]) {
        const stockData = data.data[fullSym];
        const rawBars = stockData.m30 || [];
        const name = (stockData.qt && stockData.qt[fullSym] && stockData.qt[fullSym][1]) ? stockData.qt[fullSym][1] : fullSym;

        let prevClose = null;
        const klines = [];
        for (let i = 0; i < rawBars.length; i++) {
          const item = rawBars[i];
          if (!item || item.length < 6) continue;
          const dtStr = String(item[0]);
          let dPart = dtStr;
          let tPart = "";
          let dtFmt = dtStr;
          if (dtStr.length >= 12) {
            dPart = `${dtStr.slice(0, 4)}-${dtStr.slice(4, 6)}-${dtStr.slice(6, 8)}`;
            tPart = `${dtStr.slice(8, 10)}:${dtStr.slice(10, 12)}`;
            dtFmt = `${dPart} ${tPart}`;
          } else if (dtStr.length >= 8) {
            dPart = `${dtStr.slice(0, 4)}-${dtStr.slice(4, 6)}-${dtStr.slice(6, 8)}`;
            dtFmt = dPart;
          }

          const open = parseFloat(item[1]);
          const close = parseFloat(item[2]);
          const high = parseFloat(item[3]);
          const low = parseFloat(item[4]);
          const volume = parseFloat(item[5]) * 100;
          const amount = item[7] ? parseFloat(item[7]) * 10000 : 0;

          let pct_change = 0.0;
          if (prevClose !== null && prevClose > 0) {
            pct_change = Math.round(((close - prevClose) / prevClose * 100) * 100) / 100;
          }
          prevClose = close;

          klines.push({
            date: dtFmt,
            day_date: dPart,
            time: tPart,
            datetime: dtFmt,
            open,
            close,
            high,
            low,
            volume,
            amount,
            pct_change
          });
        }

        // 注入所有量化技术指标与买卖信号 (标明 30分)
        addMovingAverages(klines);
        addEmas(klines);
        addBoll(klines);
        addVolumeMovingAverages(klines);
        addMacd(klines);
        addKdj(klines);
        addRsi(klines);
        addSignals(klines, '30分');

        return {
          symbol: fullSym,
          code: fullSym.slice(2),
          name: name,
          klines: klines
        };
      }
    } catch (e) {
      console.error("get30MinKlines error for " + fullSym, e);
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
  function addSignals(klines, tfLabel = '60分') {
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
      const prev2J = prev2Bar ? (prev2Bar.j || 50.0) : 50.0;
      const ma10 = bar.ma10;
      const volume = bar.volume || 0;

      const candleBody = Math.abs(bar.close - bar.open);
      const upperShadow = bar.high - Math.max(bar.open, bar.close);

      // ==========================================
      // 模式 A: 未持仓状态，寻找买入信号 (B1, B2, B3, B4)
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
        const isVolumeSurgeUp = isHighPosition && (bar.pct_change >= 3.0) && (volume >= 1.3 * volMa5);

        const cond3Base = condMa5Up && condMacdTrend && condMacdGoldClose && condKdjBull && (!isVolumeSurgeUp);

        // 分档辅助研判因子
        const isVol11 = volume >= 1.1 * volMa5;
        const isVol125 = volume >= 1.25 * volMa5;
        const isRedBar = (bar.pct_change > 0) || (bar.close >= bar.open);
        const isAboveMa5 = (ma5 !== null) && (bar.close >= ma5);
        const isAboveMa10 = (ma10 !== null) && (bar.close >= ma10);

        // 4档起爆/超跌催化剂
        const isDeepOversoldBounce = (prevJ < 15 || prev2J < 15 || prevK < 20) && (jVal >= prevJ + 5.0);
        const isBreakoutLaunch = isAboveMa10 && isVol125 && isRedBar;

        if (cond3Base) {
          let tier = 2;
          let st = "B2";
          let sname = `买入: ${tfLabel}2档半仓共振`;
          let spos = "半仓 50% 标准建仓";
          let sreason = `2档标准共振：MA5向上 + MACD动能修复 + KDJ多头，建议50%半仓稳健建仓`;

          if (isDeepOversoldBounce || isBreakoutLaunch) {
            tier = 4;
            st = "B4";
            sname = `买入: ${tfLabel}4档全仓共振`;
            spos = "全仓 100% 顶格建仓";
            const launchReason = isDeepOversoldBounce ? "深跌黄金坑强力拔起" : "放量突破站稳MA10";
            sreason = `4档全仓共振：三大指标金叉 + ${launchReason}，建议100%全仓出击`;
          } else if (isAboveMa5 && isRedBar) {
            tier = 3;
            st = "B3";
            sname = `买入: ${tfLabel}3档重仓共振`;
            spos = "重仓 75% 积极建仓";
            const volNote = isVol11 ? "温和放量" : "站稳均线";
            sreason = `3档重仓共振：三大指标金叉 + ${volNote}收红站上MA5，建议75%重仓建仓`;
          }

          bar.signal_type = st;
          bar.signal_name = sname;
          bar.signal_position = spos;
          bar.signal_reason = sreason;
          bar.buy_tier = tier;

          inPosition = true;
          s3Triggered = false;
          buyIndex = i;
          buyPrice = bar.close;
          buyHighest = bar.high;
          continue;
        } else {
          // 1档: 双指标初现企稳试错 (MA5止跌 + MACD动能修复，KDJ的J拐头向上)
          const cond2Base = condMa5Up && condMacdTrend && condMacdGoldClose && (!isVolumeSurgeUp) && (jVal > prevJ);
          if (cond2Base) {
            bar.signal_type = "B1";
            bar.signal_name = `买入: ${tfLabel}1档轻仓共振`;
            bar.signal_position = "轻仓 25% 试探建仓";
            bar.signal_reason = `1档试错共振：MA5走平止跌 + MACD动能修复，双指标企稳，防踏空轻仓25%试探`;
            bar.buy_tier = 1;

            inPosition = true;
            s3Triggered = false;
            buyIndex = i;
            buyPrice = bar.close;
            buyHighest = bar.high;
            continue;
          }
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

  // ==========================================
  // 自选观察池存储与增删管理
  // ==========================================
  function getWatchList() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_WATCHLIST);
      if (saved) {
        let parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          let changed = false;
          const beforeLen = parsed.length;
          parsed = parsed.filter(item => {
            const c = (typeof item === 'string' ? item : item?.code || item?.symbol || '');
            return !c.includes('512010');
          });
          if (parsed.length !== beforeLen) changed = true;

          parsed = parsed.map(item => {
            const c = (typeof item === 'string' ? item : item?.code || item?.symbol || '');
            if (c.includes('513330')) {
              changed = true;
              return typeof item === 'string' ? 'sz159792' : { ...item, sector: "港股互联网", code: "sz159792", desc: "港股通互联网ETF", trade_rule: "T+0", optimal_period: "30min" };
            }
            return item;
          });

          const has159915 = parsed.some(item => {
            const c = (typeof item === 'string' ? item : item?.code || item?.symbol || '');
            return c.includes('159915');
          });
          if (!has159915) {
            const default159915 = DEFAULT_SECTOR_ETFS.find(x => x.code === 'sz159915');
            if (default159915) {
              parsed.push(typeof parsed[0] === 'string' ? 'sz159915' : default159915);
              changed = true;
            }
          }
          if (changed) {
            saveWatchList(parsed);
          }
          return parsed;
        }
      }
    } catch (e) {}
    saveWatchList(DEFAULT_SECTOR_ETFS);
    return [...DEFAULT_SECTOR_ETFS];
  }

  function saveWatchList(list) {
    try {
      localStorage.setItem(STORAGE_KEY_WATCHLIST, JSON.stringify(list));
    } catch (e) {}
  }

  function addToWatchList(item) {
    if (!item) return false;
    const fullSym = normalizeSymbol(item.code || item.symbol || item);
    const list = getWatchList();
    const exists = list.some(x => normalizeSymbol(x.code || x.symbol) === fullSym);
    if (!exists) {
      const name = item.desc || item.name || item.sector || fullSym;
      const isT0 = isT0Symbol(fullSym, name);
      list.push({
        sector: item.sector || name || "自选标的",
        code: fullSym,
        symbol: fullSym,
        desc: name,
        trade_rule: isT0 ? "T+0" : "T+1",
        optimal_period: isT0 ? "m30" : "m60"
      });
      saveWatchList(list);
      return true;
    }
    return false;
  }

  function removeFromWatchList(symbol) {
    if (!symbol) return false;
    const fullSym = normalizeSymbol(symbol);
    const list = getWatchList();
    const filtered = list.filter(x => normalizeSymbol(x.code || x.symbol) !== fullSym);
    saveWatchList(filtered);
    return true;
  }

  function isInWatchList(symbol) {
    if (!symbol) return false;
    const fullSym = normalizeSymbol(symbol);
    const list = getWatchList();
    return list.some(x => normalizeSymbol(x.code || x.symbol) === fullSym);
  }

  function resetWatchListToDefault() {
    saveWatchList([...DEFAULT_SECTOR_ETFS]);
    return [...DEFAULT_SECTOR_ETFS];
  }

  // 获取观察池列表与分类状态
  async function getWatchPool() {
    const listToLoad = getWatchList();
    if (!listToLoad || listToLoad.length === 0) return [];

    // 并发拉取各标的的 K 线数据 (T+0 标的自动匹配 30分钟，T+1 标的自动匹配 60分钟)
    const promises = listToLoad.map(async (item) => {
      const code = item.code || item.symbol;
      const isT0 = isT0Symbol(code, item.desc || item.name);
      const tfLabel = isT0 ? "30分" : "60分";
      const checkBarsCount = isT0 ? 8 : 4;

      const data = isT0 ? await get30MinKlines(code, 320) : await get60MinKlines(code, 320);
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
          reason_summary: `等待更多 ${tfLabel} 交易数据确认`,
          trade_rule: isT0 ? "T+0" : "T+1",
          optimal_period: isT0 ? "m30" : "m60",
          latest_bar: null
        };
      }

      const bar = klines[klines.length - 1];
      const todayDate = bar.day_date || (bar.datetime ? bar.datetime.slice(0, 10) : "");
      const todayBars = klines.filter(k => (k.day_date === todayDate) || (k.datetime && k.datetime.startsWith(todayDate)));

      let todaySig = bar.signal_type;
      if (!todaySig && todayBars.length > 1) {
        for (let j = todayBars.length - 2; j >= 0; j--) {
          if (todayBars[j].signal_type) {
            todaySig = todayBars[j].signal_type;
            break;
          }
        }
      }

      let inPos = false;
      let hasS3Holding = false;
      let buyCostPrice = bar.close;
      let buyDate = "";

      for (let j = klines.length - 2; j >= 0; j--) {
        const sig = klines[j].signal_type;
        if (sig && (sig === "B" || sig.startsWith("B"))) {
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
      let reasonSummary = `${tfLabel}形态震荡蓄势，未触发共振买点`;

      if (todaySig && (todaySig === "B" || todaySig.startsWith("B"))) {
        let tier = 2;
        if (todaySig === "B4") tier = 4;
        else if (todaySig === "B3") tier = 3;
        else if (todaySig === "B2") tier = 2;
        else if (todaySig === "B1") tier = 1;

        if (tier === 4) {
          tag = `${tfLabel}4档买入`;
          tagColor = "#b91c1c"; // 深红/紫红高亮 (全仓100%)
          sortPriority = 110;
          reasonSummary = `${tfLabel}4档全仓共振确认(100%)，深跌反弹/突破加速`;
        } else if (tier === 3) {
          tag = `${tfLabel}3档买入`;
          tagColor = "#dc2626"; // 鲜艳大红 (重仓75%)
          sortPriority = 105;
          reasonSummary = `${tfLabel}3档重仓共振确认(75%)，放量站稳均线`;
        } else if (tier === 2) {
          tag = `${tfLabel}2档买入`;
          tagColor = "#ea580c"; // 橙红 (半仓50%)
          sortPriority = 100;
          reasonSummary = `${tfLabel}2档标准共振确认(50%)，三大指标金叉`;
        } else {
          tag = `${tfLabel}1档买入`;
          tagColor = "#2563eb"; // 稳健蓝 (轻仓25%)
          sortPriority = 98;
          reasonSummary = `${tfLabel}1档轻仓共振试错(25%)，双指标企稳防踏空`;
        }
        tagGroup = "买入";
      } else if (["S1", "S2", "S7", "S4"].includes(todaySig)) {
        tag = `${tfLabel}卖出`;
        tagColor = "#16a34a"; // 鲜艳大绿 (卖出专用)
        tagGroup = "卖出";
        sortPriority = 95;
        reasonSummary = `${tfLabel}触发分级止盈/止损卖点，建议平仓`;
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
          reasonSummary = `${tfLabel}多头趋势保持良好，继续持有观察`;
        }
      } else {
        // 评估是否“即将满足”
        const prev = klines.length > 1 ? klines[klines.length - 2] : null;
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
          reasonSummary = `${tfLabel}关键技术指标转多，密切留意共振`;
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
        trade_rule: isT0 ? "T+0" : "T+1",
        optimal_period: isT0 ? "m30" : "m60",
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

  return {
    normalizeSymbol,
    isT0Symbol,
    getRealtimeQuote,
    getDailyKlines,
    get30MinKlines,
    get60MinKlines,
    getWatchList,
    saveWatchList,
    addToWatchList,
    removeFromWatchList,
    isInWatchList,
    resetWatchListToDefault,
    getWatchPool,
    searchStock,
    calculateInterval,
    calculateIntervalByPreset,
    DEFAULT_SECTOR_ETFS,
    STORAGE_KEY_WATCHLIST,
    STORAGE_KEY_THEME
  };
})();

if (typeof window !== "undefined") {
  window.MobileQuantEngine = MobileQuantEngine;
}
