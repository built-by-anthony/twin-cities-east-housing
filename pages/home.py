import streamlit as st
import polars as pl
import datetime
from pathlib import Path
from dateutil.relativedelta import relativedelta
from src.redfin import redfin_housing_market_tracker_extract, redfin_housing_market_tracker_transform
from src.zillow import zillow_price_cut_extract
from src.market_score import compute_market_score

st.set_page_config(page_title="Twin Cities East Housing", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { padding-top: 1.5rem; }
    h1 { font-size: 1.8rem !important; letter-spacing: -0.5px; }
    h2 { font-size: 1.1rem !important; color: #999 !important; font-weight: 500 !important;
         text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    redfin = redfin_housing_market_tracker_transform(redfin_housing_market_tracker_extract())
    price_cut = zillow_price_cut_extract()
    scores = compute_market_score(redfin, price_cut)
    return redfin, scores, price_cut


redfin_df, scores_df, price_cut_df = load_data()

data_through      = redfin_df["period_end"].max()
latest_month      = scores_df["period_begin"].max()
twelve_months_ago = latest_month - relativedelta(months=12)

latest_scores  = scores_df.filter(pl.col("period_begin") == latest_month)
prior_scores   = scores_df.filter(pl.col("period_begin") == twelve_months_ago)

avg_now   = latest_scores["market_score"].mean()
avg_prior = prior_scores["market_score"].mean() if len(prior_scores) > 0 else avg_now
delta     = avg_now - avg_prior

hottest = latest_scores.sort("market_score", descending=True).row(0, named=True)
coolest = latest_scores.sort("market_score").row(0, named=True)

pc_rows = price_cut_df.filter(pl.col("date") == latest_month)
pc_now  = pc_rows["price_cut_pct"][0] if len(pc_rows) > 0 else None

dom_now = redfin_df.filter(pl.col("period_begin") == latest_month)["median_days_on_market"].mean()

direction = "cooling" if delta < -3 else "heating up" if delta > 3 else "holding steady"

# ── Header ───────────────────────────────────────────────────────────────────
col_title, col_meta = st.columns([4, 1])
with col_title:
    st.title("Twin Cities East Metro — Housing Market")
with col_meta:
    redfin_mtime = Path("data/processed/redfin.csv").stat().st_mtime
    last_updated = datetime.datetime.fromtimestamp(redfin_mtime).strftime("%b %d, %Y")
    st.markdown(
        f"<p style='text-align:right; color:#666; padding-top:1.2rem;'>Updated {last_updated}</p>",
        unsafe_allow_html=True,
    )

st.markdown(
    f"<p style='color:#666;'>11 cities in the East Twin Cities metro · data through {data_through.strftime('%B %Y')}</p>",
    unsafe_allow_html=True,
)

st.divider()

# ── Snapshot metrics ─────────────────────────────────────────────────────────
st.header("Snapshot")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Metro avg score", f"{avg_now:.0f}", delta=f"{delta:+.0f} vs 1 yr ago", delta_color="off")
with col2:
    st.metric("Market direction", direction.title())
with col3:
    st.metric("Strongest market", f"{hottest['region_name']}", delta=f"{hottest['market_score']:.0f}")
with col4:
    if pc_now:
        st.metric("Price cut rate", f"{pc_now:.1f}%", help="Share of metro listings with at least one price cut")

st.divider()

# ── What's in here ───────────────────────────────────────────────────────────
st.header("What's in here")

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("**📊 Market Summary**")
    st.markdown(
        "Historical conditions across all 11 cities — score trends, price cut rate, "
        "city-by-city breakdown with year-over-year changes, and the full underlying data."
    )

with col_b:
    st.markdown("**📈 3-Month Outlook**")
    st.markdown(
        "Prophet-based forecast per city through the next 3 months, with a city selector "
        "and ranked outlook table. Includes a logged prediction you can validate when data arrives."
    )

with col_c:
    st.markdown("**📖 Methodology**")
    st.markdown(
        "Plain-English explanation of the market score — what signals are used, how they're "
        "weighted, what the forecast can and can't do, and known limitations."
    )

st.divider()

# ── About ────────────────────────────────────────────────────────────────────
st.header("About")
st.markdown("""
The **market score** is a composite index from 0 (strong buyer's market) to 100 (strong seller's market),
built from six signals: sale-to-list ratio, % sold above list price, days on market, months of supply,
pending sales, and metro-wide price cut rate. Each signal is normalized against that city's own recent
history so the score reflects relative heat, not absolute inventory scale.

Cities covered: Woodbury · Stillwater · Oak Park Heights · Maplewood · Oakdale · White Bear Lake ·
Mahtomedi · Lake Elmo · Cottage Grove · Newport · North Saint Paul

Data sourced from [Redfin Data Center](https://www.redfin.com/news/data-center/) and
[Zillow Research](https://www.zillow.com/research/data/).
This is a personal data project — not financial or real estate advice.
Open source on [GitHub](https://github.com/built-by-anthony/twin-cities-east-housing).
""")

st.info(
    "⚠️ **Work in progress.** The market score methodology is still evolving. "
    "Domain expertise welcome — especially if you have an NMLS number.",
    icon=None,
)