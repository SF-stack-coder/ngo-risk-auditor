import os
import re
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import shap

INPUT_FILE = "delhi_ngos_with_reviews_cleaned.csv"
OUTPUT_FILE = "delhi_ngos_assessed.csv"

def compute_credibility_index(row):
    """
    Computes an objective Credibility Score (0 to 100).
    Higher indicates higher public engagement and consistency;
    lower indicates negative feedback or insufficient data.
    """
    score = 50.0  # Base neutral score

    # 1. Rating contribution (-20 to +20)
    rating = row.get("avg_review_rating", 0.0)
    if rating > 0:
        score += (rating - 3.0) * 10

    # 2. NLP Sentiment contribution (-20 to +20)
    sentiment = row.get("mean_sentiment", 0.0)
    score += sentiment * 20

    # 3. Fraud keyword penalty (up to -30 points)
    kw_count = row.get("total_fraud_keywords", 0)
    score -= min(kw_count * 10, 30)

    # 4. Contact / website completeness bonus (+10 points)
    has_phone = row.get("has_phone_num", 0)
    has_web = row.get("has_valid_website", 0)
    score += (has_phone * 5) + (has_web * 5)

    # 5. Low/unverified feedback penalty
    reviews_count = row.get("authentic_review_count", 0)
    if reviews_count == 0:
        score -= 15

    return float(np.clip(score, 0.0, 100.0))

def categorize_risk(score):
    if score >= 70:
        return "Safe / High Credibility"
    elif score >= 40:
        return "Moderate / Needs Independent Verification"
    else:
        return "Elevated Risk / Requires Caution"

def run_training_pipeline():
    if not os.path.exists(INPUT_FILE):
        print(f"File {INPUT_FILE} not found!")
        return

    df = pd.read_csv(INPUT_FILE)
    print(f"Loaded {len(df)} NGO records for modeling...")

    # --- Safe Column Extraction & Fallbacks ---
    # Handle phone column
    if "phone" in df.columns:
        df["has_phone_num"] = df["phone"].apply(lambda x: 1 if pd.notna(x) and str(x).strip() not in ["N/A", "nan", ""] else 0)
    elif "raw_info" in df.columns:
        # Check for 10-digit Indian numbers or landlines in raw_info
        df["has_phone_num"] = df["raw_info"].astype(str).apply(
            lambda x: 1 if re.search(r"(\+91|0)?\s?[6-9]\d{9}|011\s?\d{7,8}", x) else 0
        )
    else:
        df["has_phone_num"] = 0

    # Handle website column
    if "website" in df.columns:
        df["has_valid_website"] = df["website"].apply(lambda x: 1 if pd.notna(x) and "http" in str(x) else 0)
    elif "url" in df.columns:
        # Check if URL is present and not just empty
        df["has_valid_website"] = df["url"].apply(lambda x: 1 if pd.notna(x) and str(x).startswith("http") else 0)
    else:
        df["has_valid_website"] = 0

    # Ensure all numerical feature columns exist
    numeric_defaults = {
        "avg_review_rating": 3.0,
        "authentic_review_count": 0,
        "mean_sentiment": 0.0,
        "total_fraud_keywords": 0
    }
    for col, default_val in numeric_defaults.items():
        if col not in df.columns:
            df[col] = default_val
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default_val)

    # Compute Credibility Index & Assign Categories
    df["credibility_score"] = df.apply(compute_credibility_index, axis=1)
    df["risk_tier"] = df["credibility_score"].apply(categorize_risk)

    features = [
        "avg_review_rating",
        "authentic_review_count",
        "mean_sentiment",
        "total_fraud_keywords",
        "has_phone_num",
        "has_valid_website"
    ]

    X = df[features]
    tier_mapping = {
        "Safe / High Credibility": 0,
        "Moderate / Needs Independent Verification": 1,
        "Elevated Risk / Requires Caution": 2
    }
    y = df["risk_tier"].map(tier_mapping)

    print("\nTarget Class Distribution:")
    print(df["risk_tier"].value_counts())

    # Check if any class has fewer than 2 samples to prevent stratify errors
    min_class_count = y.value_counts().min()
    stratify_option = y if min_class_count >= 2 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify_option
    )

    # Train Random Forest
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    present_labels = sorted(list(set(y_test) | set(y_pred)))
    target_names = [k for k, v in sorted(tier_mapping.items(), key=lambda item: item[1]) if v in present_labels]

    print("\n--- Model Evaluation Report ---")
    print(classification_report(y_test, y_pred, labels=present_labels, target_names=target_names, zero_division=0))

    # Feature Importance via TreeExplainer
    explainer = shap.TreeExplainer(model)
    _ = explainer.shap_values(X)

    # Generate Human-Readable Reason for Audit
    def generate_explanation(row):
        reasons = []
        if row["total_fraud_keywords"] > 0:
            reasons.append(f"{int(row['total_fraud_keywords'])} scam-related terms detected in reviews")
        if row["mean_sentiment"] < -0.1:
            reasons.append("Prevalently negative public sentiment")
        if row["authentic_review_count"] == 0:
            reasons.append("No independent public feedback available")
        if row["has_valid_website"] == 0:
            reasons.append("No independent portal or website found")
        if row["has_phone_num"] == 0:
            reasons.append("No verified contact number provided")
        if row["avg_review_rating"] < 3.0 and row["avg_review_rating"] > 0:
            reasons.append(f"Sub-standard user review rating ({row['avg_review_rating']} / 5.0)")

        if not reasons:
            return "Profile possesses verified contact data and positive public engagement."
        return "; ".join(reasons)

    df["risk_factors_explanation"] = df.apply(generate_explanation, axis=1)

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nFinal assessed dataset successfully saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    run_training_pipeline()