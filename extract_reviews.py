import os
import re
import pandas as pd
from playwright.sync_api import sync_playwright

INPUT_CSV = "delhi_ngos_raw.csv"
OUTPUT_REVIEWS_CSV = "delhi_ngo_reviews.csv"

def extract_reviews_from_places():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} not found. Run your NGO scraper first.")
        return

    df_ngos = pd.read_csv(INPUT_CSV)
    
    # Filter NGOs that actually have reviews and a valid Google Maps URL
    df_with_reviews = df_ngos[
        (df_ngos["total_reviews"] > 0) & 
        (df_ngos["url"].str.startswith("http", na=False))
    ].copy()

    print(f"Total NGOs with reviews to process: {len(df_with_reviews)}")

    # Load existing reviews if resuming
    existing_reviews = []
    processed_ngos = set()
    if os.path.exists(OUTPUT_REVIEWS_CSV):
        try:
            old_rev = pd.read_csv(OUTPUT_REVIEWS_CSV)
            existing_reviews = old_rev.to_dict("records")
            processed_ngos = set(old_rev["ngo_name"].unique())
            print(f"Resuming: Loaded {len(existing_reviews)} reviews for {len(processed_ngos)} NGOs.")
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"]
        )
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        count = 0
        for _, row in df_with_reviews.iterrows():
            ngo_name = row["ngo_name"]
            url = row["url"]

            if ngo_name in processed_ngos:
                continue

            print(f"[{count+1}/{len(df_with_reviews)}] Fetching reviews for: {ngo_name}")
            count += 1

            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                # Click on the "Reviews" tab button
                reviews_tab = page.locator('button[role="tab"]:has-text("Reviews")')
                if reviews_tab.count() > 0:
                    reviews_tab.first.click()
                    page.wait_for_timeout(2000)

                # Scroll down inside the reviews pane to load 5-10 reviews
                scrollable_pane = page.locator('div.m6QErb.DxyBCb.kA9KIf.dS8AEf')
                if scrollable_pane.count() > 0:
                    for _ in range(3):
                        scrollable_pane.first.evaluate("el => el.scrollBy(0, 1500)")
                        page.wait_for_timeout(1000)

                # Expand truncated reviews ("More" / "...more" buttons)
                more_btns = page.locator('button.w8nwRe.kyuRq:has-text("More")').all()
                for btn in more_btns[:5]:
                    try:
                        btn.click(timeout=1000)
                    except Exception:
                        pass

                # Locate all review blocks
                review_blocks = page.locator('div.jftiEf').all()
                found_for_this = 0

                for r in review_blocks[:10]:  # Capture top 10 reviews per NGO
                    try:
                        # Extract review text
                        text_elem = r.locator('span.wiI7pd')
                        review_text = text_elem.inner_text().strip() if text_elem.count() > 0 else ""

                        # Extract rating stars
                        rating_elem = r.locator('span.kvMYJc')
                        star_rating = None
                        if rating_elem.count() > 0:
                            aria = rating_elem.first.get_attribute("aria-label")
                            match = re.search(r"(\d)", str(aria))
                            if match:
                                star_rating = int(match.group(1))

                        # Save even if short, but skip empty reviews
                        if review_text:
                            existing_reviews.append({
                                "ngo_name": ngo_name,
                                "star_rating": star_rating,
                                "review_text": review_text
                            })
                            found_for_this += 1
                    except Exception:
                        continue

                print(f"  -> Extracted {found_for_this} reviews.")

            except Exception as e:
                print(f"  -> Skipped due to error: {e}")

            # Checkpoint save every 5 NGOs
            if count % 5 == 0:
                pd.DataFrame(existing_reviews).to_csv(OUTPUT_REVIEWS_CSV, index=False)
                print(f"--- Saved {len(existing_reviews)} total reviews so far ---")

        browser.close()

    # Final save
    pd.DataFrame(existing_reviews).to_csv(OUTPUT_REVIEWS_CSV, index=False)
    print(f"\nCompleted! Total reviews collected: {len(existing_reviews)}")
    print(f"Saved to: {OUTPUT_REVIEWS_CSV}")

if __name__ == "__main__":
    extract_reviews_from_places()