import polars as pl
from src.redfin import redfin_housing_market_tracker_extract,  redfin_housing_market_tracker_transform, redfin_housing_market_tracker_load
from src.zillow import zillow_zhvi_extract, zillow_zhvi_transform, zillow_zhvi_load

## Redfin data processing 
print("starting Redfin data processing")
redfin_df = redfin_housing_market_tracker_extract()
redfin_df = redfin_housing_market_tracker_transform(redfin_df)
redfin_housing_market_tracker_load(redfin_df)

## Zillow data procesing 
print("")
print("starting Zillow data processing")
zillow_df = zillow_zhvi_extract()
zillow_df = zillow_zhvi_transform(zillow_df)
zillow_zhvi_load(zillow_df)