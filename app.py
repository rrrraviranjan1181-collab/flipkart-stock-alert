

import re
import requests
from bs4 import BeautifulSoup

PRODUCT_URL = (
    "https://www.flipkart.com/puma-solid-men-polo-neck-white-t-shirt/"
    "p/itm7250ad5444da3?pid=TSHH4D2FGURWBGAS"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

SIZE_PATTERN = re.compile(
    r"^(?:XS|S|M|L|XL|XXL|XXXL|3XL|4XL|5XL|6XL)$",
    re.IGNORECASE,
)


def find_sizes(soup):
    """Find size labels and their corresponding HTML elements."""
    found = {}

    for element in soup.find_all(
        ["a", "button", "div", "span", "li", "label"]
    ):
        size = element.get_text(" ", strip=True).upper()

        if not SIZE_PATTERN.fullmatch(size):
            continue

        # Ignore a container if it contains a smaller element
        # with the same exact size label.
        nested_match = element.find(
            lambda child: (
                child.name in [
                    "a", "button", "div", "span", "li", "label"
                ]
                and child.get_text(" ", strip=True).upper() == size
            )
        )

        if nested_match:
            continue

        found.setdefault(size, element)

    return found


def get_status(element):
    """Inspect the size text and nearby elements."""
    current = element

    for _ in range(4):
        if current is None:
            break

        style = current.get("style", "").lower()
        classes = " ".join(current.get("class", [])).lower()
        combined = style + " " + classes

        # Explicit strike-through.
        if re.search(
            r"text-decoration\s*:[^;]*line-through|"
            r"line-through|strikethrough|strike-through",
            combined,
        ):
            return "OUT OF STOCK", "Strike-through detected"

        # Grey text observed on crossed-out Flipkart sizes.
        color = re.search(
            r"color\s*:\s*#([0-9a-f]{6,8})",
            style,
        )

        if color and color.group(1)[:6] == "707070":
            return "OUT OF STOCK", "Grey text (#707070)"

        # Check explicit disabled indicators.
        if (
            str(current.get("aria-disabled", "")).lower() == "true"
            or current.has_attr("disabled")
        ):
            return "OUT OF STOCK", "Disabled element"

        current = current.parent

    # User's working rule: sizes without the grey/crossed-out
    # indicator are considered available.
    return "AVAILABLE", "No grey/cross-out indicator detected"


def main():
    print("=" * 52)
    print("FLIPKART SIZE STOCK CHECKER")
    print("=" * 52)
    print("URL:", PRODUCT_URL)

    try:
        response = requests.get(
            PRODUCT_URL,
            headers=HEADERS,
            timeout=30,
        )

        print("HTTP status:", response.status_code)

        if response.status_code != 200:
            print("ERROR: Product page could not be loaded.")
            print("Stock results are unavailable.")
            return

        soup = BeautifulSoup(response.text, "html.parser")

        if soup.title:
            print("Page title:", soup.title.get_text(" ", strip=True))

        sizes = find_sizes(soup)

        print("\nSIZE-BY-SIZE RESULTS")
        print("-" * 52)

        if not sizes:
            print("No sizes found in the downloaded HTML.")
            print("The page may require browser-based rendering.")
            return

        available = []
        out_of_stock = []

        for size, element in sizes.items():
            status, reason = get_status(element)
            print(f"{size}: {status} ({reason})")

            if status == "AVAILABLE":
                available.append(size)
            else:
                out_of_stock.append(size)

        print("\nSUMMARY")
        print("-" * 52)
        print("Available:", ", ".join(available) or "None")
        print("Out of stock:", ", ".join(out_of_stock) or "None")
        print("Sizes detected:", len(sizes))

        print("\nNote: This uses the grey/cross-out rule observed")
        print("in your screenshots. Verify on additional products.")

    except requests.RequestException as error:
        print("REQUEST ERROR:", error)
        print("Stock results are unavailable.")

    except Exception as error:
        print("UNEXPECTED ERROR:", repr(error))


if __name__ == "__main__":
    main()
