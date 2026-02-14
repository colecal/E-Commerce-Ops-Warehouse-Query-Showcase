"""Optional: capture UI screenshots using Playwright.

Prereqs:
  pip install playwright
  playwright install chromium

Requires the app to be running locally at http://localhost:8000.
"""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

OUT = Path(__file__).resolve().parents[1] / "docs" / "assets"


async def main():
    OUT.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://localhost:8000", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(OUT / "ui-home.png"), full_page=True)

        # click first query card
        await page.click(".qcard")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(OUT / "ui-results.png"), full_page=True)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
