"""Test GitHub Pages dashboard rendering."""
import time
import os
from playwright.sync_api import sync_playwright

URL = "https://ironegglee.github.io/takeout-dashboard/"
OUT_DIR = r"C:\Users\CYYS\WorkBuddy\2026-06-16-11-25-31\screenshots"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    
    logs = []
    page.on("console", lambda msg: logs.append(f"{msg.type}: {msg.text}"))
    page.on("pageerror", lambda err: logs.append(f"PAGEERROR: {err}"))
    
    page.goto(URL, wait_until="networkidle", timeout=60000)
    time.sleep(5)
    
    print("=== Logs ===")
    for log in logs[:20]:
        print(log)
    
    has_data = page.evaluate("typeof EMBEDDED_DATA !== 'undefined'")
    print(f"\nEMBEDDED_DATA defined: {has_data}")
    
    page.screenshot(path=os.path.join(OUT_DIR, "github_pages_full.png"), full_page=True)
    print(f"Saved: {os.path.join(OUT_DIR, 'github_pages_full.png')}")
    
    browser.close()
