
import os
import re
import requests
from bs4 import BeautifulSoup

PRODUCT_URL = (
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


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def main():
    print("Checking Flipkart product...")
    print(f"Target colour: {TARGET_COLOR}")
    print(f"Target size: {TARGET_SIZE}")
    print(f"URL: {PRODUCT_URL}")

    try:
        response = requests.get(
            PRODUCT_URL,
            headers=HEADERS,
            timeout=30,
        )
        print(f"HTTP status: {response.status_code}")
        response.raise_for_status()
    except requests.RequestException as exc:
        print("RESULT: UNKNOWN")
        print(f"Reason: Request failed: {exc}")
        raise SystemExit(1)

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = clean(soup.get_text(" ", strip=True))

    # Save basic diagnostic information in the Actions log.
    print(f"Page title: {clean(soup.title.get_text()) if soup.title else 'Not found'}")
    print(f"Page text length: {len(page_text)}")

    if len(page_text) < 300:
        print("RESULT: UNKNOWN")
        print("Reason: The returned page is too short to verify product details.")
        raise SystemExit(0)

    # Look for product data embedded in the page.
    color_found = TARGET_COLOR in page_text.upper()
    size_found = bool(
        re.search(r"(?<![A-Z0-9])M(?![A-Z0-9])", page_text.upper())
    )

    print(f"Black colour mentioned on page: {color_found}")
    print(f"Size M mentioned on page: {size_found}")

    # Find size-related visible elements for diagnosis.
    candidates = []
    for element in soup.find_all(
        ["button", "div", "span", "a", "li"],
        limit=5000,
    ):
        text = clean(element.get_text(" ", strip=True))
        if text == TARGET_SIZE:
            parent = element.parent
            parent_text = clean(parent.get_text(" ", strip=True)) if parent else ""
            candidates.append({
                "tag": element.name,
                "class": " ".join(element.get("class", [])),
                "aria_label": element.get("aria-label", ""),
                "role": element.get("role", ""),
                "parent_tag": parent.name if parent else "",
                "parent_class": (
                    " ".join(parent.get("class", [])) if parent else ""
                ),
                "parent_text": parent_text[:120],
            })

    print("VISIBLE SIZE CANDIDATES:")
    if candidates:
        for index, candidate in enumerate(candidates[:20], start=1):
            print(f"{index}. {candidate}")
    else:
        print("No exact M text elements found.")

    # Never infer exact variant availability from generic product-page text.
    # Flipkart can show generic stock messages that do not correspond to M.
    print("RESULT: UNKNOWN")
    print(
        "Reason: The page was loaded, but exact Black + M availability "
        "has not yet been verified."
    )
    print(
        "Next step: Inspect the VISIBLE SIZE CANDIDATES output to identify "
        "the actual selectable size control."
    )


if __name__ == "__main__":
    main()
