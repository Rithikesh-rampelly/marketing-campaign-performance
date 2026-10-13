# Data guide

The dashboard uses `cleaned/marketing_campaign_cleaned_final.csv` as its default source. It is a UTF-8 CSV with the required campaign, funnel, audience, spend, and revenue columns.

The `raw/` folder preserves the original source export. The cleaned folder also contains the working Excel/CSV artifacts from the original analysis. Do not overwrite the raw source when cleaning a new extract; save a versioned cleaned output instead.

## Cleaning checklist

- Keep one row per campaign/date/audience record.
- Use a supported date format: `DD-MM-YYYY`, `DD/MM/YYYY`, or `YYYY-MM-DD`.
- Keep counts nonnegative and ensure `Impressions >= Clicks >= Leads >= Conversions`.
- Leave unknown audience values as blank or `Unknown`; the dashboard reports them.
- Leave unavailable revenue blank rather than changing it to zero.
- Confirm currency and attribution rules before using ROAS/ROI for a real budget decision.
