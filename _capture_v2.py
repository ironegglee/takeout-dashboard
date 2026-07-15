"""Capture dashboard screenshots for case study Word document."""
import http.server
import socketserver
import threading
import time
import os

from playwright.sync_api import sync_playwright

PORT = 9900
BASE_DIR = r"C:\Users\CYYS\WorkBuddy\2026-06-16-11-25-31"
OUTPUT_DIR = os.path.join(BASE_DIR, "screenshots")
DASHBOARD_URL = f"http://localhost:{PORT}/index.html"

os.makedirs(OUTPUT_DIR, exist_ok=True)

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
print(f"Server on port {PORT}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
    time.sleep(4)
    
    # Close any drawer
    try:
        page.locator(".drawer-close").first.click(timeout=1000)
        time.sleep(0.5)
    except:
        pass

    screenshots = {}

    # 1. Full page
    path = os.path.join(OUTPUT_DIR, "01_full.png")
    page.screenshot(path=path, full_page=True)
    screenshots["01_full"] = path

    # 2. Top metrics cards
    try:
        el = page.locator("#top-metrics")
        if el.count():
            path = os.path.join(OUTPUT_DIR, "02_top_metrics.png")
            el.first.screenshot(path=path)
            screenshots["02_top_metrics"] = path
    except Exception as e:
        print(f"err top metrics: {e}")

    # 3. Channel panels (MP + MT side by side)
    try:
        mp = page.locator("#mp-section")
        mt = page.locator("#mt-section")
        if mp.count() and mt.count():
            # Find parent container
            parent = page.locator(".main-content .channels-row, .content > div:nth-child(2)")
            path = os.path.join(OUTPUT_DIR, "03_channel_panels.png")
            page.screenshot(path=path, full_page=False)
            screenshots["03_channel_panels"] = path
    except Exception as e:
        print(f"err channel: {e}")

    # 4. Management ranking grids
    try:
        el = page.locator("#mgmt-grid-wrap")
        if el.count():
            el.first.scroll_into_view_if_needed()
            time.sleep(0.5)
            path = os.path.join(OUTPUT_DIR, "04_mgmt_ranking.png")
            page.screenshot(path=path, full_page=False)
            screenshots["04_mgmt_ranking"] = path
    except Exception as e:
        print(f"err mgmt: {e}")

    # 5. Single store data
    try:
        el = page.locator("#single-store-card")
        if el.count():
            el.first.scroll_into_view_if_needed()
            time.sleep(0.3)
            path = os.path.join(OUTPUT_DIR, "05_single_store.png")
            el.first.screenshot(path=path)
            screenshots["05_single_store"] = path
    except Exception as e:
        print(f"err single: {e}")

    # 6. Alert section
    try:
        el = page.locator("#alert-section")
        if el.count():
            el.first.scroll_into_view_if_needed()
            time.sleep(0.3)
            path = os.path.join(OUTPUT_DIR, "06_alerts.png")
            el.first.screenshot(path=path)
            screenshots["06_alerts"] = path
    except Exception as e:
        print(f"err alerts: {e}")

    # 7. Benchmark + Warning stores
    try:
        el = page.locator("#store-rank-section")
        if el.count():
            el.first.scroll_into_view_if_needed()
            time.sleep(0.3)
            path = os.path.join(OUTPUT_DIR, "07_benchmark.png")
            el.first.screenshot(path=path)
            screenshots["07_benchmark"] = path
    except Exception as e:
        print(f"err benchmark: {e}")

    # 8. Open a store detail drawer
    try:
        # Find first store row in single store section
        store_rows = page.locator("#single-store-container tr.clickable")
        if store_rows.count():
            store_rows.first.scroll_into_view_if_needed()
            time.sleep(0.3)
            store_rows.first.click()
            time.sleep(2)
            drawer = page.locator("#drawerOverlay")
            if drawer.count():
                path = os.path.join(OUTPUT_DIR, "08_store_detail.png")
                drawer.first.screenshot(path=path)
                screenshots["08_store_detail"] = path
    except Exception as e:
        print(f"err drawer: {e}")

    # 9. Dashboard summary (expanded)
    try:
        page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
        time.sleep(3)
        summary = page.locator("#dashboard-summary-card")
        if summary.count():
            # Try to expand
            toggle = page.locator("#summary-toggle-btn")
            if toggle.count():
                toggle.first.click()
                time.sleep(0.5)
            path = os.path.join(OUTPUT_DIR, "09_summary.png")
            page.screenshot(path=path, full_page=False)
            screenshots["09_summary"] = path
    except Exception as e:
        print(f"err summary: {e}")

    browser.close()

print(f"\n=== {len(screenshots)} screenshots saved ===")
for k, v in screenshots.items():
    sz = os.path.getsize(v)
    print(f"  {k}: {sz//1024} KB")
