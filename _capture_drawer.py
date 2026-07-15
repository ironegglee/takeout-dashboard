"""Capture store detail drawer screenshot."""
import time
import os
from playwright.sync_api import sync_playwright

URL = "https://ironegglee.github.io/takeout-dashboard/"
OUT_DIR = r"C:\Users\CYYS\WorkBuddy\2026-06-16-11-25-31\screenshots"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(URL, wait_until="networkidle", timeout=60000)
    time.sleep(5)
    
    # Scroll to single store section and click a row
    try:
        single_store = page.locator("#single-store-card")
        if single_store.count() > 0:
            single_store.first.scroll_into_view_if_needed()
            time.sleep(1)
            
            store_rows = page.locator("#single-store-container tr.clickable")
            print(f"Store rows found: {store_rows.count()}")
            if store_rows.count() > 0:
                # Click a row that has data (avoid header)
                store_rows.nth(1).click()
                time.sleep(2)
                
                drawer = page.locator("#drawerOverlay")
                if drawer.count() > 0 and drawer.is_visible():
                    path = os.path.join(OUT_DIR, "08_store_detail.png")
                    drawer.first.screenshot(path=path)
                    print(f"✓ 08_store_detail: {os.path.getsize(path)//1024} KB")
                else:
                    print("Drawer not visible after click")
    except Exception as e:
        print(f"error: {e}")
    
    browser.close()
