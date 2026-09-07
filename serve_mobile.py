import http.server
import socketserver
import socket
import os
import sys

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class MobileHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mobile")
        super().__init__(*args, directory=base_dir, **kwargs)

    def end_headers(self):
        # 允许所有跨域请求与手机端缓存控制
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

def main():
    port = 8080
    local_ip = get_local_ip()
    
    # 尝试绑定端口
    for p in range(8080, 8090):
        try:
            server = socketserver.TCPServer(("", p), MobileHandler)
            port = p
            break
        except OSError:
            continue
    else:
        print("Error: Ports 8080-8090 are occupied.")
        sys.exit(1)

    mobile_url = f"http://{local_ip}:{port}/index.html"
    local_url = f"http://localhost:{port}/index.html"

    print("=" * 66)
    print("🚀 【ETF量化大师 - 手机端服务已就绪】")
    print("=" * 66)
    print(f"\n📱 手机端访问地址 (确保手机与电脑连接同一个 WiFi):")
    print(f"   👉 {mobile_url}\n")
    print(f"💻 电脑浏览器调试预览地址:")
    print(f"   👉 {local_url}\n")
    print("-" * 66)
    print("📲 【如何将它变成手机原生 App (无需签名，永久免过期)】:")
    print("  🍎 苹果 iOS (iPhone):")
    print("     1. 用自带 Safari 浏览器打开上方链接;")
    print("     2. 点击底部的【分享】按钮 (向上箭头的方框);")
    print("     3. 下滑点击【添加到主屏幕】;")
    print("     4. 手机桌面上即刻生成【ETF量化大师】App 图标，点击全屏运行！\n")
    print("  🤖 安卓 Android:")
    print("     1. 用 Chrome 浏览器或自带浏览器打开上方链接;")
    print("     2. 点击右上角菜单【...】;")
    print("     3. 点击【添加到主屏幕】或【安装应用】;")
    print("     4. 手机桌面即刻生成 App 图标，拥有原生 App 相同体验！")
    print("=" * 66)
    print("按 Ctrl + C 可停止服务。\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已平稳停止。")

if __name__ == "__main__":
    main()
