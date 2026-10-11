
import re
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_PRODUCT_URL = (
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


def validate_url(url):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        return (
            parsed.scheme == "https"
            and (host == "flipkart.com" or host.endswith(".flipkart.com"))
        )
    except Exception:
        return False


def find_sizes(soup):
    found = {}

    for element in soup.find_all(
        ["a", "button", "div", "span", "li", "label"]
    ):
        size = element.get_text(" ", strip=True).upper()

        if not SIZE_PATTERN.fullmatch(size):
            continue

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
    current = element

    for _ in range(4):
        if current is None:
            break

        style = current.get("style", "").lower()
        classes = " ".join(current.get("class", [])).lower()
        combined = style + " " + classes

        if re.search(
            r"text-decoration\s*:[^;]*line-through|"
            r"line-through|strikethrough|strike-through",
            combined,
        ):
            return "OUT OF STOCK", "Strike-through detected"

        color = re.search(r"color\s*:\s*#([0-9a-f]{6,8})", style)

        if color and color.group(1)[:6] == "707070":
            return "OUT OF STOCK", "Grey text (#707070)"

        if (
            str(current.get("aria-disabled", "")).lower() == "true"
            or current.has_attr("disabled")
        ):
            return "OUT OF STOCK", "Disabled element"

        current = current.parent

    return "AVAILABLE", "No grey/cross-out indicator detected"


def check_product(product_url):
    result = {
        "ok": False,
        "product_url": product_url,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "product_name": None,
        "http_status": None,
        "sizes": [],
        "error": None,
    }

    if not validate_url(product_url):
        result["error"] = "Only HTTPS Flipkart product URLs are allowed."
        return result

    try:
        response = requests.get(
            product_url,
            headers=HEADERS,
            timeout=30,
        )
        result["http_status"] = response.status_code

        if response.status_code != 200:
            result["error"] = (
                f"Product page returned HTTP {response.status_code}."
            )
            return result

        soup = BeautifulSoup(response.text, "html.parser")

        if soup.title:
            result["product_name"] = soup.title.get_text(" ", strip=True)

        sizes = find_sizes(soup)

        if not sizes:
            result["error"] = (
                "No sizes detected. Stock status could not be determined."
            )
            return result

        for size, element in sizes.items():
            status, reason = get_status(element)
            result["sizes"].append({
                "size": size,
                "status": status,
                "reason": reason,
            })

        result["ok"] = True
        return result

    except requests.RequestException as error:
        result["error"] = f"Request failed: {error}"
        return result

    except Exception as error:
        result["error"] = f"Unexpected error: {error}"
        return result


def main():
    product_url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("PRODUCT_URL", DEFAULT_PRODUCT_URL)
    )

    output_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else os.environ.get("OUTPUT_JSON", "")
    )

    print("=" * 52)
    print("FLIPKART SIZE STOCK CHECKER")
    print("=" * 52)
    print("URL:", product_url)

    result = check_product(product_url)

    print("HTTP status:", result["http_status"])
    print("Page title:", result["product_name"] or "Unavailable")

    print("\nSIZE-BY-SIZE RESULTS")
    print("-" * 52)

    for item in result["sizes"]:
        print(
            f'{item["size"]}: {item["status"]} '
            f'({item["reason"]})'
        )

    if result["error"]:
        print("\nERROR:", result["error"])

    available = [
        item["size"] for item in result["sizes"]
        if item["status"] == "AVAILABLE"
    ]
    out_of_stock = [
        item["size"] for item in result["sizes"]
        if item["status"] == "OUT OF STOCK"
    ]

    print("\nSUMMARY")
    print("-" * 52)
    print("Available:", ", ".join(available) or "None")
    print("Out of stock:", ", ".join(out_of_stock) or "None")

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
        print("\nJSON result saved to:", output_path)

    if not result["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
