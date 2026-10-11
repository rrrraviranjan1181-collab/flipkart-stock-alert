
import re
import requests
from bs4 import BeautifulSoup

    PRODUCT_URL = ("https://www.flipkart.com/puma-solid-men-polo-neck-white-t-shirt/p/itm7250ad5444da3?pid=TSHH4D2FGURWBGAS")


SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


def get_size_elements(soup):
    """Find the smallest element containing each exact size label."""
    found = {}

    for size in SIZES:
        candidates = []

        for element in soup.find_all(
            ["a", "button", "div", "span", "li", "label"]
        ):
            if element.get_text(" ", strip=True) != size:
                continue

            # Skip containers that contain another matching size element.
            if element.find(
                lambda child: (
                    child.name in [
                        "a", "button", "div", "span", "li", "label"
                    ]
                    and child.get_text(" ", strip=True) == size
                )
            ):
                continue

            candidates.append(element)

        if candidates:
            # Prefer the size text element carrying the actual color.
            candidates.sort(
                key=lambda e: (
                    0 if re.search(
                        r"color\s*:",
                        e.get("style", ""),
                        re.IGNORECASE,
                    ) else 1,
                    len(str(e)),
                )
            )
            found[size] = candidates[0]

    return found


def inspect_size(element):
    """Inspect the size element and its ancestors for stock indicators."""
    current = element

    for _ in range(4):
        if current is None:
            break

        style = current.get("style", "").lower()
        classes = " ".join(current.get("class", [])).lower()
        aria_disabled = str(
            current.get("aria-disabled", "")
        ).lower()

        # Explicit unavailable state.
        if aria_disabled == "true" or current.has_attr("disabled"):
            return "OUT OF STOCK", "Disabled HTML control"

        # Explicit strike-through styling.
        if re.search(
            r"text-decoration\s*:[^;]*line-through|"
            r"line-through|strikethrough|strike-through",
            style + " " + classes,
        ):
            return "OUT OF STOCK", "Strike-through indicator"

        # Color used by the grey crossed-out sizes in your observed HTML.
        color = re.search(
            r"color\s*:\s*#([0-9a-f]{6,8})",
            style,
        )

        if color:
            hex_color = color.group(1)[:6]

            if hex_color == "707070":
                return "OUT OF STOCK", "Grey size text (#707070)"

        current = current.parent

    return "UNKNOWN", "No recognised stock indicator"


def main():
    print("=" * 50)
    print("FLIPKART SIZE STOCK CHECKER")
    print("=" * 50)
    print("Product: Puma Military Camouflage Black T-shirt")
    print("URL:", PRODUCT_URL)
    print()

    try:
        response = requests.get(
            PRODUCT_URL,
            headers=HEADERS,
            timeout=30,
        )

        print("HTTP status:", response.status_code)

        if response.status_code != 200:
            print("ERROR: Could not load product page.")
            print("Stock status: UNKNOWN")
            return

        soup = BeautifulSoup(response.text, "html.parser")

        if soup.title:
            print("Page title:", soup.title.get_text(" ", strip=True))

        size_elements = get_size_elements(soup)

        print("\nSIZE-BY-SIZE RESULTS")
        print("-" * 50)

        available = []
        out_of_stock = []
        unknown = []

        for size in SIZES:
            element = size_elements.get(size)

            if element is None:
                status = "UNKNOWN"
                reason = "Size label not found"
            else:
                status, reason = inspect_size(element)

            print(f"{size}: {status} ({reason})")

            if status == "AVAILABLE":
                available.append(size)
            elif status == "OUT OF STOCK":
                out_of_stock.append(size)
            else:
                unknown.append(size)

        print("\nSUMMARY")
        print("-" * 50)
        print(
            "Available:",
            ", ".join(available) if available else "None confirmed",
        )
        print(
            "Out of stock:",
            ", ".join(out_of_stock) if out_of_stock else "None detected",
        )
        print(
            "Unknown:",
            ", ".join(unknown) if unknown else "None",
        )

        print("\nNote: A size is marked available only when a")
        print("positive availability indicator is implemented and verified.")

    except requests.RequestException as error:
        print("REQUEST ERROR:", error)
        print("Stock status: UNKNOWN")

    except Exception as error:
        print("UNEXPECTED ERROR:", repr(error))
        print("Stock status: UNKNOWN")


if __name__ == "__main__":
    main()
