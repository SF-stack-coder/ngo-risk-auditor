# 🛡️ NGO Trust & Public Sentiment Risk Auditor (Delhi Region)

An AI/ML-driven pipeline designed to evaluate public trust signals, combat deceptive donation practices, and flag high-scrutiny organizations across the Delhi National Capital Region (NCR).

Rather than assigning definitive legal verdicts, this system formulates an explainable **Credibility & Public Feedback Risk Index (0–100)** by cross-referencing contact availability, review authenticity, and NLP sentiment signals.

---

## 📌 Project Overview
* **Target Scope:** 500+ Non-Governmental Organizations across Delhi micro-zones.
* **Core Objective:** Protect donors from unverified or scam-flagged entities while giving transparent visibility to legitimate grassroots charities.
* **Compliance Safeguard:** Strictly adheres to analytical risk scoring (*High Credibility*, *Needs Verification*, *Elevated Risk*) to maintain academic and legal compliance without defamatory labeling.

---

## ⚙️ Architecture & Pipeline

[ Web Data Ingestion ]
└── Multi-zone regional extraction (Playwright / Chromium)
│
▼
[ Spam & Bot Review Filtering ]
├── Removal of templated 5-star review bot patterns
├── Lexical diversity & duplicate phrase suppression
└── High-risk keyword matching (e.g., "no receipt", "fake", "police complaint")
│
▼
[ NLP & Feature Engineering ]
├── Sentiment Polarity Scoring (TextBlob / Transformer-ready)
├── Profile Completeness (Verified phone, official domain presence)
└── Composite Credibility Index (0–100)
│
▼
[ ML Risk Classification & Explainability ]
├── Random Forest Classifier (98% macro test accuracy across 3 risk tiers)
└── Model explainability engine generating itemized risk audit factors

---

## 📊 Dataset & Model Performance

The dataset was evaluated using a stratified validation split across 3 objective risk tiers:
* **Safe / High Credibility** (Score $\ge$ 70)
* **Moderate / Needs Verification** (Score 40–69)
* **Elevated Risk / Requires Caution** (Score < 40)

Risk Tier                    Precision    Recall    F1-Score
Safe / High Credibility                      0.97        1.00       0.99
Moderate / Needs Verification                1.00        0.93       0.97
Elevated Risk / Requires Caution             1.00        1.00       1.00
Accuracy: 0.98