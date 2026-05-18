import pandas as pd
import polars as pl
from prophet import Prophet


def forecast_market_score(scores_df: pl.DataFrame, months_ahead: int = 3) -> pd.DataFrame:
    """
    Fits a Prophet model per city on the historical market score and forecasts
    through today + `months_ahead` months. Returns a combined historical + forecast DataFrame.

    Note: city-level Redfin data only goes back to Jan 2023 (38 months). Forecasts
    beyond 3 months are unreliable with this training window — do not extend months_ahead
    until a longer historical dataset is available.
    """
    import datetime
    from dateutil.relativedelta import relativedelta

    target_end = (datetime.date.today().replace(day=1) + relativedelta(months=months_ahead))
    results = []

    for city in scores_df["region_name"].unique().to_list():
        city_pd = (
            scores_df.filter(pl.col("region_name") == city)
            .to_pandas()
            .rename(columns={"period_begin": "ds", "market_score": "y"})
            [["ds", "y"]]
            .sort_values("ds")
        )

        last_date = city_pd["ds"].max().date()
        months_needed = (target_end.year - last_date.year) * 12 + (target_end.month - last_date.month)
        periods = max(months_needed, 1)

        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.01,
        )
        model.fit(city_pd, iter=300)

        future = model.make_future_dataframe(periods=periods, freq="MS")
        forecast = model.predict(future)

        last_historical = city_pd["ds"].max()
        forecast["region_name"] = city
        forecast["is_forecast"] = forecast["ds"] > last_historical
        forecast["yhat"]       = forecast["yhat"].clip(0, 100).round(1)
        forecast["yhat_lower"] = forecast["yhat_lower"].clip(0, 100).round(1)
        forecast["yhat_upper"] = forecast["yhat_upper"].clip(0, 100).round(1)

        results.append(forecast[["region_name", "ds", "yhat", "yhat_lower", "yhat_upper", "is_forecast"]])

    return pd.concat(results).reset_index(drop=True)