"""Debug dashboard loading v2 - check window.EMBEDDED_DATA and errors."""
import http.server
import socketserver
import threading
import time
import os

from playwright.sync_api import sync_playwright

PORT = 9902
BASE_DIR = r"C:\Users\CYYS\WorkBuddy\2026-06-16-11-25-31"
DASHBOARD_URL = f"http://localhost:{PORT}/index.html"

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)
    def log_message(self, format, *args):
        pass

def start_server():
    with socketserver.TCPServer(("", PORT), QuietHandler) as httpd:
        httpd.serve_forever()

server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()
time.sleep(1)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    
    logs = []
    def handle_log(msg):
        logs.append(f"{msg.type}: {msg.text}")
    page.on("console", handle_log)
    
    page.on("pageerror", lambda err: logs.append(f"PAGEERROR: {err}"))
    
    page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
    time.sleep(5)
    
    print("=== Logs ===")
    for log in logs:
        print(log)
    
    print("\n=== Window data ===")
    for name in ["EMBEDDED_DATA", "EMBEDDED_DATE_START", "EMBEDDED_DATE_END", "STORE_MP"]:
        val = page.evaluate(f"window.{name}")
        print(f"window.{name}: {type(val).__name__} (truthy: {bool(val)})")
        if val and isinstance(val, str):
            print(f"  len={len(val)}")
    
    # Check if init function exists and has errors
    print("\n=== Init execution test ===")
    try:
        result = page.evaluate("""
            (() => {
                try {
                    const top = document.getElementById('top-metrics');
                    const filter = document.getElementById('globalFilterBar');
                    return {
                        topExists: !!top,
                        topHTML: top ? top.innerHTML.substring(0, 100) : 'null',
                        filterExists: !!filter,
                        error: null
                    };
                } catch(e) {
                    return { error: e.message };
                }
            })()
        """)
        print(result)
    except Exception as e:
        print(f"eval error: {e}")
    
    browser.close()
