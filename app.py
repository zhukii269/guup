import os
import sys
import webview
from stock_data_provider import StockDataProvider
from interval_calculator import IntervalCalculator

class StockApi:
    def __init__(self):
        self._dp = StockDataProvider()
        self._window = None
        self._main_window = None
        self._ball_window = None
        self._ball_dock_x = None
        self._ball_dock_y = None
        self._prev_width = 1340
        self._prev_height = 920

    def _set_window(self, window):
        self._window = window
        self._main_window = window

    def _set_windows(self, main_win, ball_win):
        self._window = main_win
        self._main_window = main_win
        self._ball_window = ball_win

    def switch_to_ball_mode(self):
        try:
            self._in_ball_mode = True
            if self._main_window:
                self._main_window.hide()
            if self._ball_window:
                self.expand_ball("ball")
                self._ball_window.show()
                try:
                    self._ball_window.on_top = True
                except Exception:
                    pass
                self._ball_window.evaluate_js("window.onBallModeActivated && window.onBallModeActivated()")
            return True
        except Exception as e:
            print("switch_to_ball_mode error:", e)
            return False

    def switch_to_main_mode(self, symbol=None):
        try:
            self._in_ball_mode = False
            if self._ball_window:
                self._ball_window.hide()
            if self._main_window:
                self._main_window.show()
                try:
                    self._main_window.restore()
                except Exception:
                    pass
                if symbol:
                    clean_sym = str(symbol).strip()
                    self._main_window.evaluate_js(f"window.switchStock && window.switchStock('{clean_sym}')")
            return True
        except Exception as e:
            print("switch_to_main_mode error:", e)
            return False

    def expand_ball(self, mode="ball"):
        if not self._ball_window:
            return False
        try:
            if mode == "ball":
                w, h = 68, 68
            elif mode == "drawer":
                w, h = 330, 580
            elif mode == "kline":
                w, h = 760, 580
            else:
                w, h = 68, 68

            screen_w = 1920
            screen_h = 1080
            if webview.screens and len(webview.screens) > 0:
                screen_w = webview.screens[0].width
                screen_h = webview.screens[0].height

            cur_x = self._ball_window.x
            cur_y = self._ball_window.y
            cur_w = self._ball_window.width

            if cur_w <= 90:
                self._ball_dock_x = cur_x
                self._ball_dock_y = cur_y
            dock_x = getattr(self, '_ball_dock_x', cur_x)
            dock_y = getattr(self, '_ball_dock_y', cur_y)
            if dock_x is None:
                dock_x = max(10, screen_w - 90)
            if dock_y is None:
                dock_y = 240

            if dock_x > screen_w / 2:
                right_edge = min(screen_w - 6, dock_x + 68)
                new_x = max(10, right_edge - w)
            else:
                new_x = max(10, dock_x)

            new_y = min(max(10, dock_y), screen_h - h - 40)

            self._ball_window.move(int(new_x), int(new_y))
            self._ball_window.resize(int(w), int(h))
            return True
        except Exception as e:
            print("expand_ball error:", e)
            return False

    def set_mini_mode(self, is_mini=True, width=960, height=68, on_top=True):
        if is_mini:
            return self.switch_to_ball_mode()
        else:
            return self.switch_to_main_mode()

    def set_always_on_top(self, on_top=True):
        win = self._main_window or self._window
        if not win:
            return False
        try:
            win.on_top = bool(on_top)
            return True
        except Exception as e:
            print("set_always_on_top error:", e)
            return False

    def minimize_window(self):
        win = self._main_window or self._window
        if win:
            try:
                win.minimize()
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
    ball_html_path = get_asset_path("ball.html")
    
    if not os.path.exists(html_path):
        print(f"Error: Asset file not found at {html_path}")
        sys.exit(1)

    screen_w = 1920
    screen_h = 1080
    if webview.screens and len(webview.screens) > 0:
        screen_w = webview.screens[0].width
        screen_h = webview.screens[0].height

    init_ball_x = max(10, screen_w - 90)
    init_ball_y = min(240, max(50, int(screen_h * 0.25)))

    main_win = webview.create_window(
        title="同花顺风格 - 股票与指数日K线涨幅分析系统",
        url=html_path,
        width=1340,
        height=920,
        min_size=(900, 600),
        js_api=api,
        resizable=True,
        text_select=False
    )

    ball_win = webview.create_window(
        title="StockBall",
        url=ball_html_path,
        width=68,
        height=68,
        x=init_ball_x,
        y=init_ball_y,
        min_size=(40, 40),
        frameless=True,
        transparent=True,
        on_top=True,
        js_api=api,
        resizable=True
    )

    api._set_windows(main_win, ball_win)

    def on_ball_shown():
        # Keep hidden on startup until user switches to ball mode
        if not getattr(api, '_in_ball_mode', False):
            try:
                ball_win.hide()
            except Exception:
                pass

    ball_win.events.shown += on_ball_shown

    def on_main_closed():
        try:
            ball_win.destroy()
        except Exception:
            pass

    def on_ball_closed():
        try:
            main_win.destroy()
        except Exception:
            pass

    main_win.events.closed += on_main_closed
    ball_win.events.closed += on_ball_closed

    webview.start(debug=False)

if __name__ == "__main__":
    main()
