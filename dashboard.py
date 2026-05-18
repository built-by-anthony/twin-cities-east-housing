import streamlit as st
import plotly.express as px
import polars as pl
from pathlib import Path
from src.redfin import redfin_housing_market_tracker_extract, redfin_housing_market_tracker_transform
from src.zillow import zillow_zhvi_extract, zillow_zhvi_transform
from src.market_score import compute_market_score

st.set_page_config(page_title="Twin Cities East Housing", layout="wide")

# Custom CSS — tighten up spacing and tone down the default Streamlit chrome
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { padding-top: 1.5rem; }
    [data-testid="stSidebar"] { padding-top: 1.5rem; }
    h1 { font-size: 1.8rem !important; letter-spacing: -0.5px; }
    h2 { font-size: 1.1rem !important; color: #999 !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 1px; }
    .stAlert p { font-size: 0.85rem; }
    div[data-testid="stHorizontalBlock"] { gap: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# Color palette for charts — avoids the default Plotly rainbow
COLORS = [
    "#E8A838", "#5B8DB8", "#7DC383", "#D96B6B",
    "#A78BCD", "#E8934A", "#5BB8A8", "#B8B85B",
    "#C46BA0", "#6B8EC4", "#8EC46B"
]

CHART_DEFAULTS = dict(template="plotly_dark", color_discrete_sequence=COLORS)

col_title, col_updated = st.columns([4, 1])
with col_title:
    st.title("Twin Cities East Metro — Housing Market")
with col_updated:
    redfin_mtime = Path("data/processed/redfin.csv").stat().st_mtime
    import datetime
    last_updated = datetime.datetime.fromtimestamp(redfin_mtime).strftime("%b %d, %Y")
    st.markdown(f"<p style='text-align:right; color:#666; padding-top:1.2rem;'>Data updated {last_updated}</p>", unsafe_allow_html=True)

st.info(
    "⚠️ **Work in progress.** This dashboard is actively being developed and the methodology "
    "behind the market score is evolving. If you work in real estate or have domain expertise, "
    "contributions and feedback are welcome — open an issue or pull request on "
    "[GitHub](https://github.com/built-by-anthony/twin-cities-east-housing). "
    "Bonus points if you have an NMLS number — your data is probably better than ours.",
    icon=None,
)

# Cache data so the CSVs aren't re-read on every user interaction
@st.cache_data
def load_data():
    redfin = redfin_housing_market_tracker_transform(redfin_housing_market_tracker_extract())
    zillow = zillow_zhvi_transform(zillow_zhvi_extract())
    scores = compute_market_score(redfin)
    return redfin, zillow, scores

redfin_df, zillow_df, scores_df = load_data()

# Sidebar city filter — defaults to all cities selected
all_cities = sorted(zillow_df["region_name"].unique().to_list())
selected_cities = st.sidebar.multiselect("Cities", all_cities, default=all_cities)

# Apply city filter and sort by date for clean line charts
redfin = redfin_df.filter(pl.col("region_name").is_in(selected_cities)).sort("period_begin")
zillow = zillow_df.filter(pl.col("region_name").is_in(selected_cities)).sort("date")
scores = scores_df.filter(pl.col("region_name").is_in(selected_cities)).sort("period_begin")

# Plotly expects pandas DataFrames
redfin_pd = redfin.to_pandas()
zillow_pd = zillow.to_pandas()
scores_pd = scores.to_pandas()

# --- Buyer / Seller Score ---
# 0 = strong buyer's market, 100 = strong seller's market, 50 = neutral
st.subheader("Market Score — Buyer vs Seller")
with st.expander("How is this calculated?"):
    st.markdown("""
    The market score is a composite index from **0 (strong buyer's market) to 100 (strong seller's market)**.
    A score near 50 indicates a balanced market.

    It combines four signals from the Redfin data, each normalized to a 0–1 scale across all cities and months in the dataset:

    | Signal | Weight | Seller-friendly when... |
    |---|---|---|
    | Avg sale-to-list ratio | 30% | Homes sell at or above asking price |
    | % sold above list price | 30% | More homes close in bidding wars |
    | Median days on market | 25% | Homes move quickly |
    | Active listings | 15% | Inventory is low |

    **Normalization** uses global min/max across all cities and time periods, so scores are comparable
    both across cities and over time — a 70 in January means the same heat as a 70 in July.
    """)

chart_col, table_col = st.columns([3, 1])

with chart_col:
    fig = px.line(
        scores_pd, x="period_begin", y="market_score", color="region_name",
        labels={"market_score": "Score (0=buyer, 100=seller)", "period_begin": "", "region_name": "City"},
        range_y=[0, 100],
        **CHART_DEFAULTS,
    )
    fig.add_hline(y=50, line_dash="dash", line_color="#555", annotation_text="Neutral (50)", annotation_font_color="#888")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")

with table_col:
    # Show each city's most recent score and classify it
    def classify(score):
        if score >= 60:
            return "🔴 Seller"
        elif score <= 40:
            return "🟢 Buyer"
        else:
            return "⚪ Balanced"

    latest = (
        scores_pd.sort_values("period_begin")
        .groupby("region_name", as_index=False)
        .last()
        [["region_name", "market_score"]]
        .sort_values("market_score", ascending=False)
    )
    latest["Market"] = latest["market_score"].apply(classify)
    latest = latest.rename(columns={"region_name": "City", "market_score": "Score"})
    latest["Score"] = latest["Score"].map("{:.0f}".format)

    st.markdown("**Latest month**")
    st.dataframe(latest[["City", "Score", "Market"]], hide_index=True, use_container_width=True)

# --- Zillow ZHVI: smoothed home value estimate per city ---
st.subheader("Home Value Index (Zillow ZHVI)")
fig = px.line(zillow_pd, x="date", y="zhvi", color="region_name", labels={"zhvi": "ZHVI ($)", "date": "", "region_name": "City"}, **CHART_DEFAULTS)
fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, width="stretch")

# --- Redfin metrics: two columns per row ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Median Sale Price")
    fig = px.line(redfin_pd, x="period_begin", y="median_sale_price", color="region_name", labels={"median_sale_price": "Price ($)", "period_begin": "", "region_name": "City"}, **CHART_DEFAULTS)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")

with col2:
    st.subheader("Median Days on Market")
    fig = px.line(redfin_pd, x="period_begin", y="median_days_on_market", color="region_name", labels={"median_days_on_market": "Days", "period_begin": "", "region_name": "City"}, **CHART_DEFAULTS)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")

col3, col4 = st.columns(2)

with col3:
    st.subheader("Inventory — New vs Active Listings")
    # Melt both listing columns so they appear as separate series on one chart
    inventory_pd = redfin_pd[["period_begin", "region_name", "new_listings", "active_listings"]].melt(
        id_vars=["period_begin", "region_name"], var_name="type", value_name="count"
    )
    inventory_pd["type"] = inventory_pd["type"].map({"new_listings": "New", "active_listings": "Active"})
    fig = px.line(inventory_pd, x="period_begin", y="count", color="region_name", line_dash="type",
        labels={"count": "Listings", "period_begin": "", "region_name": "City", "type": ""},
        **CHART_DEFAULTS)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")

with col4:
    # Values above 100% mean homes are selling over asking price
    st.subheader("Sale-to-List Ratio (%)")
    fig = px.line(redfin_pd, x="period_begin", y="avg_sale_to_list_ratio", color="region_name", labels={"avg_sale_to_list_ratio": "Ratio (%)", "period_begin": "", "region_name": "City"}, **CHART_DEFAULTS)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")

col5, col6 = st.columns(2)

with col5:
    st.subheader("Homes Sold")
    fig = px.line(redfin_pd, x="period_begin", y="homes_sold", color="region_name", labels={"homes_sold": "Homes Sold", "period_begin": "", "region_name": "City"}, **CHART_DEFAULTS)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")

with col6:
    # Share of homes that closed above the original list price — a market heat indicator
    st.subheader("% Sold Above List Price")
    fig = px.line(redfin_pd, x="period_begin", y="share_sold_above_list", color="region_name", labels={"share_sold_above_list": "% Above List", "period_begin": "", "region_name": "City"}, **CHART_DEFAULTS)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")

st.divider()
st.markdown(
    "<p style='color:#555; font-size:0.8rem;'>Data sourced from "
    "<a href='https://www.redfin.com/news/data-center/' style='color:#666;'>Redfin Data Center</a> and "
    "<a href='https://www.zillow.com/research/data/' style='color:#666;'>Zillow Research</a>. "
    "Not financial or real estate advice.</p>",
    unsafe_allow_html=True
)
