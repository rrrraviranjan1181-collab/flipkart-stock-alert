
import json
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

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


def check_product(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if parsed.scheme not in ("http", "https") or not (
        host == "flipkart.com" or host.endswith(".flipkart.com")
    ):
        raise ValueError("Only Flipkart product links are accepted.")

    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    title = soup.title.get_text(" ", strip=True) if soup.title else "Flipkart product"
    found = {}

    for element in soup.find_all(["a", "button", "div", "span", "li", "label"]):
        size = element.get_text(" ", strip=True).upper()

        if not SIZE_PATTERN.fullmatch(size):
            continue

        nested = element.find(
            lambda child: child.name in [
                "a", "button", "div", "span", "li", "label"
            ] and child.get_text(" ", strip=True).upper() == size
        )
        if nested:
            continue

        found.setdefault(size, element)

    if not found:
        raise ValueError("No sizes found in the returned HTML.")

    results = []

    for size, element in found.items():
        current = element
        status = "AVAILABLE"
        reason = "No grey/cross-out indicator detected"

        for _ in range(4):
            if current is None:
                break

            style = current.get("style", "").lower()
            classes = " ".join(current.get("class", [])).lower()
            combined = style + " " + classes

            color = re.search(r"color\s*:\s*#([0-9a-f]{6,8})", style)

            if (
                current.has_attr("disabled")
                or str(current.get("aria-disabled", "")).lower() == "true"
                or re.search(
                    r"text-decoration\s*:[^;]*line-through|"
                    r"line-through|strikethrough|strike-through",
                    combined,
                )
                or (color and color.group(1)[:6] == "707070")
            ):
                status = "OUT OF STOCK"
                reason = "Grey/cross-out indicator"
                break

            current = current.parent

        results.append({
            "size": size,
            "status": status,
            "reason": reason,
        })

    return {
        "ok": True,
        "title": title,
        "product_url": url,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "available_count": sum(x["status"] == "AVAILABLE" for x in results),
        "out_of_stock_count": sum(x["status"] == "OUT OF STOCK" for x in results),
        "unknown_count": 0,
        "note": "Results use the observed grey/cross-out rule."
    }


if __name__ == "__main__":
    try:
        if len(sys.argv) != 3:
            raise ValueError("Usage: python stock_check.py PRODUCT_URL OUTPUT_JSON")

        data = check_product(sys.argv[1])

    except Exception as exc:
        data = {
            "ok": False,
            "error": str(exc),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    with open(sys.argv[2], "w", encoding="utf-8") as output:
        json.dump(data, output, ensure_ascii=False, indent=2)

    print(json.dumps(data, ensure_ascii=False, indent=2))
