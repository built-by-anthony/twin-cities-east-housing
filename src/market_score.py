import polars as pl

WEIGHTS = {
    "avg_sale_to_list_ratio": 0.20,   # higher = seller advantage
    "share_sold_above_list":  0.20,   # higher = seller advantage
    "median_days_on_market":  0.20,   # lower  = seller advantage (inverted below)
    "months_of_supply":       0.15,   # lower  = seller advantage (inverted below)
    "pending_sales":          0.10,   # higher = seller advantage
    "price_cut_pct":          0.15,   # lower  = seller advantage (inverted below)
}

INVERT = {"median_days_on_market", "months_of_supply", "price_cut_pct"}

Z_CLIP = 2.0        # clip z-scores beyond ±2σ before rescaling
EWM_HALFLIFE = 12   # months; data 12 months ago contributes half the weight of today


def compute_market_score(redfin_df: pl.DataFrame, price_cut_df: pl.DataFrame) -> pl.DataFrame:
    """
    Returns a score from 0 (strong buyer's market) to 100 (strong seller's market)
    per city per month. Each metric is z-score normalized per city so the score
    reflects heat relative to that city's own history, not cross-city inventory scale.

    price_cut_df is metro-level (Minneapolis MSA) — all cities share the same monthly
    reading, so the signal contributes temporal information (is the market cutting more
    or less than usual?) rather than cross-city differentiation.
    """
    df = redfin_df.select([
        "region_name", "period_begin",
        "avg_sale_to_list_ratio", "share_sold_above_list",
        "median_days_on_market", "active_listings", "homes_sold", "pending_sales",
    ])

    # Join metro-level price cut rate by month
    df = df.join(price_cut_df, left_on="period_begin", right_on="date", how="left")

    # Months of supply normalizes inventory by sales pace — removes city-size bias
    df = df.with_columns(
        (pl.col("active_listings").cast(pl.Float64) / pl.col("homes_sold").cast(pl.Float64))
        .alias("months_of_supply")
    ).drop(["active_listings", "homes_sold"])

    # Sort so ewm runs in chronological order within each city group
    df = df.sort(["region_name", "period_begin"])

    # Per-city z-score using exponentially weighted mean/std: recent months anchor the
    # baseline more than older ones, so a rate-shock era doesn't permanently depress scores.
    # ewm_std is clipped away from zero to avoid divide-by-zero on the first observation.
    for col in WEIGHTS:
        ew_mean = pl.col(col).ewm_mean(half_life=EWM_HALFLIFE)
        ew_std  = pl.col(col).ewm_std(half_life=EWM_HALFLIFE).clip(lower_bound=1e-9)
        df = df.with_columns(
            ((pl.col(col) - ew_mean.over("region_name")) / ew_std.over("region_name"))
            .alias(f"{col}_z")
        )

    # Clip at ±2σ and rescale to [0, 1]
    for col in WEIGHTS:
        df = df.with_columns(
            ((pl.col(f"{col}_z").clip(-Z_CLIP, Z_CLIP) + Z_CLIP) / (2 * Z_CLIP))
            .alias(f"{col}_norm")
        )

    # Invert metrics where lower raw value = seller advantage
    df = df.with_columns([
        (1 - pl.col(f"{col}_norm")).alias(f"{col}_norm")
        for col in INVERT
    ])

    score = sum(pl.col(f"{col}_norm") * weight for col, weight in WEIGHTS.items())
    df = df.with_columns((score * 100).round(1).alias("market_score"))

    return df.select(["region_name", "period_begin", "market_score"])