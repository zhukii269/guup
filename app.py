import os
import sys
import webview
from stock_data_provider import StockDataProvider
from interval_calculator import IntervalCalculator

class StockApi:
    def __init__(self):
        self.dp = StockDataProvider()

    def get_stock_data(self, symbol="sh000001"):
        return self.dp.get_daily_klines(symbol)

    def get_realtime_quote(self, symbol="sh000001"):
        return self.dp.get_realtime_quote(symbol)

    def calculate_interval_gain(self, klines, start_date, end_date, preset_key="1m"):
        if preset_key and preset_key != "custom":
            return IntervalCalculator.calculate_by_preset(klines, preset_key)
        return IntervalCalculator.calculate_by_dates(klines, start_date, end_date)

    def search_stock(self, keyword):
        return self.dp.search_stock(keyword)

    def get_watch_pool(self, custom_list=None):
        return self.dp.get_watch_pool(custom_list)

    def get_minute_data(self, symbol="sh000001"):
        return self.dp.get_minute_data(symbol)

    def get_5min_klines(self, symbol="sh000001"):
        return self.dp.get_5min_klines(symbol)

    def get_user_config(self):
        return self.dp.get_user_config()

    def save_user_config(self, config_dict):
        return self.dp.save_user_config(config_dict)

    def get_history_pnl_analysis(self, custom_list=None, total_capital=100000):
        return self.dp.get_history_pnl_analysis(custom_list, total_capital)

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
        min_size=(1120, 720),
        js_api=api,
        resizable=True,
        text_select=False
    )
    
    webview.start(debug=False)

if __name__ == "__main__":
    main()
