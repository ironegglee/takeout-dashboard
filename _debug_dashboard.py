"""Debug dashboard loading and capture data."""
import http.server
import socketserver
import threading
import time
import os

from playwright.sync_api import sync_playwright

PORT = 9901
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
    
    # Collect console logs
    logs = []
    def handle_log(msg):
        logs.append(f"{msg.type}: {msg.text}")
    page.on("console", handle_log)
    
    page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
    time.sleep(5)
    
    # Check state
    print("=== Console logs ===")
    for log in logs:
        print(log)
    
    print("\n=== Page state ===")
    # Check if top-metrics has content
    top_html = page.evaluate("document.getElementById('top-metrics')?.innerHTML || 'NOT_FOUND'")
    print(f"top-metrics length: {len(top_html)}")
    if len(top_html) < 200:
        print(top_html[:500])
    
    # Check if data range is set
    data_range = page.evaluate("document.getElementById('data-range-display')?.innerText || 'NOT_FOUND'")
    print(f"data-range-display: {data_range}")
    
    # Check if EMBEDDED_DATA exists
    has_data = page.evaluate("typeof EMBEDDED_DATA !== 'undefined'")
    print(f"EMBEDDED_DATA defined: {has_data}")
    if has_data:
        keys = page.evaluate("Object.keys(EMBEDDED_DATA)")
        print(f"EMBEDDED_DATA keys: {keys}")
    
    # Try clicking "全部" button
    try:
        all_btns = page.locator("button", has_text="全部")
        print(f"全部 buttons: {all_btns.count()}")
        if all_btns.count() > 0:
            all_btns.first.click()
            time.sleep(3)
    except Exception as e:
        print(f"click 全部 error: {e}")
    
    # Take screenshot after clicking
    page.screenshot(path=os.path.join(BASE_DIR, "screenshots", "debug_after_click.png"), full_page=True)
    
    browser.close()
