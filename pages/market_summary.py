import streamlit as st
import polars as pl
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
from src.redfin import redfin_housing_market_tracker_extract, redfin_housing_market_tracker_transform
from src.zillow import zillow_price_cut_extract
from src.market_score import compute_market_score

st.set_page_config(page_title="Market Summary — Twin Cities East Housing", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { padding-top: 1.5rem; }
    h1 { font-size: 1.8rem !important; letter-spacing: -0.5px; }
    h2 { font-size: 1.1rem !important; color: #999 !important; font-weight: 500 !important;
         text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

COLORS = [
    "#E8A838", "#5B8DB8", "#7DC383", "#D96B6B",
    "#A78BCD", "#E8934A", "#5BB8A8", "#B8B85B",
    "#C46BA0", "#6B8EC4", "#8EC46B"
]
CHART_DEFAULTS = dict(template="plotly_dark", color_discrete_sequence=COLORS)


@st.cache_data
def load_data():
    redfin = redfin_housing_market_tracker_transform(redfin_housing_market_tracker_extract())
    price_cut = zillow_price_cut_extract()
    scores = compute_market_score(redfin, price_cut)
    return redfin, scores, price_cut


redfin_df, scores_df, price_cut_df = load_data()

latest_month    = scores_df["period_begin"].max()
six_months_ago  = latest_month - relativedelta(months=6)
twelve_months_ago = latest_month - relativedelta(months=12)

latest_scores = scores_df.filter(pl.col("period_begin") == latest_month)
prior_6_scores = scores_df.filter(pl.col("period_begin") == six_months_ago)

avg_now   = latest_scores["market_score"].mean()
avg_prior = prior_6_scores["market_score"].mean() if len(prior_6_scores) > 0 else avg_now
delta     = avg_now - avg_prior

hottest = latest_scores.sort("market_score", descending=True).row(0, named=True)
coolest = latest_scores.sort("market_score").row(0, named=True)

pc_now_df   = price_cut_df.filter(pl.col("date") == latest_month)
pc_prior_df = price_cut_df.filter(pl.col("date") == twelve_months_ago)
pc_now   = pc_now_df["price_cut_pct"][0] if len(pc_now_df) > 0 else None
pc_prior = pc_prior_df["price_cut_pct"][0] if len(pc_prior_df) > 0 else None

dom_now   = redfin_df.filter(pl.col("period_begin") == latest_month)["median_days_on_market"].mean()
dom_prior = redfin_df.filter(pl.col("period_begin") == six_months_ago)["median_days_on_market"].mean()

mos_df = redfin_df.with_columns(
    (pl.col("active_listings").cast(pl.Float64) / pl.col("homes_sold").cast(pl.Float64)).alias("mos")
)
mos_now   = mos_df.filter(pl.col("period_begin") == latest_month)["mos"].mean()
mos_prior = mos_df.filter(pl.col("period_begin") == six_months_ago)["mos"].mean()

# ── Page ─────────────────────────────────────────────────────────────────────

st.title("Market Summary")
st.markdown(
    f"<p style='color:#666; font-size:0.9rem;'>Historical analysis and current conditions — "
    f"as of {latest_month.strftime('%B %Y')}</p>",
    unsafe_allow_html=True,
)

st.divider()

# ── Current conditions ───────────────────────────────────────────────────────
st.header("Current conditions")

direction   = "cooling" if delta < -3 else "heating up" if delta > 3 else "holding steady"
delta_str   = f"down {abs(delta):.0f} pts" if delta < -1 else f"up {abs(delta):.0f} pts" if delta > 1 else "flat"
mkt_label   = "a seller's market" if avg_now >= 60 else "a buyer's market" if avg_now <= 40 else "balanced territory"
pc_sentence = f" {pc_now:.0f}% of metro listings are carrying a price cut" + (f", up {pc_now-pc_prior:.0f}pp from a year ago" if pc_prior else "") + "." if pc_now else ""

st.markdown(f"""
The East Metro is **{direction}**. The average market score is **{avg_now:.0f}** ({delta_str} from 6 months ago),
putting the metro in **{mkt_label}** on the whole. **{hottest['region_name']}** ({hottest['market_score']:.0f})
leads as the strongest seller's market; **{coolest['region_name']}** ({coolest['market_score']:.0f}) is
the softest.{pc_sentence}
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Avg market score", f"{avg_now:.0f}", delta=f"{delta:+.0f} vs 6 months ago", delta_color="off")
with col2:
    st.metric("Avg days on market", f"{dom_now:.0f} days", delta=f"{dom_now - dom_prior:+.0f} vs 6 months ago", delta_color="inverse")
with col3:
    if pc_now:
        st.metric("Price cut rate", f"{pc_now:.1f}%", delta=f"{pc_now - pc_prior:+.1f}pp vs 12 months ago" if pc_prior else None, delta_color="inverse")

st.divider()

# ── Historical market score ──────────────────────────────────────────────────
st.header("Market score — full history")

scores_pd = scores_df.sort("period_begin").to_pandas()
fig = px.line(
    scores_pd, x="period_begin", y="market_score", color="region_name",
    labels={"market_score": "Score", "period_begin": "", "region_name": "City"},
    **CHART_DEFAULTS,
)
fig.add_hline(y=60, line_dash="dash", line_color="#D96B6B", annotation_text="Seller (60)", annotation_font_color="#D96B6B")
fig.add_hline(y=40, line_dash="dash", line_color="#7DC383", annotation_text="Buyer (40)", annotation_font_color="#7DC383")
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    height=420, margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig, width="stretch")

st.divider()

# ── Price cut rate history ───────────────────────────────────────────────────
st.header("Minneapolis metro — price cut rate")
st.markdown("Share of active listings with at least one price reduction. A leading indicator of seller capitulation — typically leads closed-sale metrics by 4–8 weeks.")

pc_pd = price_cut_df.sort("date").to_pandas()
fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=pc_pd["date"], y=pc_pd["price_cut_pct"],
    fill="tozeroy", line=dict(color="#E8A838", width=2),
    fillcolor="rgba(232,168,56,0.15)", name="Price cut %",
))
fig2.add_hline(y=20, line_dash="dash", line_color="#555",
               annotation_text="20% baseline", annotation_font_color="#888")
fig2.update_layout(
    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    height=300, margin=dict(l=0, r=0, t=10, b=0),
    yaxis_title="% of listings with a price cut", xaxis_title="",
    showlegend=False,
)
st.plotly_chart(fig2, width="stretch")

st.divider()

# ── City-by-city table ───────────────────────────────────────────────────────
st.header("City breakdown")

rows = []
for row in latest_scores.sort("market_score", descending=True).iter_rows(named=True):
    prior = prior_6_scores.filter(pl.col("region_name") == row["region_name"])
    prior_score = prior["market_score"][0] if len(prior) > 0 else None
    change = row["market_score"] - prior_score if prior_score is not None else None
    rows.append({
        "City": row["region_name"],
        "Score": f"{row['market_score']:.0f}",
        "6-mo change": f"{change:+.0f}" if change is not None else "—",
        "Condition": ("🔴 Seller" if row["market_score"] >= 60
                      else "🟢 Buyer" if row["market_score"] <= 40
                      else "⚪ Balanced"),
    })

st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

st.divider()
st.markdown(
    "<p style='color:#555; font-size:0.8rem;'>Data sourced from "
    "<a href='https://www.redfin.com/news/data-center/' style='color:#666;'>Redfin Data Center</a> and "
    "<a href='https://www.zillow.com/research/data/' style='color:#666;'>Zillow Research</a>. "
    "Not financial or real estate advice.</p>",
    unsafe_allow_html=True,
)
