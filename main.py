import polars as pl
from src.redfin import redfin_housing_market_tracker_extract, redfin_housing_market_tracker_transform, redfin_housing_market_tracker_load
from src.zillow import zillow_zhvi_extract, zillow_zhvi_transform, zillow_zhvi_load, zillow_price_cut_extract, zillow_price_cut_transform
from src.market_score import compute_market_score
from src.forecast import forecast_market_score
from src.prediction_log import log_prediction

## Redfin data processing
print("starting Redfin data processing")
redfin_df = redfin_housing_market_tracker_extract()
redfin_df = redfin_housing_market_tracker_transform(redfin_df)
redfin_housing_market_tracker_load(redfin_df)

## Zillow ZHVI
print("")
print("starting Zillow ZHVI processing")
zillow_df = zillow_zhvi_transform(zillow_zhvi_extract())
zillow_zhvi_load(zillow_df)

## Zillow price cut rate (Minneapolis MSA)
# Read from raw (wide format) → transform → write processed (long format)
print("")
print("starting Zillow price cut processing")
price_cut_df = zillow_price_cut_transform(pl.read_csv("data/raw/price_cut.csv"))
price_cut_df.write_csv("data/processed/price_cut.csv")
print(f"Written {len(price_cut_df)} rows to data/processed/price_cut.csv")

## Prediction log — forecast 3 months ahead, back-fill actuals for past predictions
print("")
print("updating prediction log")
scores_df = compute_market_score(redfin_df, price_cut_df)
forecast_df = forecast_market_score(scores_df, months_ahead=3)
data_through = redfin_df["period_end"].max()
log_prediction(scores_df, data_through, forecast_df)
