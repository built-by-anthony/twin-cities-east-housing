# Improvement Roadmap

This document tracks planned improvements to the market score model and forecast, ordered by estimated impact-to-effort. Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Phase 1 — Signal Quality

These are self-contained changes to `src/market_score.py`. The data is already in the Redfin feed.

### Price Reduction Rate
**What:** Add the percentage of active listings that have taken at least one price cut as a scored signal.

**Why:** Price reductions are one of the most leading indicators available — sellers reduce price before the broader market score catches up. It's a direct measure of seller capitulation and tends to lead closed-sale metrics by 4–8 weeks.

**How:** Redfin publishes `PRICE DROPS (MOM)` in the housing market tracker. Add as a 6th signal weighted ~15%, redistributed from the sale-to-list and above-list weights.

---

### Exponentially Weighted Normalization
**What:** Replace the equal-weight historical mean/std in the per-city z-score with an exponentially weighted equivalent, so recent months carry more influence than data from 3 years ago.

**Why:** The current z-score anchors every city's baseline to the 2021–2022 pandemic frenzy. That era was a structural outlier and it's pulling the historical mean upward, which makes the entire current market look like a buyer's market by comparison. Exponential weighting decays the influence of older observations and makes the score more responsive to genuine trend shifts.

**How:** Replace `pl.col(col).mean().over("region_name")` with an exponentially weighted mean using a half-life of approximately 18–24 months.

---

### Seasonal Decomposition (STL)
**What:** Explicitly remove the seasonal component from each signal before computing z-scores, using STL (Seasonal-Trend decomposition using LOESS).

**Why:** Minnesota housing is deeply seasonal. February always scores lower than May regardless of market conditions. The current z-score asks "is this month hot compared to all months in this city's history?" It should ask "is this February hot *for a February*?" A score of 45 in winter should mean something different than a 45 in peak spring season.

**How:** Apply `statsmodels.tsa.seasonal.STL` to each city's signal series, extract the residual (deseasonalized) component, and run the z-score normalization on that instead of the raw values.

---

## Phase 2 — External Regressors

These require pulling new data sources but would significantly improve forecast range and accuracy.

### 30-Year Mortgage Rate (FRED)
**What:** Add the weekly 30-year fixed mortgage rate (FRED series: `MORTGAGE30US`) as an external regressor in the Prophet forecast model.

**Why:** Mortgage rates are the single variable most correlated with buyer demand and affordability. The current forecast extrapolates purely from price and volume signals with no visibility into the rate environment. Adding rates as a known future regressor (FRED publishes forecasts) would unlock a credible 12-month forecast horizon and let the model distinguish rate-driven slowdowns from organic ones.

**How:** Pull via the FRED API (free, no key required for public series). Resample to monthly. Pass as a `Prophet.add_regressor()` call. Requires a projected future rate series for the forecast window.

---

### Building Permits (Washington + Ramsey County)
**What:** Add monthly residential building permit counts from Washington and Ramsey counties as a supply-side leading indicator.

**Why:** Permits lead active inventory by 6–12 months. If permit issuance is rising in Woodbury today, supply pressure is coming whether or not it's visible in current listings. This is especially relevant for newer suburbs where new construction is a meaningful share of the market.

**How:** Census Building Permits Survey (`https://www.census.gov/construction/bps/`) publishes monthly county-level data. No API key required.

---

## Phase 3 — Validation and Robustness

### Backtest
**What:** Hold out the last 6 months of data, fit the model on everything prior, and score forecast accuracy against actuals.

**Why:** There is currently no ground truth check on whether the model is actually predictive. Before adding more complexity, we should establish a baseline accuracy metric (e.g., MAE on the 3-month and 6-month score predictions) so future changes can be measured against it.

---

### Small-Market Confidence Weighting
**What:** Damp the scores of low-volume cities toward neutral (50) when monthly transaction counts are thin.

**Why:** Newport and Oak Park Heights regularly see 5–10 closed sales per month. One atypical transaction can move their z-score by a full standard deviation, producing signal that looks meaningful but is mostly noise. A reliability weight inversely proportional to the coefficient of variation would make these markets more honest about their uncertainty.

---

### Weight Calibration via Domain Expert Labels
**What:** Collect 20–30 historical month-city labels (buyer / balanced / seller) from a local real estate professional, then fit the signal weights using logistic regression against those labels.

**Why:** The current 25/25/20/15/15 weight split is reasoned, not empirically fit. An expert with ground truth knowledge of what the East Metro felt like in specific months could validate or correct the weighting scheme.

**Note:** If you have an NMLS number or know someone who does, their transaction history is probably worth more than any of the above.

---

## Contributing

If you want to take on one of these, open an issue to claim it before starting. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guidelines.