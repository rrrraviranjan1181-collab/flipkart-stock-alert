
import re
import sys
import requests
from bs4 import BeautifulSoup

URL = (
    "https://www.flipkart.com/adidas-solid-men-round-neck-black-t-shirt/"
    "p/itma8b701e39e950?pid=TSHHNNHCKTYHWHGN&marketplace=FLIPKART"
)

SIZES = ["XS", "S", "M", "L", "XL", "XXL"]

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


def is_struck_out(element):
    """Look for the grey strike-through observed on unavailable sizes."""
    for node in [element, *element.find_all(True)]:
        style = node.get("style", "")

        grey_line = (
            re.search(r"height\s*:\s*1px", style, re.I)
            and re.search(
                r"background-color\s*:\s*(#d6d6d6ff|#d6d6d6)",
                style,
                re.I,
            )
        )

        line_through = re.search(
            r"text-decoration(?:-line)?\s*:\s*[^;]*line-through",
            style,
            re.I,
        )

        if grey_line or line_through:
            return True

    return False


def main():
    try:
        response = requests.get(URL, headers=HEADERS, timeout=25)
        response.raise_for_status()
    except requests.RequestException as exc:
        print("\n========== STOCK CHECK REPORT ==========")
        print("RESULT: CHECK FAILED")
        print("ERROR:", clean(str(exc))[:200])
        print("FIX: Check the URL, network, or possible website blocking.")
        print("========================================")
        sys.exit(1)

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = clean(soup.get_text(" ", strip=True)).lower()

    # Find size links that look like product variant selectors.
    links_by_size = {size: [] for size in SIZES}

    for link in soup.find_all("a", href=True):
        label = clean(link.get_text(" ", strip=True)).upper()
        href = link.get("href", "").lower()

        if label in SIZES and (
            "swatchattr=" in href or "pid=" in href
        ):
            links_by_size[label].append(link)

    print("\n========== STOCK CHECK REPORT ==========")
    print("PRODUCT: Adidas Black Round Neck T-Shirt")
    print("PAGE STATUS: Loaded successfully")
    print("COLOUR: BLACK")
    print("----------------------------------------")

    found = 0
    for size in SIZES:
        links = links_by_size[size]

        if not links:
            print(f"{size:>3}: UNKNOWN - size selector not found")
            continue

        found += 1
        # Prefer the link containing a product variant identifier.
        link = max(
            links,
            key=lambda item: len(item.get("href", "")),
        )

        if is_struck_out(link):
            print(f"{size:>3}: LIKELY OUT OF STOCK - strike-through detected")
        else:
            print(
                f"{size:>3}: UNKNOWN - no strike-through detected; "
                "stock not confirmed"
            )

    print("----------------------------------------")
    print(f"SIZES FOUND: {found}/{len(SIZES)}")

    if found == len(SIZES):
        print("CHECK: All six size selectors were found.")
    else:
        print("CHECK: Some sizes could not be identified in the HTML.")

    if "notify me" in page_text:
        print("PAGE CLUE: 'Notify Me' appears on the page.")
        print("NOTE: This may refer only to the currently selected variant.")

    print("IN-STOCK CONFIRMATION: Not yet implemented.")
    print("========================================")
    print("Copy this report and send it to ChatGPT.")


if __name__ == "__main__":
    main()
