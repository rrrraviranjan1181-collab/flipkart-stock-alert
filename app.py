
import os
import re
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

PRODUCT_URL = os.getenv(
    "PRODUCT_URL",
    "https://www.flipkart.com/adidas-solid-men-round-neck-black-t-shirt/p/itma8b701e39e950?pid=TSHHNNHCKTYHWHGN&marketplace=FLIPKART"
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

            # Locate the size selector, then try its exact M option.
            selector = page.get_by_text(
                re.compile(r"^\s*Select Size\s*$", re.I)
            ).first

            try:
                await selector.wait_for(timeout=5000)
                size_option = selector.locator(
                    f"xpath=following::*[normalize-space()='{SIZE}'][1]"
                )
                await size_option.click(timeout=5000)
                await page.wait_for_timeout(1500)
                print(f"Clicked size option: {SIZE}")
            except Exception as error:
                print("SIZE SELECTION NOT CONFIRMED:", str(error))

            body = await page.locator("body").inner_text()
            print("\nPAGE TEXT AFTER SIZE TEST:\n")
            print(body[:7000])

            # Never infer size-specific stock from generic page text.
            print("\nRESULT: SIZE-SPECIFIC STATUS NOT YET VERIFIED.")
            print("Inspect the page text above for the selected size,")
            print("availability message, and purchase button.")

        except Exception as error:
            print("PAGE READ FAILED:", str(error))
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
