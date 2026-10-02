import os
import re
import pandas as pd
from textblob import TextBlob

ASSESSED_FILE = "delhi_ngos_assessed.csv"

FRAUD_KEYWORDS = [
    "fake", "scam", "fraud", "cheat", "loot", "money", "extortion", 
    "receipt", "police", "fir", "harass", "threat", "bogus", "stolen"
]

def analyze_custom_input(name, rating, phone, website, reviews):
    """Evaluates arbitrary inputs on the fly."""
    # 1. NLP Sentiment & Keywords
    cleaned_reviews = [r.strip() for r in reviews if len(r.strip().split()) >= 3]
    total_reviews = len(cleaned_reviews)
    
    if total_reviews > 0:
        sentiments = [TextBlob(r).sentiment.polarity for r in cleaned_reviews]
        mean_sentiment = sum(sentiments) / total_reviews
        joined_text = " ".join(cleaned_reviews).lower()
        fraud_kws = sum(1 for kw in FRAUD_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", joined_text))
    else:
        mean_sentiment = 0.0
        fraud_kws = 0

    # 2. Credibility Score calculation
    score = 50.0
    if rating > 0:
        score += (rating - 3.0) * 10
    score += mean_sentiment * 20
    score -= min(fraud_kws * 10, 30)

    has_phone = 1 if phone and phone.strip() not in ["N/A", ""] else 0
    has_web = 1 if website and "http" in website else 0
    score += (has_phone * 5) + (has_web * 5)

    if total_reviews == 0:
        score -= 15

    score = max(0.0, min(100.0, score))

    # 3. Tier assignment
    if score >= 70:
        tier = "Safe / High Credibility"
    elif score >= 40:
        tier = "Moderate / Needs Independent Verification"
    else:
        tier = "Elevated Risk / Requires Caution"

    # 4. Reason breakdown
    reasons = []
    if fraud_kws > 0:
        reasons.append(f"{fraud_kws} scam/fraud-related keywords found in reviews")
    if mean_sentiment < -0.1:
        reasons.append(f"Negative sentiment score ({round(mean_sentiment, 2)})")
    if total_reviews == 0:
        reasons.append("Zero authentic public reviews")
    if not has_web:
        reasons.append("No active digital portal or website linked")
    if not has_phone:
        reasons.append("Missing contact phone number")
    if rating < 3.0 and rating > 0:
        reasons.append(f"Low rating score ({rating} / 5.0)")

    return {
        "NGO": name,
        "Trust Score": round(score, 1),
        "Tier": tier,
        "Sentiment Score": round(mean_sentiment, 2),
        "Fraud Keyword Hits": fraud_kws,
        "Audit Factors": "; ".join(reasons) if reasons else "Verified profile details with consistent positive engagement."
    }

def main():
    if not os.path.exists(ASSESSED_FILE):
        print(f"Error: {ASSESSED_FILE} missing.")
        return

    df = pd.read_csv(ASSESSED_FILE)

    print("=" * 60)
    print("NGO VERIFICATION SYSTEM - TESTING CONSOLE")
    print("=" * 60)
    print("1. Search an extracted Delhi NGO by name")
    print("2. Test a custom/synthetic scenario (Simulate Fraud or Safe)")
    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        query = input("Enter NGO name or keyword: ").strip().lower()
        matches = df[df["ngo_name"].astype(str).str.lower().str.contains(query)]

        if matches.empty:
            print("No matching NGO found in the dataset.")
            return

        for _, row in matches.head(3).iterrows():
            print("\n" + "-" * 50)
            print(f"Name:        {row['ngo_name']}")
            print(f"Trust Score: {round(row['credibility_score'], 1)} / 100")
            print(f"Risk Tier:   {row['risk_tier']}")
            print(f"Avg Rating:  {row['avg_review_rating']}")
            print(f"Audit Notes: {row.get('risk_factors_explanation', 'N/A')}")
            print("-" * 50)

    elif choice == "2":
        print("\n--- Running 2 Pre-built Simulated Edge Cases ---")
        
        # Test Case A: Reputable Profile
        test_safe = analyze_custom_input(
            name="Delhi Child Hope Care",
            rating=4.8,
            phone="+919811223344",
            website="https://delhichildcare.org",
            reviews=[
                "Received the 80G tax exemption receipt on time. Very transparent team.",
                "Visited their center in South Delhi, genuine work being done for kids."
            ]
        )
        print("\n[Safe Case Result]:", test_safe)

        # Test Case B: Suspicious Profile
        test_risky = analyze_custom_input(
            name="Emergency Relief Trust",
            rating=2.1,
            phone="N/A",
            website="N/A",
            reviews=[
                "Fake organization, they took donation money and gave no receipt.",
                "Cheaters and fraud, police complaint has been filed against them."
            ]
        )
        print("\n[Elevated Risk Case Result]:", test_risky)

if __name__ == "__main__":
    main()