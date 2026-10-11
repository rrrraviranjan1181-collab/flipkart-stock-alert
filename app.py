
import requests
from bs4 import BeautifulSoup
import re

PRODUCT_URL = "https://www.flipkart.com/puma-military-camouflage-men-crew-neck-black-t-shirt/p/itm5336dfb62fa01?pid=TSHHP6ADWYWKBJV2"

SIZES = ["XS", "S", "M", "L", "XL", "XXL"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def check_stock():
    print("=" * 45)
    print("FLIPKART T-SHIRT STOCK CHECK")
    print("=" * 45)
    print("Product: Puma Military Camouflage Black T-shirt")
    print("Checking product page...\n")

    try:
        response = requests.get(
            PRODUCT_URL,
            headers=HEADERS,
            timeout=30,
        )

        print(f"HTTP Status: {response.status_code}")

        if response.status_code != 200:
            print("ERROR: Could not access the product page.")
            print("Stock status: UNKNOWN")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text(" ", strip=True)

        print(f"Page title: {soup.title.get_text(strip=True) if soup.title else 'Not found'}")
        print("\nSIZE RESULTS")
        print("-" * 45)

        # Find size labels in the page text.
        # This is a diagnostic check, not definitive proof of stock.
        for size in SIZES:
            found = False

            for element in soup.find_all(["a", "button", "div", "span"]):
                text = element.get_text(" ", strip=True)

                if text == size:
                    found = True
                    break

            if found:
                print(f"{size}: Size label found — availability UNKNOWN")
            else:
                print(f"{size}: Size label not found — availability UNKNOWN")

        print("\nPAGE DIAGNOSTICS")
        print("-" * 45)

        for phrase in ["Add to cart", "Buy now", "Notify Me", "Out of Stock"]:
            print(f"{phrase}: {'Found' if phrase.lower() in page_text.lower() else 'Not found'}")

        print("\nIMPORTANT:")
        print("Finding a size label does NOT prove that size is in stock.")
        print("This script does not yet reliably verify each size's availability.")
        print("Compare these results with the sizes you check manually.")

    except requests.RequestException as error:
        print(f"Request error: {error}")
        print("Stock status: UNKNOWN")
    except Exception as error:
        print(f"Unexpected error: {error}")
        print("Stock status: UNKNOWN")


if __name__ == "__main__":
    check_stock()
