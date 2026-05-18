# Contributing

Thanks for your interest in improving this project. Contributions from people with real estate or housing market experience are especially welcome — the methodology behind the market score is a work in progress and benefits from domain knowledge.

## Ways to contribute

- **Open an issue** to suggest a new metric, flag a flaw in the scoring logic, or report a bug
- **Open a pull request** to propose a code change

## Before opening a pull request

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Test locally with `uv run streamlit run dashboard.py`
4. Open a PR with a clear description of what you changed and why

All PRs require approval before merging. For changes to the market score methodology, please explain your reasoning in the PR description — ideally with a source or reference if you're adjusting weights or adding signals.

## Project structure

```
src/
  redfin.py        — extract, transform, load for Redfin data
  zillow.py        — extract, transform, load for Zillow ZHVI data
  market_score.py  — composite buyer/seller score calculation
dashboard.py       — Streamlit app
main.py            — runs the full pipeline and writes to DuckDB
data/raw/          — source CSV files
```

## Questions

Open an issue and tag it `question`.