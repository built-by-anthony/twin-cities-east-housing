import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import polars as pl
import pandas as pd
import datetime
from pathlib import Path
from src.redfin import redfin_housing_market_tracker_extract, redfin_housing_market_tracker_transform
from src.zillow import zillow_zhvi_extract, zillow_zhvi_transform, zillow_price_cut_extract
from src.market_score import compute_market_score
from src.forecast import forecast_market_score

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
    price_cut = zillow_price_cut_extract()
    scores = compute_market_score(redfin, price_cut)
    return redfin, zillow, scores, price_cut

# Forecast is cached separately — fitting 11 Prophet models takes ~10s
@st.cache_data
def load_forecast(scores_df, months_ahead=12):
    return forecast_market_score(scores_df, months_ahead=months_ahead)

redfin_df, zillow_df, scores_df, price_cut_df = load_data()

all_cities = sorted(zillow_df["region_name"].unique().to_list())

redfin_pd = redfin_df.sort("period_begin").to_pandas()
zillow_pd = zillow_df.sort("date").to_pandas()
scores_pd = scores_df.sort("period_begin").to_pandas()

def classify(score):
    if score >= 60:
        return "🔴 Seller"
    elif score <= 40:
        return "🟢 Buyer"
    else:
        return "⚪ Balanced"

tab_score, tab_data = st.tabs(["Market Score", "Underlying Data"])

# ── Tab 1: Market Score + Forecast ──────────────────────────────────────────
with tab_score:

    from dateutil.relativedelta import relativedelta

    with st.expander("How is this calculated?"):
        st.markdown("""
        The market score is a composite index from **0 (strong buyer's market) to 100 (strong seller's market)**.
        A score near 50 indicates a balanced market.

        It combines six signals from Redfin and Zillow data:

        | Signal | Weight | Seller-friendly when... |
        |---|---|---|
        | Avg sale-to-list ratio | 20% | Homes sell at or above asking price |
        | % sold above list price | 20% | More homes close in bidding wars |
        | Median days on market | 20% | Homes move quickly |
        | Months of supply | 15% | Inventory moves fast relative to sales pace |
        | Pending sales | 10% | More buyers are actively under contract |
        | % listings with price cut | 15% | Fewer sellers are cutting prices |

        **Normalization** uses per-city z-scores — each metric is measured relative to that city's own
        historical average. A score of 70 in Woodbury reflects the same *relative heat* as a 70 in Newport,
        regardless of their different inventory scales. Scores beyond ±2 standard deviations are clipped
        to keep outliers from distorting the index.
        """)

    with st.spinner("Fitting forecast models..."):
        forecast_df = load_forecast(scores_df, months_ahead=3)

    forecast_cities = forecast_df

    # --- Forecast line chart with city selector ---
    st.subheader("Forecast — Next 3 Months")
    top_3 = (
        scores_pd.sort_values("period_begin").groupby("region_name")["market_score"].last()
        .sort_values(ascending=False).head(3).index.tolist()
    )
    forecast_selected = st.multiselect("Select cities to compare", all_cities, default=top_3)

    if forecast_selected:
        fig = go.Figure()

        for i, city in enumerate(forecast_selected):
            color = COLORS[i % len(COLORS)]
            # Only plot forecast rows — no historical trace
            pred = (
                forecast_cities[
                    (forecast_cities["region_name"] == city) &
                    (forecast_cities["is_forecast"])
                ].sort_values("ds")
            )
            fig.add_trace(go.Scatter(
                x=pred["ds"], y=pred["yhat"], name=city,
                line=dict(color=color, width=2),
            ))

        today = str(datetime.date.today().replace(day=1))
        fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=100,
                      line=dict(color="#E8A838", dash="dot", width=1))
        this_month = datetime.date.today().strftime("%b '%y")
        fig.add_annotation(x=today, y=95, text=this_month,
                           font=dict(color="#E8A838", size=10), showarrow=False, xanchor="left")
        fig.add_hline(y=50, line_dash="dash", line_color="#555",
                      annotation_text="Neutral (50)", annotation_font_color="#888")
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=380, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(title="Score (0=buyer, 100=seller)"),
            xaxis_title="",
        )
        st.plotly_chart(fig, width="stretch")

    # --- Outlook tables side by side ---
    def outlook_table(months, label):
        target = pd.Timestamp(datetime.date.today().replace(day=1) + relativedelta(months=months))
        df = (
            forecast_cities[forecast_cities["is_forecast"]]
            .assign(dist=lambda d: (d["ds"] - target).abs())
            .sort_values("dist")
            .groupby("region_name").first().reset_index()
            [["region_name", "yhat"]]
        )
        df["Score"] = df["yhat"].map("{:.0f}".format)
        df["Outlook"] = df["yhat"].apply(classify)
        df = df.rename(columns={"region_name": "City"}).sort_values("yhat", ascending=False)
        st.markdown(f"**{label} outlook ({target.strftime('%b \'%y')})**")
        st.dataframe(df[["City", "Score", "Outlook"]], hide_index=True, use_container_width=True)

    outlook_table(3, "3 month")

    # --- Market narrative ---
    st.divider()
    from dateutil.relativedelta import relativedelta as rd

    latest_month  = scores_df["period_begin"].max()
    six_ago       = latest_month - rd(months=6)
    avg_now       = scores_df.filter(pl.col("period_begin") == latest_month)["market_score"].mean()
    avg_prior_df  = scores_df.filter(pl.col("period_begin") == six_ago)["market_score"]
    avg_prior     = avg_prior_df.mean() if len(avg_prior_df) > 0 else avg_now
    delta         = avg_now - avg_prior

    hottest = scores_df.filter(pl.col("period_begin") == latest_month).sort("market_score", descending=True).row(0, named=True)
    coolest = scores_df.filter(pl.col("period_begin") == latest_month).sort("market_score").row(0, named=True)

    pc_rows = price_cut_df.filter(pl.col("date") == latest_month)
    pc_now  = pc_rows["price_cut_pct"][0] if len(pc_rows) > 0 else None

    direction     = "cooling" if delta < -3 else "heating up" if delta > 3 else "holding steady"
    delta_phrase  = f"down {abs(delta):.0f} points" if delta < -1 else f"up {abs(delta):.0f} points" if delta > 1 else "roughly flat"
    pc_phrase     = f" {pc_now:.0f}% of listings metro-wide are carrying price cuts." if pc_now else ""

    st.markdown(f"""
**What the data is saying as of {latest_month.strftime('%B %Y')}:** The East Metro is **{direction}**.
The average score across all cities is {avg_now:.0f} — {delta_phrase} from six months ago.
**{hottest['region_name']}** ({hottest['market_score']:.0f}) is the strongest seller's market right now;
**{coolest['region_name']}** ({coolest['market_score']:.0f}) is the softest.{pc_phrase}
See the [Market Summary](?page=market_summary) page for a full breakdown.
""")

# ── Tab 2: Underlying Data ───────────────────────────────────────────────────
with tab_data:

    selected_cities = st.multiselect("Cities", all_cities, default=all_cities)
    rf = redfin_pd[redfin_pd["region_name"].isin(selected_cities)]
    zl = zillow_pd[zillow_pd["region_name"].isin(selected_cities)]

    st.subheader("Home Value Index (Zillow ZHVI)")
    fig = px.line(zl, x="date", y="zhvi", color="region_name", labels={"zhvi": "ZHVI ($)", "date": "", "region_name": "City"}, **CHART_DEFAULTS)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Median Sale Price")
        fig = px.line(rf, x="period_begin", y="median_sale_price", color="region_name", labels={"median_sale_price": "Price ($)", "period_begin": "", "region_name": "City"}, **CHART_DEFAULTS)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.subheader("Median Days on Market")
        fig = px.line(rf, x="period_begin", y="median_days_on_market", color="region_name", labels={"median_days_on_market": "Days", "period_begin": "", "region_name": "City"}, **CHART_DEFAULTS)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Inventory — New vs Active Listings")
        inventory_pd = rf[["period_begin", "region_name", "new_listings", "active_listings"]].melt(
            id_vars=["period_begin", "region_name"], var_name="type", value_name="count"
        )
        inventory_pd["type"] = inventory_pd["type"].map({"new_listings": "New", "active_listings": "Active"})
        fig = px.line(inventory_pd, x="period_begin", y="count", color="region_name", line_dash="type",
            labels={"count": "Listings", "period_begin": "", "region_name": "City", "type": ""},
            **CHART_DEFAULTS)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")

    with col4:
        st.subheader("Sale-to-List Ratio (%)")
        fig = px.line(rf, x="period_begin", y="avg_sale_to_list_ratio", color="region_name", labels={"avg_sale_to_list_ratio": "Ratio (%)", "period_begin": "", "region_name": "City"}, **CHART_DEFAULTS)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")

    col5, col6 = st.columns(2)

    with col5:
        st.subheader("Homes Sold")
        fig = px.line(rf, x="period_begin", y="homes_sold", color="region_name", labels={"homes_sold": "Homes Sold", "period_begin": "", "region_name": "City"}, **CHART_DEFAULTS)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")

    with col6:
        st.subheader("% Sold Above List Price")
        fig = px.line(rf, x="period_begin", y="share_sold_above_list", color="region_name", labels={"share_sold_above_list": "% Above List", "period_begin": "", "region_name": "City"}, **CHART_DEFAULTS)
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