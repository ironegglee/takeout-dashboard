"""Capture screenshots of the dashboard for the case study document."""
import http.server
import socketserver
import threading
import time
import os
import sys

from playwright.sync_api import sync_playwright

PORT = 8899
DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(DASHBOARD_DIR, "screenshots")
DASHBOARD_URL = f"http://localhost:{PORT}/index.html"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Start HTTP server in background
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)
    def log_message(self, format, *args):
        pass

def start_server():
    with socketserver.TCPServer(("", PORT), QuietHandler) as httpd:
        httpd.serve_forever()

server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()
time.sleep(1)
print(f"Server started on port {PORT}")

def capture_screenshot(page, selector, filename, full_page=False, clip=None):
    """Capture a screenshot of a specific element or full page."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    try:
        if clip:
            page.screenshot(path=filepath, clip=clip, full_page=False)
        elif full_page:
            page.screenshot(path=filepath, full_page=True)
        elif selector:
            el = page.locator(selector)
            el.screenshot(path=filepath)
        else:
            page.screenshot(path=filepath)
        size = os.path.getsize(filepath)
        print(f"  ✓ {filename} ({size//1024} KB)")
        return filepath
    except Exception as e:
        print(f"  ✗ {filename}: {e}")
        return None

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=30000)
    time.sleep(3)  # Let charts render
    
    # Close any open drawers
    try:
        close_btn = page.locator(".drawer-close")
        if close_btn.count() > 0:
            close_btn.first.click()
            time.sleep(0.5)
    except:
        pass
    
    print("\n=== Capturing Screenshots ===\n")
    
    # 1. Full page overview
    capture_screenshot(page, None, "01_dashboard_full.png", full_page=True)
    
    # Wait and let all charts render
    time.sleep(2)
    
    # 2. Channel panel (top section with MP + MT panels)
    try:
        channel_panel = page.locator(".channels-row")
        if channel_panel.count() > 0:
            channel_panel.first.screenshot(path=os.path.join(OUTPUT_DIR, "02_channel_panel.png"))
            print(f"  ✓ 02_channel_panel.png")
    except Exception as e:
        print(f"  ✗ channel_panel: {e}")
    
    # 3. Management ranking section (market/brand + region/area manager + single store)
    try:
        # Scroll to ranking section
        ranking_section = page.locator("#mgmt-ranking")
        if ranking_section.count() > 0:
            ranking_section.first.scroll_into_view_if_needed()
            time.sleep(1)
            # Take a full screenshot of the ranking area
            page.screenshot(path=os.path.join(OUTPUT_DIR, "03_management_ranking.png"), full_page=False)
            print(f"  ✓ 03_management_ranking.png")
    except Exception as e:
        print(f"  ✗ management_ranking: {e}")
    
    # 4. Alert panel + benchmark/warning stores
    try:
        alerts_panel = page.locator("#alerts-panel")
        if alerts_panel.count() > 0:
            alerts_panel.first.scroll_into_view_if_needed()
            time.sleep(0.5)
            alerts_panel.first.screenshot(path=os.path.join(OUTPUT_DIR, "04_alerts_benchmark.png"))
            print(f"  ✓ 04_alerts_benchmark.png")
    except Exception as e:
        print(f"  ✗ alerts: {e}")
    
    # 5. Click a store to open detail drawer
    try:
        # Find a clickable store row and click it
        store_row = page.locator("tr.store-row, tr.clickable").first
        if store_row.count() > 0:
            store_row.click()
            time.sleep(2)  # Wait for drawer animation
            drawer = page.locator(".drawer")
            if drawer.count() > 0:
                drawer.first.screenshot(path=os.path.join(OUTPUT_DIR, "05_store_detail_drawer.png"))
                print(f"  ✓ 05_store_detail_drawer.png")
    except Exception as e:
        print(f"  ✗ store_detail: {e}")
    
    # 6. Take a closer screenshot of the single store data section
    try:
        single_store = page.locator("#single-store-card")
        if single_store.count() > 0:
            single_store.first.scroll_into_view_if_needed()
            time.sleep(0.5)
            single_store.first.screenshot(path=os.path.join(OUTPUT_DIR, "06_single_store_data.png"))
            print(f"  ✓ 06_single_store_data.png")
    except Exception as e:
        print(f"  ✗ single_store: {e}")
    
    # 7. Benchmark/warning stores detail
    try:
        page.locator("body").scroll_into_view_if_needed()
        time.sleep(0.5)
        benchmark = page.locator("#benchmark-panel")
        if benchmark.count() > 0:
            benchmark.first.scroll_into_view_if_needed()
            time.sleep(0.3)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "07_benchmark_warning.png"), full_page=False)
            print(f"  ✓ 07_benchmark_warning.png")
    except Exception as e:
        print(f"  ✗ benchmark: {e}")
    
    browser.close()

print(f"\n=== Done! Screenshots saved to {OUTPUT_DIR} ===\n")
