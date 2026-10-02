import os
import re
import pandas as pd
from playwright.sync_api import sync_playwright

SEARCH_QUERIES = [
    "NGO in South Extension Delhi",
    "NGO in Saket Delhi",
    "NGO in Hauz Khas Delhi",
    "NGO in Lajpat Nagar Delhi",
    "NGO in Connaught Place Delhi",
    "NGO in Karol Bagh Delhi",
    "NGO in Patel Nagar Delhi",
    "NGO in Rohini Delhi",
    "NGO in Pitampura Delhi",
    "NGO in Janakpuri Delhi",
    "NGO in Dwarka Delhi",
    "NGO in Uttam Nagar Delhi",
    "NGO in Laxmi Nagar Delhi",
    "NGO in Mayur Vihar Delhi",
    "NGO in Shahdara Delhi",
    "NGO in Okhla Delhi",
    "NGO in Vasant Kunj Delhi",
    "NGO in Chandni Chowk Delhi",
    "NGO in Paschim Vihar Delhi",
    "Charity trust Delhi",
    "Child welfare trust Delhi",
    "Animal shelter NGO Delhi",
    "Women welfare society Delhi"
]

TARGET_COUNT = 500
NGO_FILE = "delhi_ngos_raw.csv"

def run_scraper():
    all_ngos = {}

    if os.path.exists(NGO_FILE):
        try:
            old_df = pd.read_csv(NGO_FILE)
            for _, r in old_df.iterrows():
                all_ngos[r["ngo_name"]] = r.to_dict()
            print(f"Resuming with {len(all_ngos)} existing NGOs from {NGO_FILE}")
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"]
        )
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        for query in SEARCH_QUERIES:
            if len(all_ngos) >= TARGET_COUNT:
                print(f"\nReached target of {TARGET_COUNT} NGOs!")
                break

            print(f"\nSearching: '{query}' | Total unique collected: {len(all_ngos)}")
            encoded_query = query.replace(" ", "+")

            try:
                page.goto(f"https://www.google.com/maps/search/{encoded_query}/", timeout=45000)
                page.wait_for_timeout(2500)
            except Exception as e:
                print(f"Error loading {query}, skipping: {e}")
                continue

            feed = page.locator('div[role="feed"]')
            if feed.count() == 0:
                continue

            # Scroll until 'end of list' sentinel or cards stop increasing
            last_count = 0
            stuck_count = 0
            while True:
                # 1. Check if end of list message is present
                end_message = page.locator("text=You've reached the end of the list").count()
                if end_message > 0:
                    print("Reached end of list for this query. Harvesting results...")
                    break

                # 2. Scroll the feed
                feed.evaluate("el => el.scrollBy(0, 2000)")
                page.wait_for_timeout(1500)

                current_count = page.locator('div[role="article"]').count()
                if current_count == last_count:
                    stuck_count += 1
                    if stuck_count >= 3:
                        print("No more items loading. Harvesting results...")
                        break
                else:
                    stuck_count = 0
                    last_count = current_count

            # Extract data directly from the feed elements (Fast & doesn't break DOM)
            cards = page.locator('div[role="article"]').all()
            new_added = 0

            for card in cards:
                if len(all_ngos) >= TARGET_COUNT:
                    break

                try:
                    text_blob = card.inner_text()
                    lines = [line.strip() for line in text_blob.split("\n") if line.strip()]
                    if not lines:
                        continue

                    name = lines[0]
                    if "Sponsored" in name or name in all_ngos:
                        continue

                    # Extract Rating & Review Count from the card's aria-labels
                    rating = 0.0
                    rating_count = 0
                    full_text = " ".join(lines)

                    star_match = re.search(r"(\d\.\d)\s*stars?", full_text)
                    if star_match:
                        rating = float(star_match.group(1))

                    rev_match = re.search(r"\((\d[\d,]*)\)", full_text)
                    if rev_match:
                        rating_count = int(rev_match.group(1).replace(",", ""))

                    # Extract address/category info from card snippets
                    details = " | ".join(lines[1:5])

                    # Get direct link to place
                    link_elem = card.locator('a[href*="/maps/place/"]')
                    place_url = link_elem.first.get_attribute("href") if link_elem.count() > 0 else "N/A"

                    all_ngos[name] = {
                        "ngo_name": name,
                        "rating": rating,
                        "total_reviews": rating_count,
                        "raw_info": details,
                        "url": place_url,
                        "query_zone": query
                    }
                    new_added += 1
                except Exception:
                    continue

            print(f"Added {new_added} new NGOs from this locality.")

            # Save immediately after each locality
            pd.DataFrame(list(all_ngos.values())).to_csv(NGO_FILE, index=False)
            print(f"Checkpoint: {len(all_ngos)} total unique NGOs saved to {NGO_FILE}")

        browser.close()

    print(f"\nFinished! Total unique NGOs extracted: {len(all_ngos)}")

if __name__ == "__main__":
    run_scraper()