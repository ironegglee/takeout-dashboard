"""Capture screenshots from GitHub Pages dashboard for business case Word doc."""
import time
import os
from playwright.sync_api import sync_playwright

URL = "https://ironegglee.github.io/takeout-dashboard/"
OUT_DIR = r"C:\Users\CYYS\WorkBuddy\2026-06-16-11-25-31\screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(URL, wait_until="networkidle", timeout=60000)
    time.sleep(5)
    
    screenshots = {}

    def save_screenshot(name, clip=None, element=None, full_page=False):
        path = os.path.join(OUT_DIR, name + ".png")
        try:
            if element:
                element.screenshot(path=path)
            elif clip:
                page.screenshot(path=path, clip=clip)
            elif full_page:
                page.screenshot(path=path, full_page=True)
            else:
                page.screenshot(path=path)
            screenshots[name] = path
            print(f"✓ {name}: {os.path.getsize(path)//1024} KB")
            return path
        except Exception as e:
            print(f"✗ {name}: {e}")
            return None

    # 1. Full overview (already captured)
    save_screenshot("01_full_overview", full_page=True)

    # 2. Top metrics area (after page loads, scroll to top)
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)
    # Top metrics is between filter bar and channel panels
    save_screenshot("02_top_metrics", clip={"x": 0, "y": 160, "width": 1440, "height": 170})

    # 3. Channel panels
    save_screenshot("03_channel_panels", clip={"x": 0, "y": 330, "width": 1440, "height": 420})

    # 4. Management ranking area (full width, all tables)
    page.evaluate("window.scrollTo(0, 750)")
    time.sleep(0.5)
    save_screenshot("04_mgmt_ranking", clip={"x": 0, "y": 750, "width": 1440, "height": 700})

    # 5. Single store data close-up
    try:
        single_store = page.locator("#single-store-card")
        if single_store.count() > 0:
            single_store.first.scroll_into_view_if_needed()
            time.sleep(0.5)
            save_screenshot("05_single_store", element=single_store.first)
    except Exception as e:
        print(f"single store error: {e}")

    # 6. Alert panel
    try:
        alert_section = page.locator("#alert-section")
        if alert_section.count() > 0:
            alert_section.first.scroll_into_view_if_needed()
            time.sleep(0.5)
            save_screenshot("06_alert_panel", element=alert_section.first)
    except Exception as e:
        print(f"alert error: {e}")

    # 7. Benchmark + warning stores
    try:
        store_rank = page.locator("#store-rank-section")
        if store_rank.count() > 0:
            store_rank.first.scroll_into_view_if_needed()
            time.sleep(0.5)
            save_screenshot("07_benchmark_stores", element=store_rank.first)
    except Exception as e:
        print(f"benchmark error: {e}")

    # 8. Open store detail drawer
    try:
        # Close any existing drawer
        close_btn = page.locator(".drawer-close")
        if close_btn.count() > 0:
            close_btn.first.click()
            time.sleep(0.5)
        
        # Click a store in the single store table
        store_rows = page.locator("#single-store-container tr.clickable")
        if store_rows.count() > 0:
            store_rows.first.scroll_into_view_if_needed()
            time.sleep(0.3)
            store_rows.first.click()
            time.sleep(2)
            drawer = page.locator("#drawerOverlay")
            if drawer.count() > 0:
                save_screenshot("08_store_detail", element=drawer.first)
    except Exception as e:
        print(f"drawer error: {e}")

    # 9. Dashboard summary card (if visible)
    try:
        summary_card = page.locator("#dashboard-summary-card")
        if summary_card.count() > 0:
            summary_card.first.scroll_into_view_if_needed()
            time.sleep(0.5)
            save_screenshot("09_summary_card", element=summary_card.first)
    except Exception as e:
        print(f"summary error: {e}")

    # 10. Filter bar
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)
    save_screenshot("10_filter_bar", clip={"x": 0, "y": 60, "width": 1440, "height": 100})

    browser.close()

print(f"\n=== Captured {len(screenshots)} screenshots ===")
for name, path in screenshots.items():
    print(f"  {name}")
