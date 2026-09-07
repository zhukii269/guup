import requests
import json
import re
import math
import os
import sys
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor


class StockDataProvider:
    def __init__(self):
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        self._watch_pool_cache = None
        self._watch_pool_cache_time = 0
        self._watch_pool_dict_cache = {}
        self._watch_pool_dict_cache_time = {}
        self._item_data_cache = {}

    def normalize_symbol(self, raw_symbol):
        s = str(raw_symbol).strip().lower()
        if re.match(r'^\d{6}$', s):
            if s.startswith(('6', '9', '688')):
                return f"sh{s}"
            elif s.startswith(('0', '3', '159', '12', '16', '399')):
                return f"sz{s}"
            elif s == "000001":
                return "sh000001"
            else:
                return f"sh{s}"
        if s.startswith(('sh', 'sz')):
            return s
        return "sh000001"

    def get_realtime_quote(self, symbol="sh000001"):
        symbol = self.normalize_symbol(symbol)
        url = f"https://hq.sinajs.cn/list={symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://finance.sina.com.cn/"
        }
        try:
            res = self.session.get(url, headers=headers, timeout=5)
            content = res.content.decode('gbk', errors='ignore')
            match = re.search(r'var hq_str_(\w+)="(.*)";', content)
            if match:
                parts = match.group(2).split(',')
                if len(parts) >= 31:
                    name = parts[0]
                    open_price = float(parts[1]) if parts[1] else 0.0
                    prev_close = float(parts[2]) if parts[2] else 0.0
                    current_price = float(parts[3]) if parts[3] else prev_close
                    high_price = float(parts[4]) if parts[4] else 0.0
                    low_price = float(parts[5]) if parts[5] else 0.0
                    volume = float(parts[8]) if parts[8] else 0.0
                    amount = float(parts[9]) if parts[9] else 0.0
                    date_str = parts[30]
                    time_str = parts[31] if len(parts) > 31 else ""

                    change = current_price - prev_close if prev_close > 0 else 0.0
                    pct_change = (change / prev_close * 100.0) if prev_close > 0 else 0.0

                    return {
                        "symbol": symbol,
                        "code": symbol[2:],
                        "name": name,
                        "current": current_price,
                        "prev_close": prev_close,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "change": round(change, 3),
                        "pct_change": round(pct_change, 2),
                        "volume": volume,
                        "amount": amount,
                        "date": date_str,
                        "time": time_str
                    }
        except Exception as e:
            print(f"Error fetching realtime quote for {symbol}: {e}")
        
        return {
            "symbol": symbol,
            "code": symbol[2:],
            "name": "未知股票/指数",
            "current": 0.0,
            "prev_close": 0.0,
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "change": 0.0,
            "pct_change": 0.0,
            "volume": 0.0,
            "amount": 0.0,
            "date": "",
            "time": ""
        }

    def get_daily_klines(self, symbol="sh000001", limit=600):
        symbol = self.normalize_symbol(symbol)
        urls = [
            f"https://ifzq.gtimg.cn/appstock/app/newfqkline/get?param={symbol},day,,,{limit},qfq",
            f"http://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get?param={symbol},day,,,{limit},qfq",
            f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{limit},qfq"
        ]
        data = {}
        for url in urls:
            try:
                res = self.session.get(url, timeout=5)
                if res.status_code == 200 and res.text.startswith('{'):
                    data = res.json()
                    if 'data' in data and symbol in data.get('data', {}):
                        break
            except Exception as e:
                print(f"URL {url} failed for {symbol}: {e}")

        try:
            stock_dict = data.get('data', {}).get(symbol, {})
            day_data = stock_dict.get('day', stock_dict.get('qfqday', []))
            
            raw_bars = []
            for bar in day_data:
                if len(bar) >= 6:
                    raw_bars.append({
                        "date": bar[0],
                        "open": float(bar[1]),
                        "close": float(bar[2]),
                        "high": float(bar[3]),
                        "low": float(bar[4]),
                        "volume": float(bar[5])
                    })
            
            klines = []
            for i, bar in enumerate(raw_bars):
                prev_close = raw_bars[i-1]["close"] if i > 0 else bar["open"]
                chg_val = round(bar["close"] - prev_close, 3)
                pct_val = round((chg_val / prev_close * 100.0) if prev_close > 0 else 0.0, 2)

                klines.append({
                    "date": bar["date"],
                    "open": bar["open"],
                    "close": bar["close"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "volume": bar["volume"],
                    "prev_close": prev_close,
                    "change": chg_val,
                    "pct_change": pct_val
                })
            
            self._add_moving_averages(klines)
            self._add_emas(klines)
            self._add_boll(klines)
            self._add_volume_moving_averages(klines)
            self._add_macd(klines)
            self._add_kdj(klines)
            self._add_rsi(klines)
            
            # Fetch 60m K-lines in background for Signal C & 60m top divergence
            m60_signals = self._fetch_m60_signals(symbol)
            self._add_signals(klines, m60_signals)
            
            name = stock_dict.get('qt', {}).get(symbol, ['', ''])[1] if 'qt' in stock_dict else ""
            if not name:
                rt = self.get_realtime_quote(symbol)
                name = rt.get('name', '')

            return {
                "symbol": symbol,
                "code": symbol[2:],
                "name": name,
                "klines": klines
            }
        except Exception as e:
            print(f"Error fetching daily klines for {symbol}: {e}")
            return {"symbol": symbol, "code": symbol[2:], "name": "", "klines": []}

    def _add_moving_averages(self, klines):
        closes = [k["close"] for k in klines]
        for i in range(len(klines)):
            for period in [5, 10, 20, 30, 60]:
                if i + 1 >= period:
                    ma_val = sum(closes[i + 1 - period : i + 1]) / period
                    klines[i][f"ma{period}"] = round(ma_val, 3)
                else:
                    klines[i][f"ma{period}"] = None

    def _add_emas(self, klines):
        closes = [k["close"] for k in klines]
        for period in [5, 13, 30]:
            multiplier = 2 / (period + 1)
            ema = 0.0
            for i, bar in enumerate(klines):
                c = closes[i]
                if i == 0:
                    ema = c
                else:
                    ema = (c - ema) * multiplier + ema
                bar[f"ema{period}"] = round(ema, 3)

    def _add_boll(self, klines, period=20, k=2):
        closes = [k["close"] for k in klines]
        for i, bar in enumerate(klines):
            if i + 1 < period:
                bar["boll_mid"] = None
                bar["boll_upper"] = None
                bar["boll_lower"] = None
                bar["boll_width"] = None
            else:
                sub = closes[i + 1 - period : i + 1]
                mid = sum(sub) / period
                variance = sum((x - mid) ** 2 for x in sub) / period
                std = math.sqrt(variance)
                upper = mid + k * std
                lower = mid - k * std
                width = (upper - lower) / mid if mid > 0 else 0
                bar["boll_mid"] = round(mid, 3)
                bar["boll_upper"] = round(upper, 3)
                bar["boll_lower"] = round(lower, 3)
                bar["boll_width"] = round(width, 4)

    def _add_volume_moving_averages(self, klines):
        volumes = [k["volume"] for k in klines]
        for i in range(len(klines)):
            for period in [5, 10]:
                if i + 1 >= period:
                    vol_ma_val = sum(volumes[i + 1 - period : i + 1]) / period
                    klines[i][f"vol_ma{period}"] = round(vol_ma_val, 0)
                else:
                    klines[i][f"vol_ma{period}"] = None

    def _add_macd(self, klines, short=12, long=26, mid=9):
        closes = [k["close"] for k in klines]
        ema_short = 0.0
        ema_long = 0.0
        dea = 0.0

        for i, k in enumerate(klines):
            close = closes[i]
            if i == 0:
                ema_short = close
                ema_long = close
                dif = 0.0
                dea = 0.0
            else:
                ema_short = ema_short * (short - 1) / (short + 1) + close * 2 / (short + 1)
                ema_long = ema_long * (long - 1) / (long + 1) + close * 2 / (long + 1)
                dif = ema_short - ema_long
                dea = dea * (mid - 1) / (mid + 1) + dif * 2 / (mid + 1)

            macd_bar = (dif - dea) * 2
            k["dif"] = round(dif, 3)
            k["dea"] = round(dea, 3)
            k["macd"] = round(macd_bar, 3)

    def _add_kdj(self, klines, n=9, m1=3, m2=3):
        k_val = 50.0
        d_val = 50.0

        for i, bar in enumerate(klines):
            start_idx = max(0, i - n + 1)
            period_highs = [k["high"] for k in klines[start_idx : i + 1]]
            period_lows = [k["low"] for k in klines[start_idx : i + 1]]
            
            hn = max(period_highs) if period_highs else bar["high"]
            ln = min(period_lows) if period_lows else bar["low"]
            
            if hn == ln:
                rsv = 50.0
            else:
                rsv = (bar["close"] - ln) / (hn - ln) * 100.0
            
            k_val = (m1 - 1) / m1 * k_val + 1 / m1 * rsv
            d_val = (m2 - 1) / m2 * d_val + 1 / m2 * k_val
            j_val = 3 * k_val - 2 * d_val

            bar["k"] = round(k_val, 3)
            bar["d"] = round(d_val, 3)
            bar["j"] = round(j_val, 3)

    def _add_rsi(self, klines, period=6):
        if not klines:
            return
        gains = []
        losses = []
        for i in range(len(klines)):
            if i == 0:
                klines[i]["rsi6"] = 50.0
                continue
            change = klines[i]["close"] - klines[i-1]["close"]
            gain = max(0.0, change)
            loss = max(0.0, -change)
            
            if i <= period:
                gains.append(gain)
                losses.append(loss)
                avg_gain = sum(gains) / len(gains)
                avg_loss = sum(losses) / len(losses)
            else:
                avg_gain = (gains[-1] * (period - 1) + gain) / period
                avg_loss = (losses[-1] * (period - 1) + loss) / period
                gains[-1] = avg_gain
                losses[-1] = avg_loss

            if avg_loss == 0:
                rsi_val = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_val = 100.0 - (100.0 / (1.0 + rs))
            klines[i]["rsi6"] = round(rsi_val, 2)

    def _fetch_m60_signals(self, symbol):
        """Fetch 60m K-lines in background to compute 60m MACD bottom/top divergence per date"""
        m60_signals = {}
        urls = [
            f"http://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get?param={symbol},m60,,,300,qfq",
            f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},m60,,,300,qfq"
        ]
        data = {}
        for url in urls:
            try:
                res = self.session.get(url, timeout=5)
                if res.status_code == 200 and res.text.startswith('{'):
                    data = res.json()
                    if 'data' in data and symbol in data.get('data', {}):
                        break
            except Exception as e:
                pass

        try:
            m60_data = data.get("data", {}).get(symbol, {}).get("m60", []) or data.get("data", {}).get(symbol, {}).get("qfqm60", [])
            if not m60_data:
                return m60_signals

            bars = []
            for item in m60_data:
                if len(item) >= 6:
                    datetime_str = item[0]
                    date_key = datetime_str.split()[0] if ' ' in datetime_str else datetime_str[:10]
                    if len(date_key) == 8 and '-' not in date_key:
                        date_key = f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:]}"
                    bars.append({
                        "date": date_key,
                        "close": float(item[2]),
                        "high": float(item[3]),
                        "low": float(item[4]),
                        "volume": float(item[5])
                    })

            if len(bars) < 20:
                return m60_signals

            # Calculate 60m EMA5, EMA13, MACD
            ema5 = 0.0
            ema13 = 0.0
            ema12 = 0.0
            ema26 = 0.0
            dea = 0.0

            for i, b in enumerate(bars):
                c = b["close"]
                if i == 0:
                    ema5 = c; ema13 = c; ema12 = c; ema26 = c; dea = 0.0
                    b["dif"] = 0.0; b["dea"] = 0.0; b["macd"] = 0.0
                else:
                    ema5 = (c - ema5) * (2/6) + ema5
                    ema13 = (c - ema13) * (2/14) + ema13
                    ema12 = (c - ema12) * (2/13) + ema12
                    ema26 = (c - ema26) * (2/27) + ema26
                    dif = ema12 - ema26
                    dea = dea * (8/10) + dif * (2/10)
                    b["dif"] = dif
                    b["dea"] = dea
                    b["macd"] = (dif - dea) * 2

                b["ema5"] = ema5
                b["ema13"] = ema13

            # Detect 60m divergence by date
            for i in range(15, len(bars)):
                b = bars[i]
                d_key = b["date"]

                # 60m Bottom Divergence: price new low in last 15 bars, but dif > min_dif in last 15 bars
                sub = bars[i-15 : i+1]
                min_price_idx = min(range(len(sub)), key=lambda idx: sub[idx]["low"])
                min_dif_idx = min(range(len(sub)), key=lambda idx: sub[idx]["dif"])

                if min_price_idx == len(sub) - 1 and min_dif_idx != len(sub) - 1 and b["close"] > b["ema5"] and b["close"] > b["ema13"]:
                    m60_signals[d_key] = m60_signals.get(d_key, {})
                    m60_signals[d_key]["bottom_divergence"] = True

                # 60m Top Divergence: price new high, but dif not new high
                max_price_idx = max(range(len(sub)), key=lambda idx: sub[idx]["high"])
                max_dif_idx = max(range(len(sub)), key=lambda idx: sub[idx]["dif"])
                if max_price_idx == len(sub) - 1 and max_dif_idx != len(sub) - 1:
                    m60_signals[d_key] = m60_signals.get(d_key, {})
                    m60_signals[d_key]["top_divergence"] = True

        except Exception as e:
            print(f"Error fetching 60m signals: {e}")

        return m60_signals

    def _add_signals(self, klines, m60_signals=None):
        if not klines or len(klines) < 30:
            return

        in_position = False
        buy_index = -1
        buy_price = 0.0
        buy_highest = 0.0
        s3_triggered = False

        for i in range(len(klines)):
            bar = klines[i]
            bar["signal_type"] = None
            bar["signal_name"] = None
            bar["signal_reason"] = None
            bar["signal_position"] = None

            if i < 20:
                continue

            prev_bar = klines[i-1]
            prev2_bar = klines[i-2]
            prev3_bar = klines[i-3]

            ma5 = bar.get("ma5")
            prev_ma5 = prev_bar.get("ma5")

            vol_ma5 = bar.get("vol_ma5") or bar["volume"]

            dif = bar.get("dif", 0)
            dea = bar.get("dea", 0)
            prev_dif = prev_bar.get("dif", 0)
            prev_dea = prev_bar.get("dea", 0)

            macd_bar = bar.get("macd", 0)
            prev_macd = prev_bar.get("macd", 0)
            prev2_macd = prev2_bar.get("macd", 0)
            prev3_macd = prev3_bar.get("macd", 0)

            k_val = bar.get("k", 50.0)
            d_val = bar.get("d", 50.0)
            j_val = bar.get("j", 50.0)
            prev_k = prev_bar.get("k", 50.0)
            prev_d = prev_bar.get("d", 50.0)
            prev_j = prev_bar.get("j", 50.0)

            # K线形态分析
            candle_body = abs(bar["close"] - bar["open"])
            upper_shadow = bar["high"] - max(bar["open"], bar["close"])

            # ----------------------------------------------------
            # ----------------------------------------------------
            # 模式 A: 未持仓状态，寻找【买入信号 (B)】
            # ----------------------------------------------------
            if not in_position:
                # 1. 5日线止跌 (MA5 >= 前一日 MA5)
                cond_ma5_up = (ma5 is not None) and (prev_ma5 is not None) and (ma5 >= prev_ma5 - 1e-5)

                # 2. MACD动能验证 (绿柱连续2日缩短 或 红柱连续2日放大 / 刚转红柱)
                cond_macd_green_shrink = (macd_bar <= 0) and (prev_macd <= 0) and (abs(macd_bar) < abs(prev_macd)) and (abs(prev_macd) <= abs(prev2_macd))
                cond_macd_red_expand = (macd_bar >= 0) and ((prev_macd <= 0 or prev2_macd <= 0) or (prev2_macd >= 0 and macd_bar > prev_macd and prev_macd >= prev2_macd))
                cond_macd_trend = cond_macd_green_shrink or cond_macd_red_expand

                # 3. MACD金叉附近判定 (二选一) + 通用约束 (DIF主动上行 dif > prev_dif)
                universal_dif_up = (dif > prev_dif)

                # 场景 A（绿柱末期・金叉前左侧）：绿柱绝对值 <= 本轮峰值的 35%
                scenario_a = False
                if macd_bar <= 0:
                    green_wave_peak = 0.0
                    j = i
                    while j >= 0 and klines[j]["macd"] <= 0:
                        green_wave_peak = max(green_wave_peak, abs(klines[j]["macd"]))
                        j -= 1
                    if green_wave_peak > 0:
                        scenario_a = abs(macd_bar) <= 0.35 * green_wave_peak

                # 场景 B（红柱初期・金叉后右侧）：MACD正式金叉后的前 2 根红柱 (prev_macd <= 0 或 prev2_macd <= 0)
                scenario_b = (macd_bar >= 0) and (prev_macd <= 0 or prev2_macd <= 0)

                cond_macd_gold_close = (scenario_a or scenario_b) and universal_dif_up

                # 4. KDJ多头结构 (K > D)
                cond_kdj_bull = k_val > d_val

                # 5. 放量大涨过滤：严格看位置！
                # 长期下跌/中长期回调后的放量大涨是好事(底部放量长阳突破)，大幅上涨之后的放量大涨才是坏事(高位脉冲诱多追高)
                start_60 = max(0, i - 60 + 1)
                highest_60 = max(b["high"] for b in klines[start_60:i+1])
                lowest_60 = min(b["low"] for b in klines[start_60:i+1])
                range_60 = max(0.001, highest_60 - lowest_60)
                pos_ratio_60 = (bar["close"] - lowest_60) / range_60

                start_15 = max(0, i - 15 + 1)
                lowest_15 = min(b["low"] for b in klines[start_15:i+1])
                gain_from_recent_low = (bar["close"] - lowest_15) / lowest_15 if lowest_15 > 0 else 0

                # 仅当处于大幅上涨之后(60日相对高位 pos_ratio_60 >= 0.65 或 近期已累计大涨 gain_from_recent_low >= 0.15)时，放量大涨才属于脉冲追高
                is_high_position = (pos_ratio_60 >= 0.65) or (gain_from_recent_low >= 0.15)
                is_volume_surge_up = is_high_position and (bar["pct_change"] >= 3.0) and (bar["volume"] >= 1.3 * vol_ma5)

                # 全部同时满足方可开仓 (严格秉承“低吸买点、位置甄别”原则)
                if cond_ma5_up and cond_macd_trend and cond_macd_gold_close and cond_kdj_bull and (not is_volume_surge_up):
                    bar["signal_type"] = "B"
                    bar["signal_name"] = "买入: 5日线+MACD+KDJ共振"
                    bar["signal_position"] = "标准建仓 / 试错开仓"
                    reason_extra = "底部放量突破确认" if ((bar["pct_change"] >= 3.0) and (bar["volume"] >= 1.3 * vol_ma5)) else "满足共振条件"
                    bar["signal_reason"] = f"MA5止跌({ma5:.3f})，MACD金叉附近(场景A/B+DIF主动上行)，KDJ多头(K>D)，{reason_extra}"
                    
                    in_position = True
                    s3_triggered = False
                    buy_index = i
                    buy_price = bar["close"]
                    buy_highest = bar["high"]
                    continue

            # ----------------------------------------------------
            # 模式 B: 持仓状态，评估【卖出条件 (止盈 / 止损)】
            # ----------------------------------------------------
            else:
                holding_days = i - buy_index
                profit_pct = (bar["close"] - buy_price) / buy_price if buy_price > 0 else 0
                buy_highest = max(buy_highest, bar["high"])

                # --- (0) 放量大涨(>=5%)且上影线占全天振幅>=10%冲高离场 (最高优先级止盈) ---
                is_volume_surge_up_s7 = (bar["pct_change"] >= 5.0) and (bar["volume"] >= 1.3 * vol_ma5)
                day_range = max(0.001, bar["high"] - bar["low"])
                shadow_ratio = upper_shadow / day_range
                
                if is_volume_surge_up_s7 and (shadow_ratio >= 0.10):
                    bar["signal_type"] = "S7"
                    bar["signal_name"] = "止盈: 放量大涨带上影"
                    bar["signal_position"] = "止盈清仓 / 锁定利润"
                    vol_ratio = bar["volume"] / vol_ma5 if vol_ma5 else 1.0
                    bar["signal_reason"] = f"持仓期间放量大涨(+{bar['pct_change']:.2f}% >=5%)且上影线占振幅{shadow_ratio*100:.0f}%(>=10%)，冲高锁定利润"
                    in_position = False
                    s3_triggered = False
                    continue

                # S4: 指标止损 (MACD绿柱重新放大>0.001 OR 破位10日线且MA5下拐)
                cond_macd_re_expand = (macd_bar < 0) and (prev_macd < 0) and (abs(macd_bar) - abs(prev_macd) > 0.001)

                # 优化均线离场逻辑：改为跌破10日线(MA10)防守，过滤5日线附近微弱震荡，且在 MACD 红柱扩张(多头)时保护不卖出
                ma10 = bar.get("ma10", ma5)
                ma5_drop_ratio = (prev_ma5 - ma5) / prev_ma5 if (ma5 and prev_ma5 and prev_ma5 > 0) else 0
                macd_bull_expanding = (macd_bar > 0) and (macd_bar >= prev_macd)
                ma_break_down = (ma10 is not None) and (bar["close"] < ma10)
                ma5_significant_down = (ma5_drop_ratio >= 0.005 and ma_break_down) or (ma5 < prev_ma5 * 0.995 and ma_break_down)
                cond_ma_turn_down = (ma5 is not None) and (prev_ma5 is not None) and ma5_significant_down and (not macd_bull_expanding)

                if cond_macd_re_expand or cond_ma_turn_down:
                    bar["signal_type"] = "S4"
                    bar["signal_name"] = "止损: 指标走坏"
                    bar["signal_position"] = "100% 严格止损"
                    reason_detail = "MACD绿柱重新放大(>0.001)" if cond_macd_re_expand else "破位10日线且MA5下拐"
                    bar["signal_reason"] = f"触发指标止损({reason_detail})，必须严格离场防范套牢"
                    in_position = False
                    s3_triggered = False
                    continue


                # --- (一) S1 止盈升级规则 (DIF 0轴上线下分级策略) ---
                recent_3d_js = [klines[j].get("j", 50.0) for j in range(max(0, i-3), i+1)]
                kdj_exact_death = (prev_k >= prev_d) and (k_val < d_val)
                kdj_near_death = (j_val < prev_j) and (k_val >= d_val) and (k_val - d_val <= 2.5) and (k_val - d_val <= 0.45 * (prev_k - prev_d))
                kdj_death_or_near = kdj_exact_death or kdj_near_death
                d_filter_passed = d_val >= 50

                s1_triggered = False
                s1_reason = ""

                # 场景 1: DIF < 0 (0轴下方，弱势反弹)：J >= 80 后死叉 / 预判死叉，快速落袋
                if dif < 0:
                    has_j_overbought = any(j >= 80 for j in recent_3d_js)
                    if has_j_overbought and kdj_death_or_near and d_filter_passed:
                        s1_triggered = True
                        detail = "正式死叉" if kdj_exact_death else f"预判死叉(间距仅{k_val-d_val:.2f})"
                        s1_reason = f"0轴下方弱势反弹，J值高位(>80)回落，KDJ({detail})，快速落袋为安"
                # 场景 2: DIF >= 0 (0轴上方，强势行情)：三种高级触发机制
                else:
                    # ① J值突破100极端超买后KDJ正式死叉 (必须 K < D，防止多头趋势中因预判死叉提前卖飞)
                    has_j_extreme = any(j >= 100 for j in recent_3d_js)
                    cond_j100_death = has_j_extreme and kdj_exact_death and d_filter_passed
                    
                    # ② 核心触发：MACD红柱连续3个交易日逐根缩短 (替代原KDJ假死叉)
                    cond_red_shrink_3d = (macd_bar > 0) and (prev_macd > 0) and (prev2_macd > 0) and (prev3_macd > 0) and (macd_bar < prev_macd) and (prev_macd < prev2_macd) and (prev2_macd < prev3_macd)

                    # ③ 最终兜底：MACD正式死叉 (DIF下穿DEA，且柱子由红变绿)
                    cond_macd_death = (prev_macd > 0) and (macd_bar <= 0) and (prev_dif >= prev_dea) and (dif < dea)

                    if cond_j100_death:
                        s1_triggered = True
                        s1_reason = "0轴上方强势行情，J值冲破100极端超买后KDJ正式死叉(K<D)，高位锁定利润"
                    elif cond_red_shrink_3d:
                        s1_triggered = True
                        s1_reason = "0轴上方强势行情，MACD红柱连续3日逐根缩短，提前锁定利润"
                    elif cond_macd_death:
                        s1_triggered = True
                        s1_reason = "0轴上方强势行情，MACD正式死叉(DIF下穿DEA)，兜底无条件清仓"

                if s1_triggered:
                    bar["signal_type"] = "S1"
                    bar["signal_name"] = "止盈: 强势/弱势分级止盈"
                    bar["signal_position"] = "止盈清仓 / 锁定利润"
                    bar["signal_reason"] = s1_reason
                    in_position = False
                    s3_triggered = False
                    continue

                # S2: 放量长上影线 (量能>=1.5倍MAVOL5, 上影线>=2倍实体, 出现于高位)
                volume_burst = bar["volume"] >= 1.5 * vol_ma5
                long_upper = upper_shadow >= 2.0 * max(0.001, candle_body)
                recent_up = (prev_bar["pct_change"] > 0 and prev2_bar["pct_change"] > 0) or (profit_pct >= 0.03)
                if volume_burst and long_upper and recent_up:
                    bar["signal_type"] = "S2"
                    bar["signal_name"] = "止盈: 放量长上影线"
                    bar["signal_position"] = "减仓 / 锁定利润"
                    bar["signal_reason"] = f"高位放量({bar['volume']/vol_ma5:.1f}倍均量)收长上影线(影长{upper_shadow:.3f})，主力抛压强烈"
                    in_position = False
                    s3_triggered = False
                    continue

                # S3: 目标止盈 (盈利>=5% 仅触发一次，减仓50%，保留50%底仓等待后续卖点)
                if profit_pct >= 0.05 and (not s3_triggered):
                    bar["signal_type"] = "S3"
                    bar["signal_name"] = "止盈: 目标落袋50%"
                    bar["signal_position"] = "减仓50% / 保留50%底仓"
                    bar["signal_reason"] = f"持仓盈利达到 {profit_pct*100:.2f}%，首次触及5%目标止盈点，减仓50%锁定利润，保留50%底仓等待后续信号"
                    s3_triggered = True
                    continue


    def search_stock(self, keyword):
        if not keyword:
            return []
        url = f"https://smartbox.gtimg.cn/s3/?t=all&q={keyword}"
        try:
            res = self.session.get(url, timeout=5)
            text = res.text
            match = re.search(r'v_hint="(.*)"', text)
            results = []
            if match:
                items = match.group(1).split('^')
                for item in items:
                    parts = item.split('~')
                    if len(parts) >= 3:
                        mkt = parts[0]
                        code = parts[1]
                        name = parts[2]
                        try:
                            name = name.encode('utf-8').decode('unicode_escape')
                        except Exception:
                            pass
                        full_symbol = f"{mkt}{code}"
                        results.append({
                            "symbol": full_symbol,
                            "code": code,
                            "name": name,
                            "market": mkt.upper()
                        })
            return results[:8]
        except Exception as e:
            print(f"Error searching stock {keyword}: {e}")
            return []

    def get_watch_pool(self, custom_list=None):
        """
        获取主流板块 (A股+港股) 精选观察池
        """
        if custom_list and isinstance(custom_list, list) and len(custom_list) > 0:
            sector_etfs = []
            for item in custom_list:
                if isinstance(item, dict):
                    sector_etfs.append({
                        "sector": item.get("sector", "自选板块"),
                        "code": item.get("code", item.get("symbol", "")),
                        "desc": item.get("desc", item.get("name", "自选股"))
                    })
                elif isinstance(item, str):
                    sector_etfs.append({
                        "sector": "自选板块",
                        "code": item,
                        "desc": item
                    })
        else:
            sector_etfs = [
                {"sector": "金融科技", "code": "sz159851", "desc": "金融科技ETF"},
                {"sector": "人工智能", "code": "sz159819", "desc": "人工智能ETF"},
                {"sector": "半导体芯片", "code": "sz159995", "desc": "芯片ETF"},
                {"sector": "半导体设备", "code": "sz159516", "desc": "半导体设备ETF"},
                {"sector": "通信技术", "code": "sh515880", "desc": "通信ETF"},
                {"sector": "消费电子", "code": "sz159997", "desc": "电子ETF"},
                {"sector": "动漫游戏", "code": "sz159869", "desc": "游戏ETF"},
                {"sector": "计算机软件", "code": "sh512720", "desc": "计算机ETF"},
                {"sector": "新能源车", "code": "sh515030", "desc": "新能源车ETF"},
                {"sector": "光伏新能源", "code": "sh515790", "desc": "光伏ETF"},
                {"sector": "医药生物", "code": "sh512010", "desc": "医药ETF"},
                {"sector": "A股创新药", "code": "sz159992", "desc": "创新药ETF"},
                {"sector": "港股创新药", "code": "sz159567", "desc": "港股创新药ETF"},
                {"sector": "恒生医疗", "code": "sh513060", "desc": "恒生医疗ETF"},
                {"sector": "恒生互联网", "code": "sh513330", "desc": "恒生互联网ETF"},
                {"sector": "大金融证券", "code": "sh512880", "desc": "证券ETF"},
                {"sector": "国防军工", "code": "sh512660", "desc": "军工ETF"},
                {"sector": "人形机器人", "code": "sh562500", "desc": "机器人ETF"},
                {"sector": "有色金属", "code": "sh512400", "desc": "有色金属ETF"},
                {"sector": "煤炭周期", "code": "sh515220", "desc": "煤炭ETF"},
                {"sector": "电力绿电", "code": "sz159611", "desc": "电力ETF"},
                {"sector": "红利低波", "code": "sh515180", "desc": "红利ETF"}
            ]

        cache_key = tuple(sorted([x.get("code", "") for x in sector_etfs]))
        now_ts = time.time()
        if hasattr(self, "_watch_pool_dict_cache") and cache_key in self._watch_pool_dict_cache:
            last_ts = self._watch_pool_dict_cache_time.get(cache_key, 0)
            if now_ts - last_ts < 12.0:
                return self._watch_pool_dict_cache[cache_key]

        def _process_item(item):
            code = item["code"]
            try:
                data = self.get_daily_klines(code)
                klines = data.get("klines", [])
                
                # 若初次拉取无数据，自动重试一次防抖
                if not klines:
                    time.sleep(0.15)
                    data = self.get_daily_klines(code)
                    klines = data.get("klines", [])

                if not klines:
                    # 优先使用个股内存缓存
                    if hasattr(self, "_item_data_cache") and code in self._item_data_cache:
                        return self._item_data_cache[code]
                    # 终极兜底：严禁静默丢弃标的，返回安全占位标的
                    return {
                        "sector": item.get("sector", "自选板块"),
                        "name": item.get("desc", code),
                        "code": code,
                        "symbol": code,
                        "close": 1.0,
                        "price": 1.0,
                        "open": 1.0,
                        "high": 1.0,
                        "low": 1.0,
                        "prev_close": 1.0,
                        "change": 0.0,
                        "pct_change": 0.0,
                        "score": 0,
                        "tag": "行情同步中",
                        "tag_color": "#94a3b8",
                        "buy_cost_price": 1.0,
                        "buy_date": "",
                        "sort_priority": 10,
                        "is_triggered": False,
                        "reason_summary": "正在连接网络更新行情..."
                    }
                
                bar = klines[-1]
                prev = klines[-2] if len(klines) > 1 else bar
                prev2 = klines[-3] if len(klines) > 2 else prev
                prev3 = klines[-4] if len(klines) > 3 else prev2

                ma5 = bar.get("ma5")
                prev_ma5 = prev.get("ma5")
                
                # 评估 5 项 B1 条件
                c1 = (ma5 is not None) and (prev_ma5 is not None) and (ma5 >= prev_ma5 - 1e-5)
                
                mb = bar.get("macd", 0)
                pmb = prev.get("macd", 0)
                p2mb = prev2.get("macd", 0)
                p3mb = prev3.get("macd", 0)
                c2 = (mb <= 0 and pmb <= 0 and abs(mb) < abs(pmb) and abs(pmb) <= abs(p2mb)) or (mb >= 0 and (pmb <= 0 or p2mb <= 0 or (p2mb >= 0 and mb > pmb and pmb >= p2mb)))

                universal_dif_up = (bar.get("dif", 0) > prev.get("dif", 0))

                # 场景 A（绿柱末期・金叉前左侧）
                scenario_a = False
                if mb <= 0:
                    green_wave_peak = 0.0
                    j = len(klines) - 1
                    while j >= 0 and klines[j]["macd"] <= 0:
                        green_wave_peak = max(green_wave_peak, abs(klines[j]["macd"]))
                        j -= 1
                    if green_wave_peak > 0:
                        scenario_a = abs(mb) <= 0.35 * green_wave_peak

                # 场景 B（红柱初期・金叉后右侧）：前 2 根红柱
                scenario_b = (mb >= 0) and (pmb <= 0 or p2mb <= 0)

                c3 = (scenario_a or scenario_b) and universal_dif_up

                c4 = bar.get("k", 0) > bar.get("d", 0)

                score = sum([c1, c2, c3, c4])

                today_sig = bar.get("signal_type")

                # 评估股票当前是否处于持仓状态 (S3减仓50%后依然保持持仓，唯有S1/S2/S4/S7完全清仓)
                in_pos = False
                has_s3_holding = False
                buy_cost_price = bar["close"]
                buy_date = ""

                for k in reversed(klines[:-1]):
                    sig = k.get("signal_type")
                    if sig in ["B", "B1"]:
                        in_pos = True
                        buy_cost_price = k.get("close", bar["close"])
                        buy_date = k.get("date", "")
                        break
                    elif sig in ["S1", "S2", "S4", "S7"]:
                        in_pos = False
                        break
                    elif sig == "S3":
                        in_pos = True
                        has_s3_holding = True
                        buy_cost_price = k.get("close", bar["close"])
                        buy_date = k.get("date", "")
                        break

                sort_priority = 10

                # 优先判定【今日 (最新交易日)】是否刚触发买卖/减仓信号
                if today_sig in ["B", "B1"]:
                    tag = "尾盘买入"
                    tag_color = "#dc2626"  # 鲜艳大红高亮 (买点专用)
                    reason_summary = "日K多指标共振确认，统一尾盘(14:30~14:50)建仓"
                    sort_priority = 100
                    buy_cost_price = bar["close"]  # 统一为尾盘收盘价建仓，取消早盘开盘价
                    buy_date = bar.get("date", "")

                elif today_sig in ["S1", "S2", "S7", "S4"]:
                    tag = "今天卖出"
                    tag_color = "#16a34a"  # 鲜艳大绿高亮 (卖点专用)
                    reason_summary = "触发分级止盈/止损卖点，建议平仓"
                    sort_priority = 95
                elif today_sig == "S3":
                    tag = "今天卖出"
                    tag_color = "#16a34a"
                    reason_summary = "盈利触及5%，止盈减仓50%"
                    sort_priority = 90
                elif in_pos:
                    if has_s3_holding:
                        tag = "持仓(50%底仓)"
                        tag_color = "#f97316"  # 橙色
                        reason_summary = "盈利已锁定50%，留50%底仓观察"
                        sort_priority = 80
                    else:
                        tag = "观望持仓"
                        tag_color = "#ea580c"  # 红橙色 (已持仓多头状态)
                        reason_summary = "持仓观望中，等待后续卖点"
                        sort_priority = 70
                elif score >= 3:
                    tag = "即将满足"
                    tag_color = "#f97316"  # 醒目橙色
                    sub_reasons = []
                    if c1: sub_reasons.append("MA5向上")
                    if mb > 0 and mb > pmb: sub_reasons.append("红柱延伸")
                    elif mb < 0 and abs(mb) < abs(pmb): sub_reasons.append("绿柱缩短")
                    if scenario_b: sub_reasons.append("红柱初期")
                    elif scenario_a: sub_reasons.append("绿柱末期")
                    if c4: sub_reasons.append("KDJ多头")
                    reason_summary = " · ".join(sub_reasons[:2]) if sub_reasons else "多指标拐头向好"
                    sort_priority = 50
                else:
                    tag = "蓄势回调"
                    tag_color = "#94a3b8"  # 浅灰
                    reason_summary = "探底寻支撑，密切观察"
                    sort_priority = 10

                res_dict = {
                    "sector": item["sector"],
                    "name": data.get("name", item["desc"]),
                    "code": item["code"],
                    "symbol": data.get("symbol", item["code"]),
                    "close": bar["close"],
                    "price": bar["close"],
                    "open": bar.get("open", bar["close"]),
                    "high": bar.get("high", bar["close"]),
                    "low": bar.get("low", bar["close"]),
                    "prev_close": bar.get("prev_close", bar["close"]),
                    "change": bar.get("change", 0.0),
                    "pct_change": bar["pct_change"],
                    "score": score,
                    "tag": tag,
                    "tag_color": tag_color,
                    "buy_cost_price": round(buy_cost_price, 3),
                    "buy_date": buy_date,
                    "sort_priority": sort_priority,
                    "is_triggered": (sort_priority >= 70),
                    "reason_summary": reason_summary
                }
                if not hasattr(self, "_item_data_cache"):
                    self._item_data_cache = {}
                self._item_data_cache[code] = res_dict
                return res_dict
            except Exception as e:
                print(f"Error scanning watch pool for {item['code']}: {e}")
                if hasattr(self, "_item_data_cache") and code in self._item_data_cache:
                    return self._item_data_cache[code]
                return {
                    "sector": item.get("sector", "自选板块"),
                    "name": item.get("desc", code),
                    "code": code,
                    "symbol": code,
                    "close": 1.0,
                    "price": 1.0,
                    "open": 1.0,
                    "high": 1.0,
                    "low": 1.0,
                    "prev_close": 1.0,
                    "change": 0.0,
                    "pct_change": 0.0,
                    "score": 0,
                    "tag": "蓄势观察",
                    "tag_color": "#94a3b8",
                    "buy_cost_price": 1.0,
                    "buy_date": "",
                    "sort_priority": 10,
                    "is_triggered": False,
                    "reason_summary": "行情网络波动，保留标的观察"
                }

        with ThreadPoolExecutor(max_workers=8) as executor:
            raw_results = list(executor.map(_process_item, sector_etfs))

        pool = [x for x in raw_results if x is not None]

        # 排序：今日买点/卖点最高优先级置顶，持仓中紧随其后，按分数降序
        pool.sort(key=lambda x: (x["sort_priority"], x["score"]), reverse=True)

        if not hasattr(self, "_watch_pool_dict_cache"):
            self._watch_pool_dict_cache = {}
            self._watch_pool_dict_cache_time = {}
        self._watch_pool_dict_cache[cache_key] = pool
        self._watch_pool_dict_cache_time[cache_key] = time.time()
        self._watch_pool_cache = pool
        self._watch_pool_cache_time = time.time()

        return pool

    def get_minute_data(self, symbol="sh000001"):
        symbol = self.normalize_symbol(symbol)
        url = f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://finance.qq.com/"
        }
        try:
            res = self.session.get(url, headers=headers, timeout=5)
            data = res.json()
            if "data" in data and symbol in data["data"]:
                stock_dict = data["data"][symbol]
                raw_minutes = stock_dict.get("data", {}).get("data", [])
                
                prev_close = 0.0
                if "qt" in stock_dict and symbol in stock_dict["qt"] and len(stock_dict["qt"][symbol]) > 4:
                    try:
                        prev_close = float(stock_dict["qt"][symbol][4])
                    except:
                        pass
                
                parsed_minutes = []
                prev_cum_vol = 0.0
                prev_cum_amt = 0.0
                
                is_index = symbol.startswith("sh000") or symbol.startswith("sz399")
                sum_p = 0.0
                count_p = 0
                
                for line in raw_minutes:
                    parts = line.strip().split(" ")
                    if len(parts) >= 4:
                        time_str = parts[0]
                        formatted_time = f"{time_str[:2]}:{time_str[2:]}" if len(time_str) == 4 else time_str
                        price = float(parts[1])
                        cum_vol = float(parts[2])
                        cum_amt = float(parts[3])
                        
                        vol = cum_vol - prev_cum_vol
                        amt = cum_amt - prev_cum_amt
                        if vol < 0: vol = cum_vol
                        if amt < 0: amt = cum_amt
                        
                        prev_cum_vol = cum_vol
                        prev_cum_amt = cum_amt
                        
                        sum_p += price
                        count_p += 1
                        if is_index:
                            vwap = round(sum_p / count_p, 3)
                        else:
                            vwap = round(cum_amt / (cum_vol * 100), 3) if cum_vol > 0 else price
                            
                        pct_change = round(((price - prev_close) / prev_close * 100.0), 2) if prev_close > 0 else 0.0
                        
                        parsed_minutes.append({
                            "time": formatted_time,
                            "price": price,
                            "vol": vol,
                            "amt": amt,
                            "cum_vol": cum_vol,
                            "cum_amt": cum_amt,
                            "vwap": vwap,
                            "pct_change": pct_change
                        })
                
                return {
                    "symbol": symbol,
                    "date": stock_dict.get("data", {}).get("date", ""),
                    "prev_close": prev_close,
                    "minutes": parsed_minutes
                }
        except Exception as e:
            print(f"Error fetching minute data for {symbol}: {e}")
            
        return {
            "symbol": symbol,
            "date": "",
            "prev_close": 0.0,
            "minutes": []
        }

    def get_5min_klines(self, symbol="sh000001"):
        symbol = self.normalize_symbol(symbol)
        urls = [
            f"https://ifzq.gtimg.cn/appstock/app/kline/mkline?param={symbol},m5,,320",
            f"https://web.ifzq.gtimg.cn/appstock/app/kline/mkline?param={symbol},m5,,320"
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://finance.qq.com/"
        }
        data = None
        for url in urls:
            try:
                res = self.session.get(url, headers=headers, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    if "data" in data and symbol in data["data"]:
                        break
            except Exception:
                pass

        if not data or "data" not in data or symbol not in data["data"]:
            return {"symbol": symbol, "klines": []}

        stock_dict = data["data"][symbol]
        m5_raw = stock_dict.get("m5", [])
        if not m5_raw:
            return {"symbol": symbol, "klines": []}

        bars = []
        for row in m5_raw:
            dt_str = str(row[0])
            fmt_dt = f"{dt_str[:4]}-{dt_str[4:6]}-{dt_str[6:8]} {dt_str[8:10]}:{dt_str[10:12]}" if len(dt_str) >= 12 else dt_str
            time_part = f"{dt_str[8:10]}:{dt_str[10:12]}" if len(dt_str) >= 12 else dt_str
            date_part = f"{dt_str[:4]}-{dt_str[4:6]}-{dt_str[6:8]}" if len(dt_str) >= 8 else dt_str
            try:
                o = float(row[1])
                c = float(row[2])
                h = float(row[3])
                l = float(row[4])
                v = float(row[5])
            except Exception:
                continue

            bars.append({
                "datetime": fmt_dt,
                "date": date_part,
                "time": time_part,
                "open": o,
                "close": c,
                "high": h,
                "low": l,
                "volume": v,
                "signal_type": None,
                "signal_name": None,
                "signal_reason": None,
                "signal_position": None
            })

        if not bars:
            return {"symbol": symbol, "klines": []}

        for i, bar in enumerate(bars):
            prev_c = bars[i-1]["close"] if i > 0 else bar["open"]
            bar["prev_close"] = prev_c
            bar["change"] = round(bar["close"] - prev_c, 4)
            bar["pct_change"] = round((bar["change"] / prev_c * 100.0) if prev_c > 0 else 0.0, 2)

        # Calculate MAs
        for i, bar in enumerate(bars):
            for period, k in [(5, "ma5"), (10, "ma10"), (20, "ma20"), (30, "ma30")]:
                if i + 1 >= period:
                    bar[k] = round(sum(b["close"] for b in bars[i - period + 1 : i + 1]) / period, 3)
                else:
                    bar[k] = None
            for period, k in [(5, "vol_ma5"), (10, "vol_ma10")]:
                if i + 1 >= period:
                    bar[k] = round(sum(b["volume"] for b in bars[i - period + 1 : i + 1]) / period, 1)
                else:
                    bar[k] = None

        # Calculate MACD (12, 26, 9)
        ema12 = ema26 = dea = 0.0
        for i, bar in enumerate(bars):
            c = bar["close"]
            if i == 0:
                ema12 = ema26 = c
                dif = dea = macd = 0.0
            else:
                ema12 = (2 * c + 11 * ema12) / 13.0
                ema26 = (2 * c + 25 * ema26) / 27.0
                dif = ema12 - ema26
                dea = (2 * dif + 8 * dea) / 10.0
                macd = 2 * (dif - dea)
            bar["dif"] = round(dif, 4)
            bar["dea"] = round(dea, 4)
            bar["macd"] = round(macd, 4)

        # Calculate KDJ (9, 3, 3)
        k_val = d_val = 50.0
        for i, bar in enumerate(bars):
            start_idx = max(0, i - 9 + 1)
            phs = [b["high"] for b in bars[start_idx : i + 1]]
            pls = [b["low"] for b in bars[start_idx : i + 1]]
            hn = max(phs)
            ln = min(pls)
            rsv = 50.0 if hn == ln else (bar["close"] - ln) / (hn - ln) * 100.0
            k_val = 2/3 * k_val + 1/3 * rsv
            d_val = 2/3 * d_val + 1/3 * k_val
            j_val = 3 * k_val - 2 * d_val
            bar["k"] = round(k_val, 2)
            bar["d"] = round(d_val, 2)
            bar["j"] = round(j_val, 2)

                # Evaluate 5-min Quant Signals
        for i in range(1, len(bars)):
            cur = bars[i]
            prev = bars[i - 1]
            time_str = cur.get("time", "")
            is_tail_session = (time_str >= "14:30" and time_str <= "14:50") if time_str else False

            # 取消日内购买，统一为尾盘购买：日内(14:30前)不触发任何买入信号，仅在尾盘窗口(14:30~14:50)触发并锁定买点！
            if is_tail_session:
                # B1: 尾盘KDJ超卖金叉 + MACD多头/企稳
                if prev["k"] <= prev["d"] and cur["k"] > cur["d"] and cur["k"] < 50 and cur["macd"] >= -0.01:
                    cur["signal_type"] = "B1"
                    cur["signal_name"] = "尾盘低吸"
                    cur["signal_reason"] = f"尾盘({time_str})KDJ金叉(K:{cur['k']})，MACD企稳回升"
                    cur["signal_position"] = "尾盘确定性建仓"
                # B2: 尾盘放量突破前高
                elif cur.get("vol_ma5") and cur["vol_ma5"] > 0 and cur["volume"] > 1.5 * cur["vol_ma5"] and cur["close"] > prev["high"] and cur["close"] > (cur.get("ma5") or 0):
                    cur["signal_type"] = "B2"
                    cur["signal_name"] = "尾盘放量突破"
                    ratio = round(cur["volume"] / cur["vol_ma5"], 1)
                    cur["signal_reason"] = f"尾盘({time_str})放量(+{ratio}倍)突破前高"
                    cur["signal_position"] = "尾盘顺势买入"

            # S1: 5分KDJ高位死叉
            elif prev["k"] >= prev["d"] and cur["k"] < cur["d"] and (prev["k"] >= 68 or cur["d"] >= 65):
                cur["signal_type"] = "S1"
                cur["signal_name"] = "5分高位死叉"
                cur["signal_reason"] = f"5分KDJ超买区死叉(前K:{prev['k']}, 现K:{cur['k']})"
                cur["signal_position"] = "冲高止盈减仓50%"
            # S2: 5分MACD死叉
            elif prev["dif"] >= prev["dea"] and cur["dif"] < cur["dea"]:
                cur["signal_type"] = "S2"
                cur["signal_name"] = "5分MACD死叉"
                cur["signal_reason"] = f"5分MACD高位死叉(DIF:{cur['dif']}, DEA:{cur['dea']})"
                cur["signal_position"] = "分批止盈离场"
            # S3: 5分跌破MA20生命线
            elif prev.get("ma20") and cur.get("ma20") and prev["close"] >= prev["ma20"] and cur["close"] < cur["ma20"]:
                cur["signal_type"] = "S3"
                cur["signal_name"] = "5分跌破MA20"
                cur["signal_reason"] = f"5分跌破20周期生命均线({cur['ma20']})"
                cur["signal_position"] = "破位防守清仓"

        intraday_signals = []
        for b in bars:
            if b.get("signal_type"):
                intraday_signals.append({
                    "type": b["signal_type"],
                    "name": b.get("signal_name", ""),
                    "reason": b.get("signal_reason", ""),
                    "time": b.get("time", ""),
                    "datetime": b.get("datetime", ""),
                    "price": b.get("close", 0.0),
                    "high": b.get("high", 0.0),
                    "low": b.get("low", 0.0)
                })

        name = stock_dict.get("name", symbol)
        if name == symbol:
            pool_map = {
                "sz159869": "游戏ETF华夏", "sh515180": "红利ETF易方达", "sz159819": "人工智能TF",
                "sh512720": "计算机ETF", "sh562500": "机器人ETF", "sz159611": "电力绿电ETF",
                "sz159851": "金融科技ETF", "sh512880": "证券ETF", "sh512660": "军工ETF",
                "sz159997": "电子ETF", "sz159995": "芯片ETF", "sh515880": "通信ETF",
                "sh512690": "酒ETF", "sh512010": "医药ETF", "sh512480": "半导体ETF",
                "sz159928": "消费ETF", "sh512800": "银行ETF", "sh515050": "5GETF",
                "sz159996": "家电ETF", "sh515790": "光伏ETF", "sh515030": "新能源车ETF",
                "sh510300": "沪深300ETF", "sh000001": "上证指数"
            }
            name = pool_map.get(symbol.lower(), symbol)

        return {
            "symbol": symbol,
            "name": name,
            "klines": bars,
            "intraday_signals": intraday_signals
        }

    def _get_appdata_config_path(self):
        appdata = os.environ.get("APPDATA")
        if appdata:
            config_dir = os.path.join(appdata, "StockMaster")
            try:
                os.makedirs(config_dir, exist_ok=True)
                return os.path.join(config_dir, "user_config.json")
            except Exception:
                pass
        return None

    def _get_local_config_path(self):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "user_config.json")

    def get_user_config(self):
        # 1. 优先从用户目录 %APPDATA%/StockMaster/user_config.json 读取 (跨版本、重新编译永不丢失)
        appdata_path = self._get_appdata_config_path()
        if appdata_path and os.path.exists(appdata_path):
            try:
                with open(appdata_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["_has_saved_config"] = True
                    return data
            except Exception:
                pass

        # 2. 其次尝试从本地程序目录读取
        local_path = self._get_local_config_path()
        if os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["_has_saved_config"] = True
                    return data
            except Exception:
                pass

        # 3. 若均不存在，返回默认配置并标明尚未自定义
        return {"total_pos_capital": 100000, "available_cash": 50000, "theme": "light", "_has_saved_config": False}

    def save_user_config(self, config_dict):
        try:
            current = self.get_user_config()
            if isinstance(config_dict, dict):
                current.update(config_dict)
            current["_has_saved_config"] = True

            # 双重持久化：同时写入 %APPDATA% 与本地程序目录，确保双保险
            appdata_path = self._get_appdata_config_path()
            if appdata_path:
                try:
                    with open(appdata_path, "w", encoding="utf-8") as f:
                        json.dump(current, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"Failed to save to appdata config: {e}")

            local_path = self._get_local_config_path()
            try:
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump(current, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Failed to save to local config: {e}")

            return True
        except Exception as e:
            print(f"Failed to save user config: {e}")
            return False


    def get_history_pnl_analysis(self, custom_list=None, total_capital=100000, max_pos_cap_pct=0.30):
        if not custom_list:
            custom_list = [
                {"sector": "金融科技", "code": "sz159851", "desc": "金融科技ETF"},
                {"sector": "人工智能", "code": "sz159819", "desc": "人工智能ETF"},
                {"sector": "半导体芯片", "code": "sz159995", "desc": "芯片ETF"},
                {"sector": "半导体设备", "code": "sz159516", "desc": "半导体设备ETF"},
                {"sector": "通信技术", "code": "sh515880", "desc": "通信ETF"},
                {"sector": "消费电子", "code": "sz159997", "desc": "电子ETF"},
                {"sector": "动漫游戏", "code": "sz159869", "desc": "游戏ETF"},
                {"sector": "计算机软件", "code": "sh512720", "desc": "计算机ETF"},
                {"sector": "新能源车", "code": "sh515030", "desc": "新能源车ETF"},
                {"sector": "光伏新能源", "code": "sh515790", "desc": "光伏ETF"},
                {"sector": "医药生物", "code": "sh512010", "desc": "医药ETF"},
                {"sector": "A股创新药", "code": "sz159992", "desc": "创新药ETF"},
                {"sector": "港股创新药", "code": "sz159567", "desc": "港股创新药ETF"},
                {"sector": "恒生医疗", "code": "sh513060", "desc": "恒生医疗ETF"},
                {"sector": "恒生互联网", "code": "sh513330", "desc": "恒生互联网ETF"},
                {"sector": "大金融证券", "code": "sh512880", "desc": "证券ETF"},
                {"sector": "国防军工", "code": "sh512660", "desc": "军工ETF"},
                {"sector": "人形机器人", "code": "sh562500", "desc": "机器人ETF"},
                {"sector": "有色金属", "code": "sh512400", "desc": "有色金属ETF"},
                {"sector": "煤炭周期", "code": "sh515220", "desc": "煤炭ETF"},
                {"sector": "电力绿电", "code": "sz159611", "desc": "电力ETF"},
                {"sector": "红利低波", "code": "sh515180", "desc": "红利ETF"}
            ]

        try:
            total_capital = float(total_capital) if total_capital and float(total_capital) > 0 else 100000.0
        except Exception:
            total_capital = 100000.0

        max_single_pos_cap = total_capital * float(max_pos_cap_pct)

        from concurrent.futures import ThreadPoolExecutor

        def fetch_one(item):
            try:
                code = item.get("code") or item.get("symbol")
                data = self.get_daily_klines(code)
                return item, data.get("klines", [])
            except Exception:
                return item, []

        with ThreadPoolExecutor(max_workers=12) as executor:
            stock_data = list(executor.map(fetch_one, custom_list))

        bench_data = self.get_daily_klines("sh000001").get("klines", [])
        bench_map = {b["date"]: b["close"] for b in bench_data}

        all_dates_set = set()
        for item, klines in stock_data:
            for k in klines:
                all_dates_set.add(k["date"])
        sorted_dates = sorted(list(all_dates_set))
        if len(sorted_dates) > 300:
            sorted_dates = sorted_dates[-300:]

        if not sorted_dates:
            return {
                "initial_capital": total_capital,
                "total_capital": total_capital,
                "total_assets": total_capital,
                "total_pnl": 0.0,
                "total_pct": 0.0,
                "capital_utilization": 0.0,
                "daily_curve": [],
                "closed_trades": []
            }

        stock_map = {}
        for item, klines in stock_data:
            code = item.get("code") or item.get("symbol")
            k_map = {k["date"]: k for k in klines}
            stock_map[code] = {
                "info": item,
                "klines": klines,
                "k_map": k_map
            }

        positions = {}
        closed_trades = []
        daily_records = []
        available_cash = total_capital
        start_bench_close = bench_map.get(sorted_dates[0], 3000.0)

        for d in sorted_dates:
            # Step 1: Process Sells & Profit Taking first to recover cash
            for code, s_obj in stock_map.items():
                k = s_obj["k_map"].get(d)
                if not k:
                    continue
                sig = k.get("signal_type")
                c = k["close"]
                pos = positions.get(code)

                if pos and pos["shares"] > 0:
                    if sig == "S3":
                        sell_shares = int(pos["shares"] * 0.5 / 100) * 100
                        if sell_shares > 0:
                            returned_cash = sell_shares * c
                            available_cash += returned_cash
                            pnl = sell_shares * (c - pos["cost_price"])
                            ret_pct = ((c - pos["cost_price"]) / pos["cost_price"] * 100.0) if pos["cost_price"] > 0 else 0.0
                            closed_trades.append({
                                "code": code,
                                "name": s_obj["info"].get("desc") or s_obj["info"].get("name", code),
                                "sector": s_obj["info"].get("sector", "自选"),
                                "buy_date": pos["buy_date"],
                                "sell_date": d,
                                "buy_price": round(pos["cost_price"], 3),
                                "sell_price": round(c, 3),
                                "shares": sell_shares,
                                "profit": round(pnl, 2),
                                "return_pct": round(ret_pct, 2),
                                "reason": "S3目标落袋50%"
                            })
                            pos["shares"] -= sell_shares
                            pos["buy_amount"] = pos["shares"] * pos["cost_price"]
                            if pos["shares"] <= 0:
                                positions[code] = None
                    elif sig in ["S1", "S2", "S4", "S7"]:
                        sell_shares = pos["shares"]
                        returned_cash = sell_shares * c
                        available_cash += returned_cash
                        pnl = sell_shares * (c - pos["cost_price"])
                        ret_pct = ((c - pos["cost_price"]) / pos["cost_price"] * 100.0) if pos["cost_price"] > 0 else 0.0
                        closed_trades.append({
                            "code": code,
                            "name": s_obj["info"].get("desc") or s_obj["info"].get("name", code),
                            "sector": s_obj["info"].get("sector", "自选"),
                            "buy_date": pos["buy_date"],
                            "sell_date": d,
                            "buy_price": round(pos["cost_price"], 3),
                            "sell_price": round(c, 3),
                            "shares": sell_shares,
                            "profit": round(pnl, 2),
                            "return_pct": round(ret_pct, 2),
                            "reason": k.get("signal_name", "分级止盈/清仓")
                        })
                        positions[code] = None

            # Step 2: Score buy candidates for day d
            buy_candidates = []
            for code, s_obj in stock_map.items():
                k = s_obj["k_map"].get(d)
                if not k:
                    continue
                sig = k.get("signal_type")
                if sig in ["B", "B1"]:
                    pos = positions.get(code)
                    cur_cost = pos["buy_amount"] if pos else 0.0
                    room = max_single_pos_cap - cur_cost
                    if k.get("close", 0) > 0 and room >= (k["close"] * 100):
                        dif = k.get("dif", 0.0)
                        score = k.get("score", 3)
                        trend_mult = 1.3 if dif > 0 else 1.0
                        conf_mult = 1.5 if score >= 4 else (1.0 if score == 3 else 0.7)
                        final_weight = max(0.5, score * trend_mult * conf_mult)
                        buy_candidates.append({
                            "code": code,
                            "price": k["close"],
                            "room": room,
                            "weight": final_weight,
                            "score": score
                        })

            # Step 3: Greedy Cash Allocation to maximize capital utilization
            if buy_candidates and available_cash >= 500:
                buy_candidates.sort(key=lambda x: x["weight"], reverse=True)
                total_weight = sum(c["weight"] for c in buy_candidates)

                # First pass: Proportional weighting
                for cand in buy_candidates:
                    if cand["price"] <= 0 or available_cash < (cand["price"] * 100):
                        continue
                    portion = (cand["weight"] / total_weight) if total_weight > 0 else (1.0 / len(buy_candidates))
                    target_budget = min(cand["room"], available_cash * portion)
                    if len(buy_candidates) <= 2 and available_cash > target_budget:
                        target_budget = min(cand["room"], available_cash * 0.7)

                    hands = int(target_budget / cand["price"] / 100)
                    if hands > 0:
                        shares = hands * 100
                        buy_cost = shares * cand["price"]
                        available_cash -= buy_cost
                        pos = positions.get(cand["code"])
                        if pos and pos["shares"] > 0:
                            tot_s = pos["shares"] + shares
                            pos["cost_price"] = (pos["shares"] * pos["cost_price"] + buy_cost) / tot_s if tot_s > 0 else cand["price"]
                            pos["shares"] = tot_s
                            pos["buy_amount"] += buy_cost
                        else:
                            positions[cand["code"]] = {
                                "shares": shares,
                                "cost_price": cand["price"],
                                "buy_date": d,
                                "buy_amount": buy_cost,
                                "score": cand["score"]
                            }

                # Second pass: Residual cash sweep into top candidate
                for cand in buy_candidates:
                    if cand["price"] <= 0:
                        continue
                    pos = positions.get(cand["code"])
                    cur_cost = pos["buy_amount"] if pos else 0.0
                    room = max_single_pos_cap - cur_cost
                    hands = int(min(available_cash, room) / cand["price"] / 100)
                    if hands > 0:
                        shares = hands * 100
                        buy_cost = shares * cand["price"]
                        available_cash -= buy_cost
                        if pos and pos["shares"] > 0:
                            tot_s = pos["shares"] + shares
                            pos["cost_price"] = (pos["shares"] * pos["cost_price"] + buy_cost) / tot_s if tot_s > 0 else cand["price"]
                            pos["shares"] = tot_s
                            pos["buy_amount"] += buy_cost
                        else:
                            positions[cand["code"]] = {
                                "shares": shares,
                                "cost_price": cand["price"],
                                "buy_date": d,
                                "buy_amount": buy_cost,
                                "score": cand["score"]
                            }

            # Step 4: Daily Portfolio Valuation
            current_market_val = 0.0
            for code, pos in positions.items():
                if pos and pos["shares"] > 0:
                    k = stock_map[code]["k_map"].get(d)
                    p = k["close"] if k else pos["cost_price"]
                    current_market_val += pos["shares"] * p

            tot_assets = current_market_val + available_cash
            tot_pnl = tot_assets - total_capital
            port_pct = (tot_pnl / total_capital) * 100.0
            cap_util = (current_market_val / tot_assets * 100.0) if tot_assets > 0 else 0.0

            b_close = bench_map.get(d, start_bench_close)
            bench_pct = ((b_close - start_bench_close) / start_bench_close) * 100.0 if start_bench_close > 0 else 0.0

            daily_records.append({
                "date": d,
                "total_assets": round(tot_assets, 2),
                "market_val": round(current_market_val, 2),
                "cash": round(available_cash, 2),
                "capital_utilization": round(cap_util, 1),
                "total_pnl": round(tot_pnl, 2),
                "portfolio_pct": round(port_pct, 2),
                "bench_pct": round(bench_pct, 2),
                "bench_close": b_close
            })

        latest = daily_records[-1] if daily_records else {}
        latest_date = latest.get("date", "")
        cur_year = latest_date[:4] if len(latest_date) >= 4 else "2026"
        cur_month = latest_date[:7] if len(latest_date) >= 7 else "2026-09"

        # 1. 今年收益 (YTD)
        year_recs = [r for r in daily_records if r["date"].startswith(cur_year)]
        year_base = year_recs[0] if year_recs else daily_records[0]
        year_pnl = round(latest.get("total_pnl", 0) - year_base.get("total_pnl", 0), 2)
        year_pct = round((year_pnl / total_capital) * 100.0, 2)
        year_bench_chg = round(((latest.get("bench_close", 1) - year_base.get("bench_close", 1)) / year_base.get("bench_close", 1)) * 100.0, 2) if year_base.get("bench_close") else 0.0
        year_alpha = round(year_pct - year_bench_chg, 2)

        # 2. 本月收益 (This Month)
        month_recs = [r for r in daily_records if r["date"].startswith(cur_month)]
        month_base = month_recs[0] if month_recs else daily_records[max(0, len(daily_records) - 22)]
        month_pnl = round(latest.get("total_pnl", 0) - month_base.get("total_pnl", 0), 2)
        month_pct = round((month_pnl / total_capital) * 100.0, 2)
        month_bench_chg = round(((latest.get("bench_close", 1) - month_base.get("bench_close", 1)) / month_base.get("bench_close", 1)) * 100.0, 2) if month_base.get("bench_close") else 0.0
        month_alpha = round(month_pct - month_bench_chg, 2)

        # 3. 本周收益 (This Week)
        week_recs = daily_records[-5:] if len(daily_records) >= 5 else daily_records
        week_base = week_recs[0] if week_recs else daily_records[0]
        week_pnl = round(latest.get("total_pnl", 0) - week_base.get("total_pnl", 0), 2)
        week_pct = round((week_pnl / total_capital) * 100.0, 2)
        week_bench_chg = round(((latest.get("bench_close", 1) - week_base.get("bench_close", 1)) / week_base.get("bench_close", 1)) * 100.0, 2) if week_base.get("bench_close") else 0.0
        week_alpha = round(week_pct - week_bench_chg, 2)

        # 4. 今日盈亏 (Today)
        prev_day = daily_records[-2] if len(daily_records) >= 2 else latest
        today_pnl = round(latest.get("total_pnl", 0) - prev_day.get("total_pnl", 0), 2)
        today_pct = round((today_pnl / total_capital) * 100.0, 2)

        # 5. 胜率与交易统计 (Trades Summary)
        win_trades = [t for t in closed_trades if t["profit"] > 0]
        loss_trades = [t for t in closed_trades if t["profit"] <= 0]
        total_closed_count = len(closed_trades)
        win_rate = round((len(win_trades) / total_closed_count * 100.0), 1) if total_closed_count > 0 else 0.0

        avg_win_pct = round(sum(t["return_pct"] for t in win_trades) / len(win_trades), 2) if win_trades else 0.0
        avg_loss_pct = round(sum(t["return_pct"] for t in loss_trades) / len(loss_trades), 2) if loss_trades else 0.0
        max_win = max([t["profit"] for t in closed_trades], default=0.0)
        max_loss = min([t["profit"] for t in closed_trades], default=0.0)

        closed_trades.reverse()

        return {
            "initial_capital": total_capital,
            "total_capital": total_capital,
            "total_assets": latest.get("total_assets", total_capital),
            "market_val": latest.get("market_val", 0.0),
            "available_cash": latest.get("cash", total_capital),
            "capital_utilization": latest.get("capital_utilization", 0.0),
            "total_pnl": latest.get("total_pnl", 0.0),
            "total_pct": latest.get("portfolio_pct", 0.0),
            "total_bench_pct": latest.get("bench_pct", 0.0),
            "total_alpha": round(latest.get("portfolio_pct", 0.0) - latest.get("bench_pct", 0.0), 2),
            "year": {
                "pnl": year_pnl,
                "pct": year_pct,
                "bench_pct": year_bench_chg,
                "alpha": year_alpha,
                "label": f"{cur_year}年以来"
            },
            "month": {
                "pnl": month_pnl,
                "pct": month_pct,
                "bench_pct": month_bench_chg,
                "alpha": month_alpha,
                "label": f"{cur_month[-2:]}月以来"
            },
            "week": {
                "pnl": week_pnl,
                "pct": week_pct,
                "bench_pct": week_bench_chg,
                "alpha": week_alpha,
                "label": "本周以来"
            },
            "today": {
                "pnl": today_pnl,
                "pct": today_pct
            },
            "stats": {
                "total_trades": total_closed_count,
                "win_trades": len(win_trades),
                "loss_trades": len(loss_trades),
                "win_rate": win_rate,
                "avg_win_pct": avg_win_pct,
                "avg_loss_pct": avg_loss_pct,
                "max_win": max_win,
                "max_loss": max_loss
            },
            "daily_curve": daily_records,
            "closed_trades": closed_trades[:80]
        }





