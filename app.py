


import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

PRODUCT_URL = (
    "https://www.flipkart.com/"
    "adidas-solid-men-round-neck-black-t-shirt/"
    "p/itma8b701e39e950"
    "?pid=TSHHNNHCKTYHWHGN&marketplace=FLIPKART"
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

session = requests.Session()
session.headers.update(HEADERS)


def fetch(url):
    response = session.get(url, timeout=25)
    response.raise_for_status()

    if "captcha" in response.url.lower():
        raise RuntimeError("Flipkart CAPTCHA blocked the request")

    soup = BeautifulSoup(response.text, "html.parser")

    if not soup.find("body"):
        raise RuntimeError("Page HTML is incomplete")

    return soup


def clean_text(element):
    return " ".join(element.stripped_strings).strip()


def get_colour_name(soup, url):
    # First try the product's selected-colour text.
    text = soup.get_text(" ", strip=True)

    match = re.search(
        r"Selected Color:\s*([A-Z][A-Z /_-]{1,35})",
        text,
        re.IGNORECASE,
    )
    if match:
        value = match.group(1).strip()
        value = re.split(
            r"\s+(?:Select Size|Size Chart|Selected Size)\b",
            value,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()
        if value:
            return value.upper()

    # Then use the colour in the page title.
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    match = re.search(
        r"\b(Black|White|Red|Blue|Pink|Grey|Gray|Green|"
        r"Yellow|Beige|Brown|Orange|Purple|Maroon|Navy)\b",
        title,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).upper()

    # Finally try the URL slug.
    slug = urlparse(url).path.lower()
    for colour in [
        "black", "white", "red", "blue", "pink", "grey",
        "gray", "green", "yellow", "beige", "brown",
        "orange", "purple", "maroon", "navy",
    ]:
        if re.search(rf"-{colour}-t-shirt", slug):
            return colour.upper()

    return "COLOUR NOT IDENTIFIED"


def is_gray_strike_overlay(size_link):
    """
    Detect a thin, gray, horizontal overlay inside a size option.
    Supports inline styles and common gray colour formats.
    """
    gray_pattern = re.compile(
        r"(#(?:ddd|ddd{1,3}|ccc|ccc{1,3}|"
        r"e0e0e0|d3d3d3|c0c0c0|bdbdbd)\b|"
        r"rgb\(\s*(?:19[0-9]|2[0-5][0-9])\s*,\s*"
        r"(?:19[0-9]|2[0-5][0-9])\s*,\s*"
        r"(?:19[0-9]|2[0-5][0-9])\s*\))",
        re.IGNORECASE,
    )

    for element in [size_link] + size_link.find_all(True):
        style = element.get("style", "").replace(" ", "").lower()

        # Thin horizontal line: width is full or nearly full,
        # and height is approximately 1–3 pixels.
        thin_line = bool(
            re.search(r"height:\s*[123]px", style)
            and (
                "width:100%" in style
                or "width:100.0%" in style
            )
        )

        gray_background = bool(
            re.search(r"background(?:-color)?:", style)
            and gray_pattern.search(style)
        )

        # Flipkart may put the gray colour on a parent
        # and the thin-line dimensions on a child.
        if thin_line and gray_background:
            return True

        if thin_line:
            parent = element.parent
            for _ in range(2):
                if not parent or not getattr(parent, "get", None):
                    break
                parent_style = (
                    parent.get("style", "").replace(" ", "").lower()
                )
                if (
                    re.search(r"background(?:-color)?:", parent_style)
                    and gray_pattern.search(parent_style)
                ):
                    return True
                parent = parent.parent

    return False


def find_size_links(soup):
    found = {}

    for link in soup.find_all("a", href=True):
        label = clean_text(link).upper()

        if label not in SIZES:
            continue

        # Prefer actual size-variant links, not unrelated text.
        href = link["href"]
        query = parse_qs(urlparse(href).query)

        if "pid" not in query and "swatchAttr" not in query:
            continue

        found[label] = link

    return found


def find_colour_links(soup, current_url):
    found = {}

    for link in soup.find_all("a", href=True):
        href = urljoin(current_url, link["href"])
        query = parse_qs(urlparse(href).query)

        swatch = query.get("swatchAttr", [""])[0].lower()
        if swatch not in ("colour", "color"):
            continue

        # Exclude size links.
        if clean_text(link).upper() in SIZES:
            continue

        # Prefer the product's colour swatch link.
        label = (
            link.get("title")
            or link.get("aria-label")
            or link.get("data-testid")
            or ""
        )

        if not label:
            image = link.find("img")
            if image:
                label = image.get("alt", "") or image.get("title", "")

        label = label.strip() or f"COLOUR VARIANT {len(found) + 1}"
        found[href] = label

    return found


def make_report(url):
    soup = fetch(url)
    colour = get_colour_name(soup, url)
    size_links = find_size_links(soup)

    if not size_links:
        raise RuntimeError(
            f"No size variant links found for {colour}. "
            "Flipkart may have changed its HTML."
        )

    result = {}

    for size in SIZES:
        link = size_links.get(size)

        if link is None:
            result[size] = "DETECTION ERROR"
            continue

        if is_gray_strike_overlay(link):
            result[size] = "OUT OF STOCK"
        else:
            result[size] = "IN STOCK"

    return colour, result, soup


def main():
    print("\n========== FLIPKART STOCK REPORT ==========")
    print("PRODUCT: Adidas Solid Men's Round Neck T-Shirt")
    print("RULE: Gray strike-through overlay = OUT OF STOCK")
    print("===========================================\n")

    try:
        base_colour, base_result, base_soup = make_report(PRODUCT_URL)
    except Exception as error:
        print("BASE PAGE ERROR:", error)
        print("Could not safely inspect the product page.")
        return

    colour_pages = {PRODUCT_URL: base_colour}

    for url, label in find_colour_links(base_soup, PRODUCT_URL).items():
        colour_pages[url] = label

    # Visit each discovered colour variant.
    all_results = {}
    visited = set()

    for url, label in colour_pages.items():
        if url in visited:
            continue
        visited.add(url)

        try:
            colour, sizes, _ = (
                (base_colour, base_result, base_soup)
                if url == PRODUCT_URL
                else make_report(url)
            )

            # Use the page's actual colour label when identifiable.
            if colour == "COLOUR NOT IDENTIFIED":
                colour = label.upper()

            all_results[colour] = sizes

            print(f"\nCOLOUR: {colour}")
            for size in SIZES:
                print(f"{size:3}: {sizes.get(size, 'DETECTION ERROR')}")

        except Exception as error:
            print(f"\nCOLOUR: {label.upper()}")
            print("DETECTION ERROR:", error)
            all_results[label.upper()] = {
                size: "DETECTION ERROR" for size in SIZES
            }

        time.sleep(1)

    print("\n=============== SUMMARY ===================")
    print("Colours discovered:", len(colour_pages))
    for colour, sizes in all_results.items():
        available = [
            size for size, status in sizes.items()
            if status == "IN STOCK"
        ]
        unavailable = [
            size for size, status in sizes.items()
            if status == "OUT OF STOCK"
        ]
        errors = [
            size for size, status in sizes.items()
            if status == "DETECTION ERROR"
        ]

        print(f"\n{colour}")
        print("IN STOCK:", ", ".join(available) or "None detected")
        print("OUT OF STOCK:", ", ".join(unavailable) or "None detected")
        if errors:
            print("DETECTION ERRORS:", ", ".join(errors))

    print("\n===========================================")


if __name__ == "__main__":
    main()
