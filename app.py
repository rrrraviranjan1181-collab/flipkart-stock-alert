
import re
import sys
import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("""
========== FLIPKART MONITOR REPORT ==========
RESULT: FAILED
PROBLEM: Python package 'beautifulsoup4' is missing.
RESOLUTION:
1. Add beautifulsoup4 to requirements.txt.
2. Re-run GitHub Actions.
=============================================
""")
    sys.exit(1)


URL = (
    "https://www.flipkart.com/adidas-solid-men-round-neck-black-t-shirt/"
    "p/itma8b701e39e950?pid=TSHHNNHCKTYHWHGN&marketplace=FLIPKART"
)

TARGET_COLOR = "BLACK"
TARGET_SIZE = "M"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

SIZES = {"XS", "S", "M", "L", "XL", "XXL"}


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def short(value, limit=180):
    value = clean(str(value))
    return value[:limit] + ("..." if len(value) > limit else "")


def report(lines):
    print("\n========== FLIPKART MONITOR REPORT ==========")
    for line in lines:
        print(line)
    print("=============================================")
    print("Copy the report above and send it to ChatGPT.")


def main():
    result = [
        "PRODUCT: Adidas Black Round Neck T-Shirt",
        f"TARGET VARIANT: {TARGET_COLOR}, size {TARGET_SIZE}",
    ]

    try:
        response = requests.get(URL, headers=HEADERS, timeout=25)
    except requests.RequestException as exc:
        report([
            *result,
            "RESULT: FAILED",
            f"PROBLEM: Website request failed: {short(exc, 220)}",
            "RESOLUTION: Check the internet connection, timeout, or "
            "whether Flipkart is blocking automated requests.",
        ])
        return

    result.append(f"HTTP STATUS: {response.status_code}")

    if response.status_code != 200:
        result.extend([
            "RESULT: PAGE NOT LOADED SUCCESSFULLY",
            "PROBLEM: Flipkart did not return HTTP 200.",
            "RESOLUTION: Check the product URL and retry later. "
            "A 403/429 may indicate blocking or rate limiting.",
        ])
        report(result)
        return

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = clean(soup.get_text(" ", strip=True))
    upper_text = page_text.upper()

    title = soup.title.get_text(" ", strip=True) if soup.title else "Not found"
    result.append(f"PAGE TITLE: {short(title, 150)}")
    result.append(
        "BLACK COLOUR TEXT: "
        + ("FOUND" if TARGET_COLOR in upper_text else "NOT FOUND")
    )

    # Find exact M elements without printing the entire HTML page.
    m_elements = []
    for element in soup.find_all(["a", "button", "div", "span", "li"]):
        if clean(element.get_text(" ", strip=True)).upper() == TARGET_SIZE:
            m_elements.append(element)

    # Identify the nearest ancestor that appears to contain all the size labels.
    selector = None
    for element in m_elements:
        ancestor = element.parent

        for _ in range(5):
            if ancestor is None:
                break

            labels = set()
            for item in ancestor.find_all(
                ["a", "button", "div", "span", "li"], limit=100
            ):
                label = clean(item.get_text(" ", strip=True)).upper()
                if label in SIZES:
                    labels.add(label)

            if {"XS", "S", "M", "L", "XL", "XXL"}.issubset(labels):
                selector = ancestor
                break

            ancestor = ancestor.parent

        if selector is not None:
            break

    if selector:
        labels = sorted({
            clean(item.get_text(" ", strip=True)).upper()
            for item in selector.find_all(
                ["a", "button", "div", "span", "li"], limit=100
            )
            if clean(item.get_text(" ", strip=True)).upper() in SIZES
        })

        result.append("SIZE SELECTOR: FOUND")
        result.append("SIZE LABELS: " + ", ".join(labels))
        result.append(
            "SELECTOR DETAILS: "
            + short({
                "tag": selector.name,
                "class": selector.get("class", []),
                "style": selector.get("style", ""),
            })
        )

        m_control = next(
            (
                item for item in selector.find_all(
                    ["a", "button", "div", "span", "li"]
                )
                if clean(item.get_text(" ", strip=True)).upper() == "M"
            ),
            None,
        )

        if m_control:
            result.append(
                "SIZE M CONTROL: "
                + short({
                    "tag": m_control.name,
                    "class": m_control.get("class", []),
                    "style": m_control.get("style", ""),
                    "aria_disabled": m_control.get("aria-disabled"),
                    "disabled": m_control.has_attr("disabled"),
                    "link": m_control.get("href"),
                })
            )
            result.append(
                "M CONTROL HTML: " + short(str(m_control), 350)
            )
    else:
        result.append("SIZE SELECTOR: NOT RELIABLY IDENTIFIED")
        result.append(
            f"EXACT M TEXT ELEMENTS: {len(m_elements)}"
        )

    # These are page-wide signals only, not proof for Black + M.
    signals = []
    for phrase in (
        "out of stock",
        "sold out",
        "currently unavailable",
        "add to cart",
        "buy now",
        "notify me",
    ):
        if phrase in upper_text:
            signals.append(phrase)

    result.append(
        "PAGE-WIDE STOCK WORDS: "
        + (", ".join(signals) if signals else "No known phrases found")
    )
    result.append("FINAL STOCK STATUS: UNKNOWN")
    result.append(
        "WHY: Page text and size labels alone cannot prove that the "
        "Black + M variant is purchasable."
    )

    if selector:
        result.append(
            "NEXT STEP: Inspect the reported M control and determine "
            "whether variant availability is exposed in the page data."
        )
    else:
        result.append(
            "NEXT STEP: The size selector was not identified. The page "
            "may need browser automation or a different selector."
        )

    result.append(
        "POSSIBLE RESOLUTION: Use browser automation to select Black "
        "and M, then verify the actual availability or purchase state."
    )
    result.append(
        "ALERTS: Telegram stock alerts are not enabled in this diagnostic version."
    )

    report(result)


if __name__ == "__main__":
    main()
