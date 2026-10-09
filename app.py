
import os
import asyncio
from playwright.async_api import async_playwright

URL = os.getenv(
    "PRODUCT_URL",
    "https://www.flipkart.com/adidas-solid-men-round-neck-black-t-shirt/p/itma8b701e39e950?pid=TSHHNNHCKTYHWHGN&marketplace=FLIPKART"
)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="en-IN")

        try:
            response = await page.goto(
                URL, wait_until="domcontentloaded", timeout=45000
            )
            await page.wait_for_timeout(4000)

            print("HTTP:", response.status if response else "unknown")
            print("TITLE:", await page.title())

            # Inspect exact-M elements and their surrounding markup.
            items = await page.locator("body *").evaluate_all("""
                els => els
                  .filter(e => e.children.length === 0 &&
                    e.textContent.trim() === 'M')
                  .filter(e => {
                    const r = e.getBoundingClientRect();
                    const s = getComputedStyle(e);
                    return r.width > 0 && r.height > 0 &&
                      s.visibility !== 'hidden' && s.display !== 'none';
                  })
                  .slice(0, 20)
                  .map(e => ({
                    tag: e.tagName,
                    text: e.textContent.trim(),
                    role: e.getAttribute('role'),
                    ariaLabel: e.getAttribute('aria-label'),
                    ariaSelected: e.getAttribute('aria-selected'),
                    ariaPressed: e.getAttribute('aria-pressed'),
                    disabled: e.getAttribute('disabled'),
                    className: String(e.className).slice(0, 180),
                    parent: e.parentElement
                      ? e.parentElement.outerHTML.slice(0, 700)
                      : ''
                  }))
            """)

            print("EXACT M ELEMENTS:", len(items))
            for i, item in enumerate(items, 1):
                print(f"\\nCANDIDATE {i}: {item}")

            print("\\nPAGE TEXT:")
            print((await page.locator("body").inner_text())[:2500])

        except Exception as exc:
            print("ERROR:", repr(exc))
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
