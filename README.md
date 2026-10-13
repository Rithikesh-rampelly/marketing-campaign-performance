# Marketing Performance Command Center

An approachable, portfolio-ready marketing analytics project that turns campaign, funnel, audience, and revenue data into clear decisions.

The repository keeps the original **Excel + MySQL + Python + Power BI** workflow and adds a modern, browser-friendly **Streamlit dashboard** with validated calculations, upload support, actionable data-health checks, exports, and a transparent budget-planning scenario.

> **Important:** This is historical analysis, not a live ad-platform connection. ROI and ROAS use recorded revenue and ad spend only; product cost, payroll, tax, fulfilment, discounts, and attribution uncertainty are outside the source dataset.

## What is new

- **Executive overview:** spend, revenue, ROAS, CAC, conversion rate, revenue coverage, trend charts, and next-step insight cards.
- **Performance explorer:** compare channels and campaigns by volume, funnel efficiency, revenue, and financial completeness.
- **Audience and trends:** explore age-group and gender segments plus monthly funnel rates.
- **Budget planner:** test an additional budget against historical channel ROAS with explicit assumptions and guardrails.
- **Bring your own CSV:** upload a UTF-8 campaign file and receive the same validation and dashboard experience.
- **Reliable analytics core:** one reusable module calculates every KPI with weighted denominators, safe division, date filtering, and validation.
- **Clear data-quality signals:** missing revenue, duplicate rows, unknown audience values, empty selections, and invalid funnel values are shown instead of silently hidden.
- **Downloads:** export the filtered data, channel/campaign analysis, and a JSON health report.
- **Test coverage:** KPI math, zero-denominator behavior, filters, validation boundaries, missing revenue, and insight generation are covered with automated tests.

## Run the dashboard

Use Python 3.10 or newer. From the repository root:

```powershell
py -3.13 -m venv .venv
\.venv\Scripts\python -m pip install -r requirements.txt
\.venv\Scripts\python -m streamlit run app.py
```

The app opens at [http://localhost:8501](http://localhost:8501). It works in current Chrome, Edge, Firefox, and Safari because the interface uses Streamlit controls and Plotly charts rather than browser-specific APIs.

If Python 3.13 is not installed, replace `py -3.13` with the supported Python version on your machine.

## Test and validate

```powershell
py -3.13 -m pytest -q
py -3.13 -m py_compile app.py python\marketing_analytics.py
py -3.13 python\generate_reports.py
```

The dashboard reads `data/cleaned/marketing_campaign_cleaned_final.csv` by default. The loader resolves that path from the repository, so the app does not depend on the folder from which Streamlit was launched.

If you need files for a presentation or a review instead of an interactive app, run `python\generate_reports.py`. It writes channel, campaign, audience, and monthly CSV summaries plus `health_report.json` to `reports/generated/`.

## Using another CSV

Select **Use another CSV** in the sidebar. A compatible file must contain:

| Column | Purpose |
| --- | --- |
| `Date` | `DD-MM-YYYY`, `DD/MM/YYYY`, or `YYYY-MM-DD` |
| `Campaign_Name` | Campaign label |
| `Channel` | Marketing channel |
| `Age_Group` | Audience age segment |
| `Gender` | Audience gender segment |
| `Impressions` | Ad views |
| `Clicks` | Ad clicks |
| `Leads` | Captured prospects |
| `Conversions` | Recorded conversions |
| `Ad_Spend` | Paid media spend in ₹ |
| `Revenue` | Attributed revenue in ₹; blank values remain missing |

`Campaign_ID` and `Customer_ID` are retained when present. Extra columns are allowed. The validator rejects negative values, nonnumeric measures, invalid dates, and impossible funnel relationships such as conversions greater than leads.

## Metric definitions

- **CTR:** clicks ÷ impressions × 100.
- **Conversion rate:** conversions ÷ leads × 100.
- **CAC:** ad spend ÷ conversions.
- **ROAS:** known revenue ÷ ad spend.
- **ROI:** (known revenue − ad spend) ÷ ad spend × 100.
- **Revenue coverage:** rows with known revenue ÷ selected rows.

Rates are calculated from aggregated totals, not by averaging row-level percentages. Undefined metrics are displayed as `—`, not infinity. Missing revenue is not changed to zero.

## Repository map

```text
app.py                              Streamlit dashboard
python/marketing_analytics.py      Validation, KPIs, filters, summaries, insights
python/01-08_*.py                   Original analysis scripts and charts
tests/                              Automated analytics tests
data/raw/                           Original source export
data/cleaned/                       Dashboard-ready cleaned CSV and Excel files
sql/                                MySQL analysis queries
powerbi/                            Power BI workbooks
screenshots/                        Existing static analysis screenshots
documentation/                      Methodology and handoff notes
```

The Power BI files remain optional portfolio artifacts. The Streamlit app is the easiest way for someone without Power BI or MySQL to explore the project.

## Analytical workflow

1. Put the source export in `data/raw/` and create or review the cleaned file in `data/cleaned/`.
2. Run the reusable validation and KPI functions in `python/marketing_analytics.py`.
3. Explore the interactive dashboard and export the filtered evidence.
4. Use SQL or Power BI for a second view of the same business questions.
5. Treat the budget planner as a controlled-test starting point, not a promise of future performance.

## Data notes

The bundled sample covers 6,000 campaign records from January through August 2026. It contains a small number of missing revenue values and unknown audience labels; the dashboard intentionally surfaces those limitations instead of hiding them.

## License and attribution

This repository preserves the original project structure and adds the analytics/dashboard layer. Review the source data and the included Power BI assets before redistributing the project outside your own portfolio.
