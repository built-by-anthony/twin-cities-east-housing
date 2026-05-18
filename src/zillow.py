import polars as pl
import duckdb

def zillow_zhvi_extract() -> pl.DataFrame:
    return pl.read_csv("data/processed/zillow.csv")

def zillow_zhvi_transform(df: pl.DataFrame) -> pl.DataFrame:
    id_cols = ["RegionID", "SizeRank", "RegionName", "RegionType", "StateName", "State", "Metro", "CountyName"]

    EAST_METRO_CITIES = [
        "Woodbury",
        "Stillwater",
        "Oak Park Heights",
        "Maplewood",
        "Oakdale",
        "White Bear Lake",
        "Mahtomedi",
        "Lake Elmo",
        "Cottage Grove",
        "Newport",
        "North Saint Paul"
    ]
    
    df = df.filter(pl.col("State") == "MN").unpivot(
        on=[c for c in df.columns if c not in id_cols],
        index=id_cols,
        variable_name="date",
        value_name="zhvi"
    )

    df = df.filter(pl.col("date") >= "2023-01-01")

    df = df.filter(pl.col("RegionName").is_in(EAST_METRO_CITIES))

    df = df.rename({
        "RegionID" : "region_id",
        "SizeRank" : "size_rank",
        "RegionName" : "region_name",
        "RegionType" : "region_type",
        "StateName" : "state_name",
        "State" : "state",
        "Metro" : "metro",
        "CountyName" : "county_name"

    })

    df = df.with_columns([
        pl.col("date").str.to_date(),
        pl.col("zhvi").round(0).cast(pl.Int64)
    ])

    df = df.drop([
        "region_type",
        "size_rank",
        "state_name",
        "state"
    ])

    return df

def zillow_zhvi_load(df): 
    con = duckdb.connect("data/housing.duckdb")
    con.execute("CREATE OR REPLACE TABLE zillow_zhvi AS SELECT * FROM df")
    count = con.execute("SELECT COUNT(*) FROM zillow_zhvi").fetchone()[0]
    print(f"Loaded {count} rows into zillow_zhvi")
    con.close()