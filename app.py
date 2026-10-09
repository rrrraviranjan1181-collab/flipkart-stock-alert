
import os
import re
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

PRODUCT_URL = os.getenv(
    "PRODUCT_URL",
    "https://dl.flipkart.com/s/kVLy0huuuN"
)
SIZE = os.getenv("SIZE_LABEL", "M")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="en-IN")

        try:
            response = await page.goto(
                PRODUCT_URL,
                wait_until="domcontentloaded",
                timeout=45000
            )
            await page.wait_for_timeout(3000)

            print("Time:", datetime.now().isoformat())
            print("HTTP:", response.status if response else "unknown")
            print("Page:", await page.title())

            body = await page.locator("body").inner_text()
            print("\nPage text preview:\n", body[:5000])

            if re.search(
                r"captcha|verify you are human|access denied",
                body,
                re.I
            ):
                print("\nRESULT: BLOCKED - manual verification needed.")
            elif re.search(
                r"sold out|out of stock|currently unavailable",
                body,
                re.I
            ):
                print("\nRESULT: Possible unavailable state.")
            else:
                print(
                    f"\nRESULT: UNKNOWN. "
                    f"Size {SIZE} availability is not verified."
                )

        except Exception as error:
            print("PAGE READ FAILED:", str(error))
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
