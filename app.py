
import re
import requests
from bs4 import BeautifulSoup

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


def main():
    response = requests.get(URL, headers=HEADERS, timeout=30)
    print("HTTP status:", response.status_code)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = clean(soup.get_text(" ", strip=True))

    print("Page title:", soup.title.get_text(strip=True) if soup.title else "Missing")
    print("Black colour mentioned:", "BLACK" in text.upper())

    print("\n--- SIZE SELECTOR MARKUP ---")
    found = 0

    for element in soup.find_all("div", class_="css-g5y9jx"):
        element_text = clean(element.get_text(" ", strip=True))

        if "XS" in element_text and "XXL" in element_text:
            print(element.prettify()[:12000])
            found += 1

    if not found:
        print("The expected size selector was not found.")

    print("\n--- SIZE M ELEMENTS ---")
    count = 0

    for element in soup.find_all(["a", "button", "div", "span"]):
        if clean(element.get_text(" ", strip=True)) != "M":
            continue

        print({
            "tag": element.name,
            "text": clean(element.get_text(" ", strip=True)),
            "class": element.get("class", []),
            "href": element.get("href"),
            "style": element.get("style"),
            "aria_disabled": element.get("aria-disabled"),
            "disabled": element.has_attr("disabled"),
            "outer_html": str(element)[:1500],
        })

        count += 1
        if count >= 12:
            break

    print("\nInspection complete.")
    print("No stock status has been inferred from size text alone.")


if __name__ == "__main__":
    main()
