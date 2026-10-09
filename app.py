import os
import sys
import webview
from stock_data_provider import StockDataProvider
from interval_calculator import IntervalCalculator

def apply_win32_window_shape(window, mode="ball", alpha=255):
    try:
        import ctypes
        if not hasattr(window, 'native') or not window.native:
            return
        form = window.native
        hwnd = form.Handle.ToInt32()
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        dwmapi = ctypes.windll.dwmapi
        
        # 1. Physical Window Region Shaping (Zero square border, hardware-clipped)
        if mode == "ball":
            # 68x68 canvas: perfect 60px circle from (4, 4) to (64, 64)
            hrgn = gdi32.CreateEllipticRgn(4, 4, 64, 64)
        elif mode == "drawer":
            # 330x580 canvas: rounded rectangle with 20px radius
            hrgn = gdi32.CreateRoundRectRgn(0, 0, 330, 580, 20, 20)
        elif mode == "kline":
            # 760x580 canvas: rounded rectangle with 20px radius
            hrgn = gdi32.CreateRoundRectRgn(0, 0, 760, 580, 20, 20)
        else:
            hrgn = gdi32.CreateEllipticRgn(4, 4, 64, 64)
            
        user32.SetWindowRgn(hwnd, hrgn, True)
        
        # 2. Native DWM Desktop Glass Transparency
        class MARGINS(ctypes.Structure):
            _fields_ = [
                ("cxLeftWidth", ctypes.c_int),
                ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int),
                ("cyBottomHeight", ctypes.c_int),
            ]
        margins = MARGINS(-1, -1, -1, -1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
        
        # 3. Ensure WinForms Form is Black and WebView2 is Transparent on UI thread
        try:
            import clr
            clr.AddReference('System.Drawing')
            from System.Drawing import Color
            import System

            def set_dwm_colors():
                try:
                    form.BackColor = Color.Black
                except Exception:
                    pass
                try:
                    if hasattr(form, 'browser') and hasattr(form.browser, 'webview'):
                        form.browser.webview.DefaultBackgroundColor = Color.Transparent
                except Exception:
                    pass

            form.BeginInvoke(System.Action(set_dwm_colors))
        except Exception:
            pass

        # 4. Remove dark WS_EX_LAYERED tint so DWM renders pure crystalline desktop glass
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x80000
        exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if exstyle & WS_EX_LAYERED:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle & ~WS_EX_LAYERED)

    except Exception as e:
        print("apply_win32_window_shape error:", e)

apply_win32_layered_transparency = apply_win32_window_shape

class StockApi:
    def __init__(self):
        self._dp = StockDataProvider()
        self._window = None
        self._main_window = None
        self._ball_window = None
        self._ball_dock_x = None
        self._ball_dock_y = None
        self._in_ball_mode = False
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
                if getattr(self, '_latest_watch_pool', None):
                    try:
                        import json
                        pool_json = json.dumps(self._latest_watch_pool)
                        self._ball_window.evaluate_js(f"window.onWatchPoolUpdated && window.onWatchPoolUpdated({pool_json})")
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
                try:
                    self._ball_window.move(-5000, -5000)
                except Exception:
                    pass
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

    def on_ball_drag_end(self):
        if not self._ball_window:
            return False
        try:
            screen_w = 1920
            if webview.screens and len(webview.screens) > 0:
                screen_w = webview.screens[0].width

            cur_x = self._ball_window.x
            cur_y = self._ball_window.y
            cur_w = self._ball_window.width

            if cur_w <= 90:
                self._ball_dock_x = cur_x
                self._ball_dock_y = cur_y
            else:
                if cur_x > screen_w / 2:
                    self._ball_dock_x = cur_x + cur_w - 68
                else:
                    self._ball_dock_x = cur_x
                self._ball_dock_y = cur_y
            return True
        except Exception as e:
            print("on_ball_drag_end error:", e)
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

            if cur_w <= 90 and cur_x > 0:
                self._ball_dock_x = cur_x
                self._ball_dock_y = cur_y
            elif cur_w > 90 and cur_x > 0 and getattr(self, '_ball_dock_x', None) is None:
                if cur_x > screen_w / 2:
                    self._ball_dock_x = cur_x + cur_w - 68
                else:
                    self._ball_dock_x = cur_x
                self._ball_dock_y = cur_y

            dock_x = getattr(self, '_ball_dock_x', None)
            dock_y = getattr(self, '_ball_dock_y', None)
            if dock_x is None or dock_x < 0:
                dock_x = max(10, screen_w - 90)
            if dock_y is None or dock_y < 0:
                dock_y = 240

            if mode == "ball":
                # In ball mode, stay EXACTLY at dock position!
                new_x = max(0, min(screen_w - 68, dock_x))
                new_y = max(0, min(screen_h - 68, dock_y))
            else:
                # In drawer / kline mode, expand outwards from dock position
                if dock_x > screen_w / 2:
                    right_edge = min(screen_w - 6, dock_x + 68)
                    new_x = max(10, right_edge - w)
                else:
                    new_x = max(10, dock_x)
                new_y = min(max(10, dock_y), screen_h - h - 40)

            self._ball_window.move(int(new_x), int(new_y))
            self._ball_window.resize(int(w), int(h))
            apply_win32_window_shape(self._ball_window, mode=mode)
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
        res = self._dp.get_watch_pool(custom_list)
        if res and isinstance(res, list):
            self._latest_watch_pool = res
            try:
                import json
                pool_json = json.dumps(res)
                if self._ball_window:
                    self._ball_window.evaluate_js(f"window.onWatchPoolUpdated && window.onWatchPoolUpdated({pool_json})")
            except Exception:
                pass
        return res

    def broadcast_watch_pool(self, pool_data):
        try:
            import json
            if isinstance(pool_data, list) and len(pool_data) > 0:
                self._latest_watch_pool = pool_data
                pool_json = json.dumps(pool_data)
                if self._ball_window:
                    self._ball_window.evaluate_js(f"window.onWatchPoolUpdated && window.onWatchPoolUpdated({pool_json})")
                if self._main_window:
                    self._main_window.evaluate_js(f"window.onWatchPoolUpdated && window.onWatchPoolUpdated({pool_json})")
            return True
        except Exception as e:
            print("broadcast_watch_pool error:", e)
            return False

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
        x=-5000,
        y=-5000,
        min_size=(40, 40),
        frameless=True,
        transparent=True,
        hidden=True,
        on_top=True,
        js_api=api,
        resizable=True
    )

    api._set_windows(main_win, ball_win)

    def on_ball_moved(x, y):
        if getattr(api, '_in_ball_mode', False) and x > 0 and y > 0:
            screen_w = 1920
            if webview.screens and len(webview.screens) > 0:
                screen_w = webview.screens[0].width
            cur_w = ball_win.width
            if cur_w <= 90:
                api._ball_dock_x = x
                api._ball_dock_y = y
            else:
                if x > screen_w / 2:
                    api._ball_dock_x = x + cur_w - 68
                else:
                    api._ball_dock_x = x
                api._ball_dock_y = y

    ball_win.events.moved += on_ball_moved

    def on_ball_shown():
        # Strictly keep hidden and offscreen on startup until user clicks floating ball mode
        if not getattr(api, '_in_ball_mode', False):
            try:
                ball_win.hide()
                ball_win.move(-5000, -5000)
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
