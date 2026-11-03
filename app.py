import os
import sys
import webview
from stock_data_provider import StockDataProvider
from interval_calculator import IntervalCalculator

def patch_pywebview_evaluate_js():
    try:
        import webview.platforms.winforms as wf
        import json
        from threading import Semaphore
        import System
        from System import Action, Func, String, Object
        from System.Threading.Tasks import Task

        def safe_evaluate_js(self, script: str, parse_json: bool):
            def _callback(res):
                nonlocal result
                if parse_json and res is not None:
                    try:
                        result = json.loads(res)
                    except Exception:
                        result = res
                else:
                    result = res
                semaphore.release()

            def _on_task_completed(task):
                try:
                    raw = task.Result
                    parsed = None
                    if raw is not None:
                        try:
                            parsed = json.loads(raw)
                        except Exception:
                            parsed = raw
                    _callback(parsed)
                except Exception:
                    try:
                        semaphore.release()
                    except Exception:
                        pass

            result = None
            semaphore = Semaphore(0)

            try:
                if not hasattr(self, 'webview') or self.webview is None:
                    return None
                if hasattr(self, 'form') and self.form and not self.form.Visible:
                    # Form is hidden; strictly return None without any Invoke to prevent WinForms STA deadlocks
                    return None

                self.webview.Invoke(
                    Func[Object](
                        lambda: self.webview.ExecuteScriptAsync(script).ContinueWith(
                            Action[Task[String]](_on_task_completed),
                            self.syncContextTaskScheduler,
                        )
                    )
                )
                # 0.5s timeout: strictly prevent any deadlock if window state changes
                if not semaphore.acquire(timeout=0.5):
                    pass
            except Exception as e:
                try:
                    semaphore.release()
                except Exception:
                    pass

            return result

        wf.Chromium.EdgeChrome.evaluate_js = safe_evaluate_js
        print("EdgeChrome.evaluate_js safely patched with timeout and hidden guard.")
    except Exception as e:
        print("patch_pywebview_evaluate_js warning:", e)

import ctypes
from ctypes import wintypes

_user32 = ctypes.windll.user32
_user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT
]
_user32.SetWindowPos.restype = wintypes.BOOL

_HWND_TOPMOST = wintypes.HWND(-1)
_HWND_NOTOPMOST = wintypes.HWND(-2)
_SWP_SHOWWINDOW = 0x0040

def set_ball_window_bounds(ball_win, x, y, w, h, on_top=True):
    try:
        if not hasattr(ball_win, 'native') or not ball_win.native:
            ball_win.move(int(x), int(y))
            ball_win.resize(int(w), int(h))
            return
        form = ball_win.native
        hwnd = form.Handle.ToInt64() if hasattr(form.Handle, 'ToInt64') else int(form.Handle)
        scale = getattr(form, '_scale', 1.0)
        phys_x = int(x * scale)
        phys_y = int(y * scale)
        phys_w = int(w * scale)
        phys_h = int(h * scale)
        
        insert_after = _HWND_TOPMOST if on_top else _HWND_NOTOPMOST
        success = _user32.SetWindowPos(hwnd, insert_after, phys_x, phys_y, phys_w, phys_h, _SWP_SHOWWINDOW)
        if not success:
            ball_win.move(int(x), int(y))
            ball_win.resize(int(w), int(h))
    except Exception as e:
        print("set_ball_window_bounds error:", e)
        try:
            ball_win.move(int(x), int(y))
            ball_win.resize(int(w), int(h))
        except Exception:
            pass

def init_win32_ball_transparency(ball_win):
    try:
        import ctypes
        if not hasattr(ball_win, 'native') or not ball_win.native:
            return
        form = ball_win.native
        hwnd = form.Handle.ToInt64() if hasattr(form.Handle, 'ToInt64') else int(form.Handle)
        dwmapi = ctypes.windll.dwmapi
        
        class MARGINS(ctypes.Structure):
            _fields_ = [
                ("cxLeftWidth", ctypes.c_int),
                ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int),
                ("cyBottomHeight", ctypes.c_int),
            ]
        margins = MARGINS(-1, -1, -1, -1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
    except Exception as e:
        print("init_win32_ball_transparency error:", e)

def apply_win32_window_shape(window, mode="ball", alpha=255):
    try:
        import ctypes
        if not hasattr(window, 'native') or not window.native:
            return
        form = window.native
        # Safe conversion of IntPtr to int across 32-bit and 64-bit platforms
        hwnd = form.Handle.ToInt64() if hasattr(form.Handle, 'ToInt64') else int(form.Handle)
        dwmapi = ctypes.windll.dwmapi
        
        # Native DWM Desktop Glass Transparency
        class MARGINS(ctypes.Structure):
            _fields_ = [
                ("cxLeftWidth", ctypes.c_int),
                ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int),
                ("cyBottomHeight", ctypes.c_int),
            ]
        margins = MARGINS(-1, -1, -1, -1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
        
        # Ensure WinForms Form is Black and WebView2 is Transparent on UI thread
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

            if hasattr(form, 'InvokeRequired') and form.InvokeRequired:
                form.BeginInvoke(System.Action(set_dwm_colors))
            else:
                set_dwm_colors()
        except Exception:
            pass

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
        self._latest_watch_pool = self._dp._load_disk_watch_pool_cache() or []

    def _set_window(self, window):
        self._window = window
        self._main_window = window

    def _set_windows(self, main_win, ball_win):
        self._window = main_win
        self._main_window = main_win
        self._ball_window = ball_win
        try:
            screen_w = webview.screens[0].width if webview.screens else 1920
            self._ball_dock_x = max(10, screen_w - 90)
            self._ball_dock_y = 240
        except Exception:
            self._ball_dock_x = 1800
            self._ball_dock_y = 240

    def switch_to_ball_mode(self, pool_data=None):
        try:
            self._in_ball_mode = True
            if pool_data and isinstance(pool_data, list) and len(pool_data) > 0:
                self._latest_watch_pool = pool_data
                self._dp._save_disk_watch_pool_cache(pool_data)

            # Signal main window to halt polling timers immediately
            if self._main_window:
                try:
                    self._main_window.evaluate_js("window.onBallModeActivated && window.onBallModeActivated()")
                except Exception:
                    pass

            if self._ball_window:
                self.expand_ball("ball")
                self._ball_window.show()
                # Activate floating ball state and quotes
                try:
                    self._ball_window.evaluate_js("window.onBallModeActivated && window.onBallModeActivated()")
                except Exception:
                    pass

            # Defer hiding main window slightly so the current IPC callback can return cleanly
            import threading
            threading.Timer(0.12, self._do_hide_main_window).start()
            return True
        except Exception as e:
            print("switch_to_ball_mode error:", e)
            return False

    def _do_hide_main_window(self):
        try:
            if getattr(self, '_in_ball_mode', False) and self._main_window:
                self._main_window.hide()
                # Ensure ball window is active foreground window
                if self._ball_window and hasattr(self._ball_window, 'native') and self._ball_window.native:
                    try:
                        form = self._ball_window.native
                        hwnd = form.Handle.ToInt64() if hasattr(form.Handle, 'ToInt64') else int(form.Handle)
                        _user32.SetForegroundWindow(hwnd)
                    except Exception:
                        pass
        except Exception as e:
            print("_do_hide_main_window error:", e)

    def switch_to_main_mode(self, symbol=None):
        try:
            self._in_ball_mode = False
            # Immediately notify ball window to pause background timers
            if self._ball_window:
                try:
                    self._ball_window.evaluate_js("window.onBallModeDeactivated && window.onBallModeDeactivated()")
                except Exception:
                    pass

            if self._main_window:
                self._main_window.show()
                try:
                    self._main_window.restore()
                except Exception:
                    pass
                try:
                    self._main_window.evaluate_js("window.onMainModeActivated && window.onMainModeActivated()")
                except Exception:
                    pass
                if symbol:
                    clean_sym = str(symbol).strip()
                    try:
                        self._main_window.evaluate_js(f"window.switchStock && window.switchStock('{clean_sym}')")
                    except Exception:
                        pass

            # Defer hiding ball window slightly so the current IPC callback can return cleanly
            import threading
            threading.Timer(0.12, self._do_hide_ball_window).start()
            return True
        except Exception as e:
            print("switch_to_main_mode error:", e)
            return False

    def _do_hide_ball_window(self):
        try:
            if not getattr(self, '_in_ball_mode', False) and self._ball_window:
                self._ball_window.hide()
                try:
                    self._ball_window.move(-5000, -5000)
                except Exception:
                    pass
        except Exception as e:
            print("_do_hide_ball_window error:", e)

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

            if cur_x > 0 and cur_y > 0:
                if cur_w <= 90:
                    self._ball_dock_x = cur_x
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

            # Maintain dock position on screen
            dock_x = getattr(self, '_ball_dock_x', None)
            dock_y = getattr(self, '_ball_dock_y', None)
            if dock_x is None or dock_x <= 0:
                dock_x = max(10, screen_w - 90)
                self._ball_dock_x = dock_x
            if dock_y is None or dock_y <= 0:
                dock_y = 240
                self._ball_dock_y = dock_y

            if mode == "ball":
                new_x = max(0, min(screen_w - 68, dock_x))
                new_y = max(0, min(screen_h - 68, dock_y))
            else:
                if dock_x > screen_w / 2:
                    right_edge = min(screen_w - 6, dock_x + 68)
                    new_x = max(10, right_edge - w)
                else:
                    new_x = max(10, dock_x)
                new_y = min(max(10, dock_y), screen_h - h - 40)

            # Move and resize window atomically via Win32 SetWindowPos
            set_ball_window_bounds(self._ball_window, new_x, new_y, w, h, on_top=True)
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
            self._dp._save_disk_watch_pool_cache(res)
        return res

    def get_current_watch_pool(self):
        if getattr(self, '_latest_watch_pool', None) and len(self._latest_watch_pool) > 0:
            return self._latest_watch_pool
        disk_pool = self._dp._load_disk_watch_pool_cache()
        if disk_pool and len(disk_pool) > 0:
            self._latest_watch_pool = disk_pool
            return disk_pool
        return []

    def broadcast_watch_pool(self, pool_data):
        try:
            if isinstance(pool_data, list) and len(pool_data) > 0:
                self._latest_watch_pool = pool_data
                self._dp._save_disk_watch_pool_cache(pool_data)
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

active_api = None

def main():
    global active_api
    patch_pywebview_evaluate_js()
    api = StockApi()
    active_api = api
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
            cur_w = ball_win.width
            if cur_w <= 90:
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
        else:
            init_win32_ball_transparency(ball_win)

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
