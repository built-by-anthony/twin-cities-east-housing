import streamlit as st

st.set_page_config(page_title="Methodology — Twin Cities East Housing", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { padding-top: 1.5rem; }
    h1 { font-size: 1.8rem !important; letter-spacing: -0.5px; }
    h2 { font-size: 1.1rem !important; color: #999 !important; font-weight: 500 !important;
         text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

st.title("How This Works")
st.markdown("<p style='color:#666;'>Plain-English explanation of the market score and forecast.</p>", unsafe_allow_html=True)

st.divider()

st.header("The Market Score")
st.markdown("""
The market score is a single number between 0 and 100 that summarizes who has the upper hand
in a given city right now — buyers or sellers.

- **Above 60** → Seller's market. Homes move fast, bidding wars are common, sellers get what they ask.
- **40–60** → Balanced. Neither side has a clear edge.
- **Below 40** → Buyer's market. Inventory is building, homes sit longer, sellers are negotiating.

The score is built from six signals — five from Redfin's monthly city-level data, one from Zillow:
""")

st.markdown("""
| Signal | Source | Weight | What it's measuring |
|---|---|---|---|
| Average sale-to-list ratio | Redfin (city) | 20% | Are homes actually selling at asking price? Above 100% means bidding wars. |
| % sold above list price | Redfin (city) | 20% | What share of closings involved a bidding war? |
| Median days on market | Redfin (city) | 20% | How fast are homes moving? |
| Months of supply | Redfin (city) | 15% | How long would it take to sell every active listing at the current sales pace? Under 3 months is hot, over 6 is slow. |
| Pending sales | Redfin (city) | 10% | How many buyers are actively under contract right now? A leading indicator. |
| % listings with a price cut | Zillow (Minneapolis metro) | 15% | Are sellers capitulating? Rising price cuts are one of the earliest signals of a cooling market. |
""")

st.markdown("""
**Why these signals?** The first two (sale-to-list ratio and bidding wars) are the most direct
measure of pricing power — they show what actually happened at the closing table. Days on market
and months of supply capture inventory pressure. Pending sales is the forward-looking piece,
since contracts signed today become closed sales in 30–60 days.

**Why months of supply instead of raw active listings?** A city like Woodbury will always have
more active listings than Newport just because it's bigger. Months of supply normalizes for
that by dividing active listings by the monthly sales pace, so you're comparing apples to apples.

**Why is the price cut signal metro-level?** Zillow doesn't publish city-level price cut data —
only metro. So all 11 cities share the same Minneapolis MSA reading each month. This means it
doesn't help compare Woodbury vs Stillwater in a given month, but it does add a strong
time-varying signal: when price cuts are rising across the metro, every city's score is pulled
lower. That's the right behavior — a metro-wide cooling trend should affect everyone.
""")

st.divider()

st.header("Why a Score of 50 Doesn't Always Mean the Same Thing")
st.markdown("""
The score is designed to answer: *"Is this city hot or cold relative to its own normal?"*

Each signal is measured against that city's own historical average — not against other cities.
A Woodbury score of 60 means Woodbury is running hotter than its own typical conditions.
A Stillwater score of 60 means the same for Stillwater, even though their markets are
structurally different (Stillwater has tighter inventory and different price points).

This makes the score useful for spotting trends *within* a city — is the market heating up
or cooling down compared to what's normal here? It's less useful for directly comparing
"is Woodbury hotter than Stillwater right now in absolute terms."
""")

st.divider()

st.header("The Forecast")
st.markdown("""
The forecast is generated using [Prophet](https://facebook.github.io/prophet/), a time series
model built by Meta's data science team. A separate model is fit for each city.

Prophet finds the underlying trend and the seasonal pattern (spring buying season, winter
slowdown), then projects those forward. It also produces a confidence range — the forecast
gets less certain the further out you go, which is why the chart shows a band rather than a line.

**Why only 3 months?** City-level Redfin data only goes back to January 2023 — about 3 years.
That's enough to make a reasonable short-term call, but 6+ month forecasts with this much
history tend to chase recent trends too aggressively and produce numbers that aren't credible.
When longer historical data becomes available, this will extend.

**What the forecast can and can't do:** It's good at capturing the seasonal pattern (spring
is always busier than January in Minnesota) and recent momentum. It can't anticipate a
sudden rate move, a recession, or anything it hasn't seen in the training data. Treat it as
a directional signal, not a prediction.
""")

st.divider()

st.header("Known Limitations")
st.markdown("""
**Short history.** Three years of data includes one rate shock (2022), an adjustment period,
and a partial recovery. There's no pre-2023 "normal market" baseline to anchor against.
This is the biggest weakness in the model right now.

**Small cities are noisy.** Newport and Oak Park Heights sometimes see fewer than 10 closed
sales per month. One unusual transaction can swing their score meaningfully. Take those two
with extra skepticism.

**No macroeconomic inputs.** The model has no idea what mortgage rates are doing. A 50-basis-point
rate move can shift buyer demand faster than any of these signals can capture. Adding mortgage
rate data from the Fed (FRED API) is on the roadmap.

**The score is relative, not absolute.** A city that's been in a soft market for 2 years
might show a 50 score (average for itself) while conditions are still objectively weak.
Use the Underlying Data tab alongside the score to get the full picture.
""")

st.divider()
st.markdown(
    "<p style='color:#555; font-size:0.8rem;'>Data sourced from "
    "<a href='https://www.redfin.com/news/data-center/' style='color:#666;'>Redfin Data Center</a> and "
    "<a href='https://www.zillow.com/research/data/' style='color:#666;'>Zillow Research</a>. "
    "Not financial or real estate advice.</p>",
    unsafe_allow_html=True,
)