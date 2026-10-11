

import re
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URL = (
    "https://www.flipkart.com/adidas-solid-men-round-neck-black-t-shirt/"
    "p/itma8b701e39e950?pid=TSHHNNHCKTYHWHGN&marketplace=FLIPKART"
)

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


def print_report(status, evidence, solution):
    print("\n========== FLIPKART MONITOR ==========")
    print("PRODUCT: Adidas Black T-Shirt")
    print("TARGET: Black | Size M")
    print(f"RESULT: {status}")
    print(f"EVIDENCE: {evidence}")
    print(f"NEXT STEP: {solution}")
    print("======================================")
    print("Copy this short report and send it to ChatGPT.")


def main():
    try:
        response = requests.get(URL, headers=HEADERS, timeout=25)
        response.raise_for_status()
    except requests.RequestException as exc:
        print_report(
            "CHECK FAILED",
            f"Could not load Flipkart: {str(exc)[:180]}",
            "Check the URL, network, or possible website blocking, then retry.",
        )
        sys.exit(1)

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = clean(soup.get_text(" ", strip=True))
    lower_text = page_text.lower()

    # Find the actual M size link, not a generic occurrence of letter M.
    m_links = [
        a for a in soup.find_all("a")
        if clean(a.get_text(" ", strip=True)).upper() == "M"
        and "swatchAttr=size" in a.get("href", "")
    ]

    if not m_links:
        print_report(
            "UNKNOWN",
            f"Page loaded (HTTP {response.status_code}), but the M size link "
            "was not found.",
            "Inspect the latest product HTML; Flipkart may have changed its layout.",
        )
        return

    m_link = m_links[0]
    m_html = str(m_link)

    # Observed on this page: unavailable size options have a thin grey
    # horizontal overlay across the size label.
    strike_marker = any(
        re.search(r"height\s*:\s*1px", element.get("style", ""), re.I)
        and re.search(
            r"background-color\s*:\s*(#d6d6d6ff|#d6d6d6)",
            element.get("style", ""),
            re.I,
        )
        for element in m_link.find_all(style=True)
    )

    notify_me = "notify me" in lower_text
    add_to_cart = "add to cart" in lower_text
    buy_now = "buy now" in lower_text

    if strike_marker:
        print_report(
            "LIKELY OUT OF STOCK",
            "Size M contains the grey strike-through overlay seen on "
            "unavailable sizes.",
            "Keep monitoring. Recheck the actual page before purchasing; "
            "this detection relies on Flipkart's current HTML styling.",
        )
        return

    if notify_me and not (add_to_cart or buy_now):
        print_report(
            "LIKELY UNAVAILABLE",
            "The page contains 'Notify Me', with no detected purchase action.",
            "Verify Black and M in a browser. The message may refer to the "
            "currently selected variant.",
        )
        return

    # Do not claim in-stock just because the size link exists.
    print_report(
        "UNKNOWN",
        "The M link exists, but no confirmed availability indicator was found. "
        f"Purchase text found: Add to Cart={add_to_cart}, Buy Now={buy_now}.",
        "Inspect the current variant's purchase state. Do not send an "
        "in-stock alert until availability is confirmed.",
    )


if __name__ == "__main__":
    main()
