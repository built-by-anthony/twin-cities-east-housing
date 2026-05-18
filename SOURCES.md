# Data Sources

## Zillow — Home Value Index (ZHVI)

- **URL:** https://www.zillow.com/research/data/
- **Dataset:** Home Values → ZHVI — Single-Family Homes, City, Smoothed Seasonally Adjusted
- **File:** `City_zhvi_uc_sfr_tier_0.33_0.67_sm_sa_month.csv`
- **Frequency:** Monthly
- **Last downloaded:** May 2026

## Redfin — Housing Market Tracker

- **URL:** https://www.redfin.com/news/data-center/
- **Dataset:** Housing Market Tracker → All cities, monthly
- **File:** `redfin_housing_market_monthly_all_cities_2023_Jan_to_2026_Apr.csv`
- **Frequency:** Monthly
- **Last downloaded:** May 2026

---

When updating, download the latest file, replace the corresponding file in `data/raw/`, then run:

```bash
uv run python main.py
```