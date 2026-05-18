# Twin Cities East Metro — Housing Market

A data pipeline and interactive dashboard tracking housing market conditions across 11 cities in the east Twin Cities metro area.

**[View the dashboard →](https://twin-cities-east-housing.streamlit.app)**

## Cities covered

Woodbury, Stillwater, Oak Park Heights, Maplewood, Oakdale, White Bear Lake, Mahtomedi, Lake Elmo, Cottage Grove, Newport, North Saint Paul

## What's tracked

- **Market Score** — composite buyer/seller index (0 = buyer's market, 100 = seller's market)
- Zillow Home Value Index (ZHVI)
- Median sale price, days on market, sale-to-list ratio
- Inventory (new and active listings), homes sold, % sold above list

## Data sources

- [Redfin Data Center](https://www.redfin.com/news/data-center/) — monthly housing market metrics by city
- [Zillow Research](https://www.zillow.com/research/data/) — ZHVI (smoothed, seasonally adjusted)

## Running locally

```bash
uv pip install -r requirements.txt
uv run streamlit run dashboard.py
```

To rebuild the DuckDB from the processed CSVs:

```bash
uv run python main.py
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Domain expertise welcome — especially around the market score methodology.