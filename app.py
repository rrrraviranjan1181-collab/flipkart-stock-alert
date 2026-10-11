
import json
import re
import requests
from bs4 import BeautifulSoup

PRODUCT_URL = (
    "https://www.flipkart.com/puma-military-camouflage-men-crew-neck-black-t-shirt/"
    "p/itm5336dfb62fa01?pid=TSHHP6ADWYWKBJV2"
)

SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}


def element_info(element):
    """Collect evidence from an element and its nearby parent elements."""
    evidence = []

    current = element

    # Inspect the size element and a few ancestors, since the disabled
    # state may be attached to a wrapper rather than the text itself.
    for _ in range(4):
        if current is None:
            break

        classes = " ".join(current.get("class", []))
        style = current.get("style", "")
        aria_disabled = current.get("aria-disabled", "")
        disabled = current.has_attr("disabled")
        data_values = " ".join(
            str(value)
            for key, value in current.attrs.items()
            if key.startswith("data-")
        )

        combined = " ".join(
            [classes, style, data_values, str(aria_disabled)]
        ).lower()

        if classes:
            evidence.append("class=" + classes)
        if style:
            evidence.append("style=" + style)
        if aria_disabled:
            evidence.append("aria-disabled=" + str(aria_disabled))
        if disabled:
            evidence.append("disabled attribute")
        if data_values:
            evidence.append("data attributes=" + data_values[:180])

        current = current.parent

    return " | ".join(evidence), combined if "combined" in locals() else ""


def classify_size(element):
    """Return a status only when the HTML gives a useful indication."""
    current = element
    combined = []

    for _ in range(4):
        if current is None:
            break

        classes = " ".join(current.get("class", []))
        style = current.get("style", "")
        aria_disabled = str(current.get("aria-disabled", ""))
        data_text = " ".join(
            str(value)
            for key, value in current.attrs.items()
            if key.startswith("data-")
        )

        combined.append(
            f"{classes} {style} {aria_disabled} {data_text}".lower()
        )
        current = current.parent

    text = " ".join(combined)

    # Explicit disabled/unavailable signals.
    if re.search(
        r"aria-disabled\s*=\s*['\"]?true|"
        r"disabled|out.of.stock|outofstock|unavailable|sold.out",
        text,
    ):
        return "OUT OF STOCK"

    # Explicit strike-through styling.
    if re.search(r"text-decoration[^;]*line-through", text):
        return "OUT OF STOCK"

    # Some pages use a pseudo-element or class to draw the diagonal line.
    # Do not interpret generic grey styling alone as proof.
    if re.search(r"line-through|strikethrough|strike-through", text):
        return "OUT OF STOCK"

    # A size label alone is not sufficient evidence of availability.
    return "UNKNOWN"


def find_size_elements(soup):
    """Find the smallest HTML elements whose text exactly matches a size."""
    results = {}

    for size in SIZES:
        matches = []

        for element in soup.find_all(
            ["a", "button", "div", "span", "li", "label"]
        ):
            if element.get_text(" ", strip=True) != size:
                continue

            # Avoid choosing large containers that include other size labels.
            child_has_same_size = any(
                child.get_text(" ", strip=True) == size
                for child in element.find_all(
                    ["a", "button", "div", "span", "li", "label"]
                )
            )
            if child_has_same_size:
                continue

            matches.append(element)

        if matches:
            # Prefer interactive elements over plain text wrappers.
            matches.sort(
                key=lambda element: (
                    0 if element.name in ("button", "a", "label") else 1
                )
            )
            results[size] = matches[0]

    return results


def main():
    print("=" * 52)
    print("FLIPKART SIZE STOCK CHECKER")
    print("=" * 52)
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
            print("RESULT: UNKNOWN — product page could not be loaded.")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title
            else "Title not found"
        )
        print("Page title:", title)

        page_text = soup.get_text(" ", strip=True).lower()

        # Basic page-level diagnostic only; this is not a size-specific test.
        print("\nPAGE DIAGNOSTICS")
        for phrase in ["Add to cart", "Buy now", "Notify Me", "Out of Stock"]:
            print(
                f"{phrase}: "
                f"{'Found' if phrase.lower() in page_text else 'Not found'}"
            )

        size_elements = find_size_elements(soup)

        print("\nSIZE-BY-SIZE RESULTS")
        print("-" * 52)

        for size in SIZES:
            element = size_elements.get(size)

            if element is None:
                print(f"{size}: UNKNOWN — size label not found in HTML")
                continue

            status = classify_size(element)
            evidence, _ = element_info(element)

            print(f"{size}: {status}")
            print("  HTML tag:", element.name)
            print("  Evidence:", evidence[:500] if evidence else "No useful attributes")

        print("\nIMPORTANT")
        print("-" * 52)
        print("UNKNOWN means the downloaded HTML did not prove the status.")
        print("A size label or Add to cart text does not prove every size is available.")
        print("If the strike-through is drawn by browser-only CSS, this script")
        print("may need browser automation to verify the actual selected size.")

    except requests.RequestException as error:
        print("REQUEST ERROR:", error)
        print("All sizes: UNKNOWN")

    except Exception as error:
        print("UNEXPECTED ERROR:", repr(error))
        print("All sizes: UNKNOWN")


if __name__ == "__main__":
    main()
