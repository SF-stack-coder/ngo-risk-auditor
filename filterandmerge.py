import os
import re
import pandas as pd
from textblob import TextBlob

NGO_FILE = "delhi_ngos_raw.csv"
REVIEW_FILE = "delhi_ngo_reviews.csv"
OUTPUT_MERGED_FILE = "delhi_ngos_with_reviews_cleaned.csv"

# Generic boilerplate phrases commonly found in bot/paid 5-star reviews
BOT_TEMPLATES = [
    r"^best ngo( in delhi)?$",
    r"^good job( keep it up)?$",
    r"^very good( ngo| service)?$",
    r"^nice( work| team)?$",
    r"^keep it up$",
    r"^great initiative$",
    r"^excellent work$",
    r"^superb$",
    r"^awesome$",
    r"^\+1$",
    r"^100% genuine$"
]

FRAUD_KEYWORDS = [
    "fake", "scam", "fraud", "cheat", "loot", "money", "extortion", 
    "receipt", "police", "fir", "harass", "threat", "bogus", "stolen"
]

def clean_text(text):
    if not isinstance(text, str):
        return ""
    # Remove excessive punctuation, emojis, and whitespace
    text = re.sub(r"[^\w\s\.,!?]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def is_fake_or_spam(text, star_rating):
    """
    Returns True if the review shows signatures of paid spam / bot generation.
    """
    t = text.lower().strip()
    words = t.split()
    word_count = len(words)

    # 1. Extremely short non-informative reviews (e.g., 'Nice', 'Good')
    if word_count < 3:
        return True

    # 2. Boilerplate templated matches
    for pattern in BOT_TEMPLATES:
        if re.search(pattern, t):
            return True

    # 3. High word repetition check (e.g., "Good good good very good")
    unique_ratio = len(set(words)) / float(word_count)
    if word_count >= 5 and unique_ratio < 0.45:
        return True

    return False

def count_fraud_keywords(text):
    t = text.lower()
    return sum(1 for kw in FRAUD_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", t))

def process_and_merge():
    if not os.path.exists(NGO_FILE) or not os.path.exists(REVIEW_FILE):
        print(f"Error: Ensure both '{NGO_FILE}' and '{REVIEW_FILE}' exist in the folder.")
        return

    print("Loading datasets...")
    df_ngos = pd.read_csv(NGO_FILE)
    df_reviews = pd.read_csv(REVIEW_FILE)

    print(f"Raw NGOs: {len(df_ngos)} | Raw Reviews: {len(df_reviews)}")

    # Clean review text
    df_reviews["review_clean"] = df_reviews["review_text"].apply(clean_text)
    df_reviews.dropna(subset=["review_clean"], inplace=True)
    df_reviews = df_reviews[df_reviews["review_clean"] != ""]

    # Drop exact duplicate reviews across the entire dataset (bot reposts)
    initial_rev_len = len(df_reviews)
    df_reviews.drop_duplicates(subset=["ngo_name", "review_clean"], inplace=True)
    
    # Identify fake / spam reviews
    df_reviews["is_spam"] = df_reviews.apply(
        lambda r: is_fake_or_spam(r["review_clean"], r.get("star_rating", 5)), axis=1
    )
    
    spam_count = df_reviews["is_spam"].sum() + (initial_rev_len - len(df_reviews))
    print(f"Detected & removed {spam_count} fake / generic promotional reviews.")

    # Keep only authentic, substantive reviews
    df_clean_reviews = df_reviews[~df_reviews["is_spam"]].copy()

    # NLP Sentiment & keyword scoring
    print("Computing sentiment polarity and fraud keyword flags...")
    df_clean_reviews["sentiment_polarity"] = df_clean_reviews["review_clean"].apply(
        lambda x: TextBlob(x).sentiment.polarity
    )
    df_clean_reviews["fraud_kw_count"] = df_clean_reviews["review_clean"].apply(count_fraud_keywords)

    # Aggregate reviews per NGO
    ngo_review_stats = df_clean_reviews.groupby("ngo_name").agg(
        authentic_review_count=("review_clean", "count"),
        avg_review_rating=("star_rating", "mean"),
        mean_sentiment=("sentiment_polarity", "mean"),
        total_fraud_keywords=("fraud_kw_count", "sum"),
        aggregated_reviews=("review_clean", lambda texts: " ||| ".join(texts[:5])) # Top 5 reviews combined
    ).reset_index()

    # Standardize names for joining
    df_ngos["clean_join_name"] = df_ngos["ngo_name"].astype(str).str.strip().str.lower()
    ngo_review_stats["clean_join_name"] = ngo_review_stats["ngo_name"].astype(str).str.strip().str.lower()

    # Merge NGO profile data with aggregated review signals
    merged_df = pd.merge(
        df_ngos, 
        ngo_review_stats.drop(columns=["ngo_name"]), 
        on="clean_join_name", 
        how="left"
    )

    # Fill default values for NGOs with zero authentic reviews
    merged_df["authentic_review_count"] = merged_df["authentic_review_count"].fillna(0).astype(int)
    merged_df["avg_review_rating"] = merged_df["avg_review_rating"].fillna(merged_df["rating"])
    merged_df["mean_sentiment"] = merged_df["mean_sentiment"].fillna(0.0) # 0.0 is neutral
    merged_df["total_fraud_keywords"] = merged_df["total_fraud_keywords"].fillna(0).astype(int)
    merged_df["aggregated_reviews"] = merged_df["aggregated_reviews"].fillna("No verified reviews found.")

    merged_df.drop(columns=["clean_join_name"], inplace=True)

    merged_df.to_csv(OUTPUT_MERGED_FILE, index=False)
    print(f"\nSuccessfully merged!")
    print(f"Saved: {OUTPUT_MERGED_FILE} with {len(merged_df)} total NGO entries.")

if __name__ == "__main__":
    process_and_merge()