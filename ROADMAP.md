# Improvement Roadmap

This document tracks planned improvements to the market score model and forecast, ordered by estimated impact-to-effort. Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Phase 1 — Signal Quality

These are self-contained changes to `src/market_score.py`. The data is already in the Redfin feed.

### ~~Price Reduction Rate~~ ✅ Done
Added as a 6th signal at 15% weight using Zillow's "Share of Listings With a Price Cut" for the Minneapolis MSA. Redfin city-level doesn't publish this metric; Zillow metro-level data goes back to 2018, giving historical context the Redfin feed lacks. Signal is metro-wide (all cities share the same monthly reading) but adds meaningful temporal variation — rising price cuts pull all scores lower, which is correct macro behavior.

---

### ~~Exponentially Weighted Normalization~~ ✅ Done
Replaced the equal-weight historical mean/std in the per-city z-score with `ewm_mean(half_life=12)` and `ewm_std(half_life=12)`. Data from 12 months ago contributes half the weight of today; 24 months ago contributes a quarter. The high-rate adjustment period (2023–2024) no longer anchors the baseline permanently — scores in balanced territory shifted up from the high 30s/low 40s into the high 40s, which more accurately reflects current conditions relative to recent norms. Rankings are unchanged.

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