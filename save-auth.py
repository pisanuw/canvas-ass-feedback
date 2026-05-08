"""
Open a browser window, let you log in manually, then save the full session
(cookies + storage) to auth-state.json for use by sharepoint-ocr.py.

Usage:
    python3 save-auth.py <url>
"""

import asyncio
import sys
from playwright.async_api import async_playwright


async def main(url: str) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(url)

        print("\nBrowser opened. Complete the full login (including Google auth).")
        print("Wait until the DOCUMENT TEXT is visible in the browser.\n")

        while True:
            input(">>> Press Enter to check current state (repeat until document is loaded): ")

            current_url = page.url
            print(f"Current URL: {current_url}")

            # Take a debug screenshot
            await page.screenshot(path="debug-current.png")
            print("Screenshot saved to debug-current.png — check it to see what the browser shows.")

            # Report which relevant cookies are present
            all_cookies = await context.cookies()
            sp_cookies = {c["name"] for c in all_cookies if "sharepoint" in c["domain"]}
            print(f"SharePoint cookies present: {sp_cookies or 'none yet'}")

            if "FedAuth" in sp_cookies:
                print("\nFedAuth found — document session is active. Saving auth state...")
                await context.storage_state(path="auth-state.json")
                print("Saved to auth-state.json")
                break
            else:
                print("FedAuth not found yet — finish logging in and press Enter again.\n")

        await browser.close()


asyncio.run(main(sys.argv[1]))
