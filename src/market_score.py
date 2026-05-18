import polars as pl

# Weights must sum to 1.0
WEIGHTS = {
    "avg_sale_to_list_ratio": 0.30,   # higher = seller advantage
    "share_sold_above_list":  0.30,   # higher = seller advantage
    "median_days_on_market":  0.25,   # lower  = seller advantage (inverted below)
    "active_listings":        0.15,   # lower  = seller advantage (inverted below)
}

INVERT = {"median_days_on_market", "active_listings"}


def compute_market_score(redfin_df: pl.DataFrame) -> pl.DataFrame:
    """
    Returns a score from 0 (strong buyer's market) to 100 (strong seller's market)
    per city per month. Normalized globally so trends are visible over time.
    """
    df = redfin_df.select(["region_name", "period_begin", *WEIGHTS.keys()])

    # Min-max normalize each metric across all cities and time
    for col in WEIGHTS:
        min_val = df[col].min()
        max_val = df[col].max()
        normed = ((pl.col(col) - min_val) / (max_val - min_val)).alias(f"{col}_norm")
        df = df.with_columns(normed)

    # Invert metrics where lower raw value = seller advantage
    df = df.with_columns([
        (1 - pl.col(f"{col}_norm")).alias(f"{col}_norm")
        for col in INVERT
    ])

    # Weighted sum scaled to 0–100
    score = sum(pl.col(f"{col}_norm") * weight for col, weight in WEIGHTS.items())
    df = df.with_columns((score * 100).round(1).alias("market_score"))

    return df.select(["region_name", "period_begin", "market_score"])