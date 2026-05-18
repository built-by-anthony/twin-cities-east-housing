import polars as pl
import duckdb

EAST_METRO_CITIES = [
    "Woodbury, MN",
    "Stillwater, MN",
    "Oak Park Heights, MN",
    "Maplewood, MN",
    "Oakdale, MN",
    "White Bear Lake, MN",
    "Mahtomedi, MN",
    "Lake Elmo, MN",
    "Cottage Grove, MN",
    "Newport, MN",
    "North St. Paul, MN"
]  

def redfin_housing_market_tracker_extract() -> pl.DataFrame:
    return pl.read_csv("data/processed/redfin.csv")

def redfin_housing_market_tracker_transform(redfin_df: pl.DataFrame) -> pl.DataFrame: 
    ## City Filter
    redfin_df = redfin_df.filter(pl.col("REGION NAME").is_in(EAST_METRO_CITIES))

    # rename and reformat column names
    redfin_df = redfin_df.rename({
        "LAST UPDATED": "last_updated",
        "FREQUENCY": "frequency",
        "PERIOD BEGIN": "period_begin",
        "PERIOD END": "period_end",
        "REGION TYPE": "region_type",
        "REGION NAME": "region_name",
        "HOMES SOLD": "homes_sold",
        "MEDIAN SALE PRICE ($)": "median_sale_price",
        "MEDIAN DAYS ON MARKET (DAYS)": "median_days_on_market",
        "AVERAGE SALE TO LIST RATIO (%)": "avg_sale_to_list_ratio",
        "SHARE SOLD ABOVE ORIGINAL LIST (%)": "share_sold_above_list",
        "NEW LISTINGS": "new_listings",
        "ACTIVE LISTINGS": "active_listings",
        "PENDING SALES": "pending_sales",
    })

    # Correct data types 
    redfin_df = redfin_df.with_columns([
        pl.col("last_updated").str.to_date(),
        pl.col("period_begin").str.to_date(),
        pl.col("period_end").str.to_date(),
        pl.col("homes_sold").cast(pl.Int64),
        pl.col("median_sale_price").cast(pl.Int64),
        pl.col("median_days_on_market").cast(pl.Int64),
        pl.col("avg_sale_to_list_ratio").cast(pl.Float64),
        pl.col("share_sold_above_list").cast(pl.Float64),
        pl.col("new_listings").cast(pl.Int64),
        pl.col("active_listings").cast(pl.Int64),
        pl.col("pending_sales").cast(pl.Int64),
    ])

    redfin_df = redfin_df.drop([
        "region_type",
        "frequency",
        "last_updated",
        "period_end"
    ])

    return redfin_df

def redfin_housing_market_tracker_load(df):
    con = duckdb.connect("data/housing.duckdb")
    con.execute("CREATE OR REPLACE TABLE redfin_housing_market_tracker AS SELECT * FROM df")
    count = con.execute("SELECT COUNT(*) FROM redfin_housing_market_tracker").fetchone()[0]
    print(f"Loaded {count} rows into redfin_housing_market_tracker")
    con.close()