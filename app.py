import os
import sys
import webview
from stock_data_provider import StockDataProvider
from interval_calculator import IntervalCalculator

class StockApi:
    def __init__(self):
        self._dp = StockDataProvider()
        self._window = None
        self._prev_width = 1340
        self._prev_height = 920

    def _set_window(self, window):
        self._window = window

    def set_mini_mode(self, is_mini=True, width=960, height=68, on_top=True):
        if not self._window:
            return False
        try:
            if is_mini:
                if self._window.width > 500 and self._window.height > 300:
                    self._prev_width = self._window.width
                    self._prev_height = self._window.height
                try:
                    self._window.on_top = bool(on_top)
                except Exception as e:
                    print("set on_top error:", e)
                self._window.resize(int(width), int(height))
            else:
                try:
                    self._window.on_top = False
                except Exception as e:
                    print("set on_top error:", e)
                w = max(1120, getattr(self, '_prev_width', 1340))
                h = max(720, getattr(self, '_prev_height', 920))
                self._window.resize(int(w), int(h))
            return True
        except Exception as e:
            print("set_mini_mode error:", e)
            return False

    def set_always_on_top(self, on_top=True):
        if not self._window:
            return False
        try:
            self._window.on_top = bool(on_top)
            return True
        except Exception as e:
            print("set_always_on_top error:", e)
            return False

    def minimize_window(self):
        if self._window:
            try:
                self._window.minimize()
                return True
            except Exception as e:
                print("minimize_window error:", e)
        return False

    def get_stock_data(self, symbol="sh000001"):
        return self._dp.get_daily_klines(symbol)

    def get_realtime_quote(self, symbol="sh000001"):
        return self._dp.get_realtime_quote(symbol)

    def calculate_interval_gain(self, klines, start_date, end_date, preset_key="1m"):
        if preset_key and preset_key != "custom":
            return IntervalCalculator.calculate_by_preset(klines, preset_key)
        return IntervalCalculator.calculate_by_dates(klines, start_date, end_date)

    def search_stock(self, keyword):
        return self._dp.search_stock(keyword)

    def get_watch_pool(self, custom_list=None):
        return self._dp.get_watch_pool(custom_list)

    def get_minute_data(self, symbol="sh000001"):
        return self._dp.get_minute_data(symbol)

    def get_5min_klines(self, symbol="sh000001"):
        return self._dp.get_5min_klines(symbol)

    def get_30min_klines(self, symbol="sh000001"):
        return self._dp.get_30min_klines(symbol)

    def get_60min_klines(self, symbol="sh000001"):
        return self._dp.get_60min_klines(symbol)

    def get_user_config(self):
        return self._dp.get_user_config()

    def save_user_config(self, config_dict):
        return self._dp.save_user_config(config_dict)

    def get_history_pnl_analysis(self, custom_list=None, total_capital=100000):
        return self._dp.get_history_pnl_analysis(custom_list, total_capital)

    def get_batch_realtime_quotes(self, symbols=None):
        return self._dp.get_batch_realtime_quotes(symbols)

def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, "assets", filename)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", filename))

def main():
    api = StockApi()
    html_path = get_asset_path("index.html")
    
    if not os.path.exists(html_path):
        print(f"Error: Asset file not found at {html_path}")
        sys.exit(1)

    window = webview.create_window(
        title="同花顺风格 - 股票与指数日K线涨幅分析系统",
        url=html_path,
        width=1340,
        height=920,
        min_size=(200, 48),
        js_api=api,
        resizable=True,
        text_select=False
    )
    api._set_window(window)
    
    webview.start(debug=False)

if __name__ == "__main__":
    main()
