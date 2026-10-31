# Problem Statement: Mutual Fund FAQ Assistant (Facts-Only Q&A)

## Overview

The objective of this project is to build a **facts-only FAQ assistant** for mutual fund schemes, using **Groww** as the reference product context. The assistant will answer objective, verifiable queries related to mutual funds by retrieving information exclusively from official public sources, such as AMC (Asset Management Company) websites, AMFI, and SEBI.

> [!IMPORTANT]
> The system must strictly avoid providing investment advice, opinions, or recommendations. Every response must include a single, clear source link and adhere to defined constraints around clarity, accuracy, and compliance.

---

## Objective

Design and implement a lightweight **Retrieval-Augmented Generation (RAG)**-based assistant that:

- Answers factual queries about mutual fund schemes
- Uses a curated corpus of official documents
- Provides concise, source-backed responses

---

## Target Users

- Retail investors comparing mutual fund schemes
- Customer support and content teams handling repetitive mutual fund queries

---

## Scope of Work

### 1. Corpus Definition

- Source platform: **Groww** (reference product context)
- Corpus limited to **15 official Groww mutual fund scheme URLs**
- Covers multiple AMCs and fund categories for broad factual coverage

#### Curated Source URLs

| # | Scheme Name | Category | URL |
|---|---|---|---|
| 1 | Bandhan Small Cap Fund – Direct Growth | Small Cap | [🔗 Link](https://groww.in/mutual-funds/bandhan-small-cap-fund-direct-growth) |
| 2 | Axis Silver FOF – Direct Growth | Fund of Funds | [🔗 Link](https://groww.in/mutual-funds/axis-silver-fof-direct-growth) |
| 3 | Parag Parikh Long Term Value Fund – Direct Growth | Value / Flexi Cap | [🔗 Link](https://groww.in/mutual-funds/parag-parikh-long-term-value-fund-direct-growth) |
| 4 | Motilal Oswal Most Focused Midcap 30 Fund – Direct Growth | Mid Cap | [🔗 Link](https://groww.in/mutual-funds/motilal-oswal-most-focused-midcap-30-fund-direct-growth) |
| 5 | Kotak Silver ETF FOF – Direct Growth | Fund of Funds | [🔗 Link](https://groww.in/mutual-funds/kotak-silver-etf-fof-direct-growth) |
| 6 | HDFC Mid Cap Fund – Direct Growth | Mid Cap | [🔗 Link](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth) |
| 7 | JioBlackRock Flexi Cap Fund – Direct Growth | Flexi Cap | [🔗 Link](https://groww.in/mutual-funds/jioblackrock-flexi-cap-fund-direct-growth) |
| 8 | HDFC Silver ETF FOF – Direct Growth | Fund of Funds | [🔗 Link](https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth) |
| 9 | SBI Nifty Next 50 Index Fund – Direct Growth | Index Fund | [🔗 Link](https://groww.in/mutual-funds/sbi-nifty-next-50-index-fund-direct-growth) |
| 10 | SBI PSU Fund – Direct Growth | Thematic / PSU | [🔗 Link](https://groww.in/mutual-funds/sbi-psu-fund-direct-growth) |
| 11 | Nippon India Growth Mid Cap Fund – Direct Growth | Mid Cap | [🔗 Link](https://groww.in/mutual-funds/nippon-india-growth-mid-cap-fund-direct-growth) |
| 12 | Bank of India Small Cap Fund – Direct Growth | Small Cap | [🔗 Link](https://groww.in/mutual-funds/bank-of-india-small-cap-fund-direct-growth) |
| 13 | ICICI Prudential Large Cap Fund – Direct Growth | Large Cap | [🔗 Link](https://groww.in/mutual-funds/icici-prudential-large-cap-fund-direct-growth) |
| 14 | Bank of India Flexi Cap Fund – Direct Growth | Flexi Cap | [🔗 Link](https://groww.in/mutual-funds/bank-of-india-flexi-cap-fund-direct-growth) |
| 15 | Axis Liquid Direct Fund – Growth | Liquid / Debt | [🔗 Link](https://groww.in/mutual-funds/axis-liquid-direct-fund-growth) |

#### AMCs Covered

| AMC | Schemes in Corpus |
|---|---|
| SBI Mutual Fund | 2 (Nifty Next 50, PSU Fund) |
| HDFC Mutual Fund | 2 (Mid Cap, Silver ETF FOF) |
| Axis Mutual Fund | 2 (Silver FOF, Liquid) |
| Bank of India Mutual Fund | 2 (Small Cap, Flexi Cap) |
| Motilal Oswal Mutual Fund | 1 (Focused Midcap 30) |
| Bandhan Mutual Fund | 1 (Small Cap) |
| Kotak Mutual Fund | 1 (Silver ETF FOF) |
| Parag Parikh Mutual Fund | 1 (Long Term Value) |
| Nippon India Mutual Fund | 1 (Growth Mid Cap) |
| ICICI Prudential Mutual Fund | 1 (Large Cap) |
| JioBlackRock Mutual Fund | 1 (Flexi Cap) |

#### Fund Categories Covered

| Category | Count |
|---|---|
| Mid Cap | 3 |
| Fund of Funds (Silver ETF) | 3 |
| Small Cap | 2 |
| Flexi Cap | 2 |
| Index Fund | 1 |
| Thematic / PSU | 1 |
| Large Cap | 1 |
| Value Fund | 1 |
| Liquid / Debt | 1 |

### 2. FAQ Assistant Requirements

The assistant must answer **facts-only queries**, such as:

#### Scheme Details

| Query Type | Example |
|---|---|
| Expense ratio | "What is the expense ratio of HDFC Mid Cap Fund?" |
| Exit load | "What is the exit load for Bandhan Small Cap Fund?" |
| Minimum SIP amount | "What is the minimum SIP amount for Axis Liquid Fund?" |
| Lock-in period | "What is the lock-in period for an ELSS fund?" |
| Risk classification | "What is the riskometer rating of Nippon India Growth Mid Cap Fund?" |
| Benchmark index | "What is the benchmark index of SBI Nifty Next 50 Index Fund?" |
| Fund type / category | "What category does Parag Parikh Long Term Value Fund belong to?" |
| AUM | "What is the AUM of ICICI Prudential Large Cap Fund?" |
| NAV | "What is the current NAV of JioBlackRock Flexi Cap Fund?" |
| Downloads | "How do I download my capital gains statement?" |

#### Fund Management Data

The assistant must also answer factual queries about **fund managers and fund management**, including:

| Query Type | Example |
|---|---|
| Fund manager name | "Who manages the HDFC Mid Cap Fund?" |
| Fund manager since | "Since when has the fund manager been managing Kotak Silver ETF FOF?" |
| Number of funds managed | "How many funds does the fund manager of SBI PSU Fund manage?" |
| Fund manager experience | "What is the total experience of the fund manager of Motilal Oswal Focused Midcap 30 Fund?" |
| Fund management team | "Who are the fund managers of Bank of India Flexi Cap Fund?" |
| Co-fund manager details | "Does Nippon India Growth Mid Cap Fund have a co-fund manager?" |

> [!NOTE]
> Fund management data (manager name, tenure, experience, co-managers) must be sourced exclusively from official AMC pages or Groww scheme pages. No third-party profile or biographical sources are permitted.

**Response constraints:**

- Each response is limited to a maximum of **3 sentences**
- Each response includes **exactly one citation link**
- Each response includes a footer:
  > *"Last updated from sources: \<date\>"*

### 3. Refusal Handling

The assistant must **refuse** non-factual or advisory queries, such as:

- *"Should I invest in this fund?"*
- *"Which fund is better?"*

Refusal responses should:

- Be polite and clearly worded
- Reinforce the facts-only limitation
- Provide a relevant educational link (e.g., AMFI or SEBI resource)

### 4. User Interface (Minimal)

The solution should include a simple interface with:

- A welcome message
- Three example questions
- A visible disclaimer:
  > **"Facts-only. No investment advice."**

---

## Constraints

### Data and Sources

> [!NOTE]
> Use only official public sources (AMC, AMFI, SEBI). Do not use third-party blogs or aggregator websites.

### Privacy and Security

> [!CAUTION]
> Do not collect, store, or process:
> - PAN or Aadhaar numbers
> - Account numbers
> - OTPs
> - Email addresses or phone numbers

### Content Restrictions

- No investment advice or recommendations
- No performance comparisons or return calculations
- For performance-related queries, provide a link to the official factsheet only

### Transparency

- Responses must be short, factual, and verifiable
- Every answer must include a **source link** and **last updated date**

---

## Expected Deliverables

1. **README Document**
   - Setup instructions
   - Selected AMC and schemes
   - Architecture overview (RAG approach)
   - Known limitations

2. **Disclaimer Snippet**
   - *"Facts-only. No investment advice."*

---

## Success Criteria

| Criteria | Description |
|---|---|
| ✅ Accurate retrieval | Factual mutual fund information is retrieved correctly |
| ✅ Facts-only adherence | Strict adherence to facts-only responses |
| ✅ Source citations | Consistent inclusion of valid source citations |
| ✅ Refusal handling | Proper refusal of advisory queries |
| ✅ UI quality | Clean, minimal, and user-friendly interface |

---

## Summary

The goal is to build a **trustworthy, transparent, and compliant** mutual fund FAQ assistant that prioritizes **accuracy over intelligence**. The system should ensure that users receive only verified, source-backed financial information, without any advisory bias or speculative content.

