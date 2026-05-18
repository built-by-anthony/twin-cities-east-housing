import streamlit as st
import plotly.graph_objects as go
import polars as pl
import pandas as pd
import datetime
from pathlib import Path
from dateutil.relativedelta import relativedelta
from src.redfin import redfin_housing_market_tracker_extract, redfin_housing_market_tracker_transform
from src.zillow import zillow_zhvi_extract, zillow_zhvi_transform, zillow_price_cut_extract
from src.market_score import compute_market_score
from src.forecast import forecast_market_score

st.set_page_config(page_title="3-Month Outlook — Twin Cities East Housing", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { padding-top: 1.5rem; }
    h1 { font-size: 1.8rem !important; letter-spacing: -0.5px; }
    h2 { font-size: 1.1rem !important; color: #999 !important; font-weight: 500 !important;
         text-transform: uppercase; letter-spacing: 1px; }
    .stAlert p { font-size: 0.85rem; }
    div[data-testid="stHorizontalBlock"] { gap: 1.5rem; }
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
    zillow = zillow_zhvi_transform(zillow_zhvi_extract())
    price_cut = zillow_price_cut_extract()
    scores = compute_market_score(redfin, price_cut)
    return redfin, zillow, scores, price_cut


@st.cache_data
def load_forecast(scores_df, months_ahead=3):
    return forecast_market_score(scores_df, months_ahead=months_ahead)


redfin_df, zillow_df, scores_df, price_cut_df = load_data()

all_cities = sorted(zillow_df["region_name"].unique().to_list())
data_through = redfin_df["period_end"].max()

scores_pd = scores_df.sort("period_begin").to_pandas()


def classify(score):
    if score >= 60:
        return "🔴 Seller"
    elif score <= 40:
        return "🟢 Buyer"
    else:
        return "⚪ Balanced"


st.title("3-Month Outlook")
st.markdown(
    f"<p style='color:#666; font-size:0.9rem;'>City-level forecast — data through {data_through.strftime('%B %Y')}</p>",
    unsafe_allow_html=True,
)

st.info(
    "⚠️ **Work in progress.** This dashboard is actively being developed. "
    "If you work in real estate or have domain expertise, contributions and feedback are welcome — "
    "open an issue or pull request on [GitHub](https://github.com/built-by-anthony/twin-cities-east-housing). "
    "Bonus points if you have an NMLS number — your data is probably better than ours.",
    icon=None,
)

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

    **Normalization** uses per-city exponentially weighted z-scores — each metric is measured relative
    to that city's own recent average (12-month half-life), so a score of 70 in Woodbury reflects the
    same *relative heat* as a 70 in Newport.
    """)

with st.spinner("Fitting forecast models..."):
    forecast_df = load_forecast(scores_df, months_ahead=3)

# ── Forecast line chart ──────────────────────────────────────────────────────
st.header("Forecast — next 3 months")
top_3 = (
    scores_pd.sort_values("period_begin").groupby("region_name")["market_score"].last()
    .sort_values(ascending=False).head(3).index.tolist()
)
forecast_selected = st.multiselect("Select cities to compare", all_cities, default=top_3)

if forecast_selected:
    fig = go.Figure()
    for i, city in enumerate(forecast_selected):
        color = COLORS[i % len(COLORS)]
        pred = (
            forecast_df[
                (forecast_df["region_name"] == city) &
                (forecast_df["is_forecast"])
            ].sort_values("ds")
        )
        fig.add_trace(go.Scatter(
            x=pred["ds"], y=pred["yhat"], name=city,
            line=dict(color=color, width=2),
        ))
    today = str(datetime.date.today().replace(day=1))
    fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=100,
                  line=dict(color="#E8A838", dash="dot", width=1))
    fig.add_annotation(x=today, y=95, text=datetime.date.today().strftime("%b '%y"),
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

# ── Outlook table ────────────────────────────────────────────────────────────
def outlook_table(months, label):
    target = pd.Timestamp(datetime.date.today().replace(day=1) + relativedelta(months=months))
    df = (
        forecast_df[forecast_df["is_forecast"]]
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

# ── Market narrative ─────────────────────────────────────────────────────────
st.divider()

latest_month = scores_df["period_begin"].max()
twelve_ago   = latest_month - relativedelta(months=12)
avg_now      = scores_df.filter(pl.col("period_begin") == latest_month)["market_score"].mean()
avg_prior_df = scores_df.filter(pl.col("period_begin") == twelve_ago)["market_score"]
avg_prior    = avg_prior_df.mean() if len(avg_prior_df) > 0 else avg_now
delta        = avg_now - avg_prior

hottest = scores_df.filter(pl.col("period_begin") == latest_month).sort("market_score", descending=True).row(0, named=True)
coolest = scores_df.filter(pl.col("period_begin") == latest_month).sort("market_score").row(0, named=True)

pc_rows  = price_cut_df.filter(pl.col("date") == latest_month)
pc_now   = pc_rows["price_cut_pct"][0] if len(pc_rows) > 0 else None

direction    = "cooling" if delta < -3 else "heating up" if delta > 3 else "holding steady"
delta_phrase = f"down {abs(delta):.0f} points" if delta < -1 else f"up {abs(delta):.0f} points" if delta > 1 else "roughly flat"
pc_phrase    = f" {pc_now:.0f}% of listings metro-wide are carrying price cuts." if pc_now else ""

_pred_sentence = ""
_log_path = Path("data/processed/prediction_log.csv")
if _log_path.exists():
    _log = pd.read_csv(_log_path, parse_dates=["logged_at", "forecast_month"])
    if len(_log) > 0:
        _latest = _log.sort_values("logged_at").iloc[-1]
        _fm = pd.Timestamp(_latest["forecast_month"]).strftime("%B %Y")
        _pred = _latest["predicted_avg"]
        _pred_label = "seller's market" if _pred >= 60 else "buyer's market" if _pred <= 40 else "balanced territory"
        _pred_sentence = f" The 3-month outlook points to a metro average of **{_pred:.0f}** by {_fm} — {_pred_label}."

st.markdown(f"""
**What the data is saying as of {data_through.strftime('%B %Y')}:** The East Metro is **{direction}**.
The average score across all cities is {avg_now:.0f} — {delta_phrase} from a year ago.
**{hottest['region_name']}** ({hottest['market_score']:.0f}) is the strongest seller's market right now;
**{coolest['region_name']}** ({coolest['market_score']:.0f}) is the softest.{pc_phrase}{_pred_sentence}
See the [Market Summary](/market_summary) page for a full breakdown.
""")

st.divider()
st.markdown(
    "<p style='color:#555; font-size:0.8rem;'>Data sourced from "
    "<a href='https://www.redfin.com/news/data-center/' style='color:#666;'>Redfin Data Center</a> and "
    "<a href='https://www.zillow.com/research/data/' style='color:#666;'>Zillow Research</a>. "
    "Not financial or real estate advice.</p>",
    unsafe_allow_html=True,
)