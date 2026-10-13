# Project Documentation

This folder contains the project methodology and the handoff notes for the modernized dashboard.

## Analysis principles

1. **Use one calculation engine.** `python/marketing_analytics.py` validates the data and calculates the KPIs used by the Streamlit app.
2. **Keep denominators visible.** CTR uses impressions, conversion rate uses leads, CAC uses conversions, and ROAS/ROI use ad spend.
3. **Do not hide incomplete financials.** Missing revenue stays missing and appears as revenue coverage in the app.
4. **Separate historical evidence from planning.** The budget planner uses historical ROAS as a transparent scenario, not a forecast.
5. **Explain decisions in plain language.** Insight cards include evidence and a suggested next step so a non-technical viewer can follow the analysis.

## Current dashboard flow

- **Overview:** portfolio health and the most important actions.
- **Performance explorer:** channel and campaign comparisons.
- **Audience & trends:** audience segments and monthly funnel movement.
- **Budget planner:** controlled-test scenario using historical channel efficiency.
- **Data & help:** data-quality checks, metric dictionary, and downloads.

## Reproducibility

Run the application from the repository root:

```powershell
py -3.13 -m streamlit run app.py
```

Run the tests and syntax checks before publishing:

```powershell
py -3.13 -m pytest -q
py -3.13 -m py_compile app.py python\marketing_analytics.py
```

The browser dashboard is intentionally a local, dependency-light application. It does not require an API key, database server, ad-platform account, or cloud deployment.
