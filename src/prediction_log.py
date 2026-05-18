import datetime
import pandas as pd
import polars as pl
from pathlib import Path
from dateutil.relativedelta import relativedelta

LOG_PATH = Path("data/processed/prediction_log.csv")

COLUMNS = [
    "logged_at",       # date this prediction was written
    "data_through",    # period_end of latest Redfin data at time of prediction
    "forecast_month",  # first day of the month being predicted (3 months out)
    "predicted_avg",   # predicted metro-average market score
    "actual_avg",      # filled in once that month's data is available
]


def log_prediction(scores_df: pl.DataFrame, data_through: datetime.date, forecast_df: pd.DataFrame) -> None:
    """Append a 3-month-ahead prediction to the log, then back-fill any actuals."""
    today = datetime.date.today()
    target_month = (today.replace(day=1) + relativedelta(months=3))

    # Metro-average predicted score for target_month
    pred_rows = forecast_df[
        forecast_df["is_forecast"] &
        (forecast_df["ds"].dt.to_period("M") == pd.Period(target_month, "M"))
    ]
    if pred_rows.empty:
        return
    predicted_avg = round(pred_rows["yhat"].mean(), 1)

    # Load existing log or start fresh
    if LOG_PATH.exists():
        log = pd.read_csv(LOG_PATH, parse_dates=["logged_at", "data_through", "forecast_month"])
    else:
        log = pd.DataFrame(columns=COLUMNS)

    # Skip if we already have an entry for this data_through date
    if len(log) > 0 and (log["data_through"] == pd.Timestamp(data_through)).any():
        pass
    else:
        new_row = pd.DataFrame([{
            "logged_at":      today,
            "data_through":   data_through,
            "forecast_month": target_month,
            "predicted_avg":  predicted_avg,
            "actual_avg":     None,
        }])
        log = pd.concat([log, new_row], ignore_index=True)

    # Back-fill actuals: for any row whose forecast_month is now in the scores data
    actual_avgs = (
        scores_df
        .group_by("period_begin")
        .agg(pl.col("market_score").mean().alias("avg"))
        .to_pandas()
        .rename(columns={"period_begin": "month", "avg": "avg_score"})
    )
    for i, row in log.iterrows():
        if pd.isna(row["actual_avg"]):
            fm = pd.Timestamp(row["forecast_month"])
            match = actual_avgs[actual_avgs["month"].apply(lambda d: pd.Timestamp(d).to_period("M")) == fm.to_period("M")]
            if not match.empty:
                log.at[i, "actual_avg"] = round(match["avg_score"].values[0], 1)

    log.to_csv(LOG_PATH, index=False)
    print(f"Prediction log updated: {len(log)} entries ({LOG_PATH})")