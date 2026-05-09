"""
SharePoint Word Online document extractor via Playwright + Tesseract OCR.

Usage:
    python3 sharepoint-ocr.py <url> [--out output.txt]

Reads auth state from auth-state.json (created by save-auth.py).
Falls back to cookies-fedauth.txt / cookies-rtfa.txt if auth-state.json is absent.

Outputs:
    screenshots/page_NNN.png  (one per page)
    <output.txt>              (concatenated OCR text, default: document-text.txt)
"""

import asyncio
import argparse
import hashlib
import sys
from pathlib import Path

from playwright.async_api import async_playwright
import pytesseract
from PIL import Image


SCREENSHOT_DIR = Path("screenshots")
DEFAULT_OUT = "document-text.txt"
STALL_LIMIT = 4   # consecutive identical frames before stopping


def load_cookie(path: str) -> str:
    return Path(path).read_text().strip()


def img_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def ocr_image(path: Path) -> str:
    img = Image.open(path)
    return pytesseract.image_to_string(img, lang="eng")


async def find_doc_frame(page):
    """Return the frame that contains the Word Online document body."""
    for frame in page.frames:
        try:
            if await frame.query_selector("body[contenteditable]"):
                return frame
        except Exception:
            pass
    return None


async def capture_pages(url: str, fedauth: str, rtfa: str) -> list[Path]:
    SCREENSHOT_DIR.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        auth_state = "auth-state.json" if Path("auth-state.json").exists() else None
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            storage_state=auth_state,
        )

        if not auth_state:
            cookies = []
            for domain in ["uwnetid.sharepoint.com", ".sharepoint.com"]:
                cookies.append({"name": "FedAuth", "value": fedauth, "domain": domain,
                                 "path": "/", "secure": True, "httpOnly": True})
                cookies.append({"name": "rtFa", "value": rtfa, "domain": domain,
                                 "path": "/", "secure": True, "httpOnly": True})
            await context.add_cookies(cookies)

        page = await context.new_page()
        print("Navigating to document...")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(4)

        # Try to find the editable Word frame and give it keyboard focus
        doc_frame = await find_doc_frame(page)
        if doc_frame:
            print("Found editable Word frame.")
            body = await doc_frame.query_selector("body")
            if body:
                await body.click()
        else:
            # Fall back: click in the centre of the document area
            print("No editable frame found; clicking document centre.")
            await page.mouse.click(640, 400)

        await asyncio.sleep(1)

        # Go to the very beginning of the document
        await page.keyboard.press("Control+Home")
        await asyncio.sleep(1.5)

        screenshots: list[Path] = []
        hashes: list[str] = []
        stall_count = 0
        page_num = 0

        print("Capturing pages with Page Down...")
        while True:
            path = SCREENSHOT_DIR / f"page_{page_num:03d}.png"
            await page.screenshot(path=str(path), full_page=False)

            h = img_hash(path)
            print(f"  {path.name}  hash={h[:8]}")

            if h in hashes[-STALL_LIMIT:]:
                stall_count += 1
            else:
                stall_count = 0

            screenshots.append(path)
            hashes.append(h)

            if stall_count >= STALL_LIMIT:
                print("Content stopped changing — reached end of document.")
                screenshots = screenshots[:-STALL_LIMIT]
                break

            await page.keyboard.press("PageDown")
            await asyncio.sleep(1.2)
            page_num += 1

            if page_num > 300:
                print("Hit safety cap of 300 pages.")
                break

        await browser.close()

    # Deduplicate consecutive identical screenshots
    seen: set[str] = set()
    unique: list[Path] = []
    for p in screenshots:
        h = img_hash(p)
        if h not in seen:
            seen.add(h)
            unique.append(p)

    print(f"Captured {len(unique)} unique pages (from {len(screenshots)} total).")
    return unique


def run_ocr(screenshots: list[Path], out_path: str) -> None:
    print("Running OCR...")
    parts = []
    for path in screenshots:
        text = ocr_image(path)
        parts.append(text.strip())
        print(f"  OCR {path.name}: {len(text)} chars")

    full_text = "\n\n--- page break ---\n\n".join(parts)
    Path(out_path).write_text(full_text, encoding="utf-8")
    print(f"\nSaved {len(full_text)} characters to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="SharePoint document URL")
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()

    fedauth = load_cookie("cookies-fedauth.txt") if Path("cookies-fedauth.txt").exists() else ""
    rtfa = load_cookie("cookies-rtfa.txt") if Path("cookies-rtfa.txt").exists() else ""

    screenshots = asyncio.run(capture_pages(args.url, fedauth, rtfa))

    if not screenshots:
        print("No screenshots captured. Check auth-state.json is valid.")
        sys.exit(1)

    run_ocr(screenshots, args.out)


if __name__ == "__main__":
    main()
