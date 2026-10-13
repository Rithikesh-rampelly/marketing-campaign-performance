"""Reusable, side-effect-free marketing analytics for the cleaned campaign CSV.

Example::

    from python.marketing_analytics import load_data, filter_data, health_summary
    data = filter_data(load_data(), start_date="2026-01-01", channels=["Email"])
    dashboard = health_summary(data)

CTR, conversion_rate_percent (conversions / leads), and ROI are percentages;
ROAS is a multiple. Profit is revenue minus ad spend, excluding other costs.
Ratios are calculated from summed amounts, never averaged from row-level rates.
Undefined scalar metrics are None (NaN in summary DataFrames), never infinity.

The source CSV contains missing Revenue values. They remain missing: reported
revenue and financial ratios use *known* revenue and are partial whenever
missing_revenue_rows is nonzero. With no known revenue, those metrics are None.
Every summary exposes completeness, and health/insights flag partial financials.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from math import fsum, isfinite
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data" / "cleaned" / "marketing_campaign_cleaned_final.csv"
)
COUNT_COLUMNS = ("Impressions", "Clicks", "Leads", "Conversions")
NUMERIC_COLUMNS = (*COUNT_COLUMNS, "Ad_Spend", "Revenue")
DIMENSION_COLUMNS = ("Channel", "Campaign_Name", "Age_Group", "Gender")
REQUIRED_COLUMNS = ("Date", *DIMENSION_COLUMNS, *NUMERIC_COLUMNS)
MIN_DATE = pd.Timestamp("1900-01-01")
MAX_DATE = pd.Timestamp("2100-12-31")
# Bound individual values and totals to the exact-integer range of float64.
MAX_SAFE_NUMBER = 2**53 - 1
GROUP_DIMENSIONS = {
    "channel": "Channel",
    "campaign": "Campaign_Name",
    "age_group": "Age_Group",
    "gender": "Gender",
    "month": "Month",
}
KPI_COLUMNS = (
    "total_ad_spend", "total_revenue", "total_impressions", "total_clicks",
    "total_leads", "total_conversions", "ctr_percent", "conversion_rate_percent",
    "cac", "roas", "roi_percent", "profit", "row_count", "missing_revenue_rows",
    "revenue_coverage_percent", "financials_complete",
)
CHANNEL_NAMES = {
    "google ads": "Google Ads", "instagram": "Instagram", "youtube": "YouTube",
    "facebook": "Facebook", "email": "Email",
}
KPIResult = dict[str, int | float | bool | None]
DateInput = str | date | datetime | pd.Timestamp


def _parse_dates(values: pd.Series, label: str = "Date") -> pd.Series:
    """Accept unambiguous ISO dates, the source's day-first dates, or datetimes."""
    if pd.api.types.is_datetime64_any_dtype(values.dtype):
        if values.dt.tz is not None:
            raise ValueError(f"{label} must contain timezone-naive calendar dates")
        parsed = values.dt.normalize()
    else:
        text = values.astype("string").str.strip()
        parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
        formats = (
            (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
            (r"\d{1,2}-\d{1,2}-\d{4}", "%d-%m-%Y"),
            (r"\d{1,2}/\d{1,2}/\d{4}", "%d/%m/%Y"),
        )
        for pattern, date_format in formats:
            mask = text.str.fullmatch(pattern, na=False)
            converted = pd.to_datetime(text[mask], format=date_format, errors="coerce")
            # Check before casting to ns; pandas can also represent broader dates.
            valid = converted.between(MIN_DATE, MAX_DATE)
            parsed.loc[converted[valid].index] = converted[valid].astype("datetime64[ns]")
    valid = parsed.notna() & parsed.between(MIN_DATE, MAX_DATE)
    if not valid.all():
        raise ValueError(
            f"{label} contains {int((~valid).sum())} missing, invalid, or out-of-range "
            "date(s); use DD-MM-YYYY, DD/MM/YYYY, or YYYY-MM-DD between "
            "1900-01-01 and 2100-12-31"
        )
    return parsed.astype("datetime64[ns]")


def validate_data(data: pd.DataFrame) -> pd.DataFrame:
    """Return a normalized copy or raise ValueError with the invalid column.

    Dates must fall in 1900..2100. Counts must be finite nonnegative integers,
    and the funnel must satisfy impressions >= clicks >= leads >= conversions.
    Spend and known revenue must be finite/nonnegative; values and column totals
    cannot exceed MAX_SAFE_NUMBER. Missing revenue is allowed and tracked; other
    missing numeric values are errors. Blank dimensions become 'Unknown'.
    Campaign_ID/Customer_ID and extra columns are optional and retained.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")
    result = data.copy(deep=True)
    result.columns = [col.strip() if isinstance(col, str) else col for col in result.columns]
    if result.columns.duplicated().any():
        raise ValueError("Duplicate column names are not supported")
    missing = sorted(set(REQUIRED_COLUMNS) - set(result.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    # A temporary unique index keeps normalization correct for concatenated frames.
    original_index = result.index
    result = result.reset_index(drop=True)
    result["Date"] = _parse_dates(result["Date"])
    for column in NUMERIC_COLUMNS:
        text = result[column].astype("string").str.strip().replace("", pd.NA)
        numeric = pd.to_numeric(text, errors="coerce")
        if (numeric.isna() & text.notna()).any():
            raise ValueError(f"{column} contains nonnumeric values")
        if column != "Revenue" and numeric.isna().any():
            raise ValueError(f"{column} contains missing values")
        values = numeric.to_numpy(dtype="float64", na_value=np.nan)
        known = values[~np.isnan(values)]
        if not np.isfinite(known).all():
            raise ValueError(f"{column} must contain only finite values")
        if (known < 0).any() or (known > MAX_SAFE_NUMBER).any():
            raise ValueError(f"{column} must be between 0 and {MAX_SAFE_NUMBER}")
        if column in COUNT_COLUMNS and (known != np.floor(known)).any():
            raise ValueError(f"{column} must contain whole-number counts")
        if fsum(known) > MAX_SAFE_NUMBER:
            raise ValueError(f"{column} total exceeds the safe numeric range")
        result[column] = values.astype("int64") if column in COUNT_COLUMNS else values

    for larger, smaller in zip(COUNT_COLUMNS, COUNT_COLUMNS[1:]):
        if (result[smaller] > result[larger]).any():
            raise ValueError(f"{smaller} cannot exceed {larger}")
    for column in (*DIMENSION_COLUMNS, "Campaign_ID", "Customer_ID"):
        if column in result:
            result[column] = result[column].astype("string").str.strip().replace("", pd.NA)
            if column in DIMENSION_COLUMNS:
                result[column] = result[column].fillna("Unknown")
    channel_keys = result["Channel"].str.casefold()
    result["Channel"] = channel_keys.map(CHANNEL_NAMES).fillna(result["Channel"])
    result.index = original_index
    return result


def load_data(path: str | Path | None = None) -> pd.DataFrame:
    """Load and validate the final cleaned CSV, independent of the working directory.

    Explicit relative paths are relative to the caller's working directory.
    UTF-8 BOMs, surrounding header/category whitespace, and numeric text are
    supported. Malformed rows or invalid values fail loudly instead of being lost.
    """
    source = DEFAULT_DATA_PATH if path is None else Path(path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"Marketing CSV not found: {source}")
    try:
        data = pd.read_csv(source, encoding="utf-8-sig", dtype="string", keep_default_na=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeError) as exc:
        raise ValueError(f"Unable to read marketing CSV {source}: {exc}") from exc
    return validate_data(data)


def _selection(values: Iterable[str] | str) -> set[str]:
    values = [values] if isinstance(values, str) else values
    selections = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError("Channel/campaign selections must be strings")
        selections.add(value.strip().casefold())
    return selections


def filter_data(
    data: pd.DataFrame,
    *,
    start_date: DateInput | None = None,
    end_date: DateInput | None = None,
    channels: Iterable[str] | str | None = None,
    campaigns: Iterable[str] | str | None = None,
) -> pd.DataFrame:
    """Apply inclusive calendar dates and case-insensitive channel/campaign filters.

    Campaign selections match names or, when present, Campaign_ID. None means
    unfiltered; an empty selection means no rows. Input data is never mutated.
    """
    result = validate_data(data)
    start = None if start_date is None else _parse_dates(pd.Series([start_date]), "start_date").iloc[0]
    end = None if end_date is None else _parse_dates(pd.Series([end_date]), "end_date").iloc[0]
    if start is not None and end is not None and start > end:
        raise ValueError("start_date must not be after end_date")
    mask = pd.Series(True, index=result.index)
    if start is not None:
        mask &= result["Date"] >= start
    if end is not None:
        mask &= result["Date"] <= end
    if channels is not None:
        mask &= result["Channel"].str.casefold().isin(_selection(channels))
    if campaigns is not None:
        selected = _selection(campaigns)
        matches = result["Campaign_Name"].str.casefold().isin(selected)
        if "Campaign_ID" in result:
            matches |= result["Campaign_ID"].str.casefold().isin(selected)
        mask &= matches
    return result.loc[mask].copy()


def _ratio(numerator: float | None, denominator: float, scale: float = 1.0) -> float | None:
    if numerator is None or denominator == 0:
        return None
    value = numerator / denominator * scale
    return float(value) if isfinite(value) else None


def _calculate_kpis(data: pd.DataFrame) -> KPIResult:
    spend = fsum(data["Ad_Spend"])
    known_revenue = data["Revenue"].dropna()
    revenue = fsum(known_revenue) if not known_revenue.empty or data.empty else None
    counts = {column: int(data[column].sum()) for column in COUNT_COLUMNS}
    profit = None if revenue is None else revenue - spend
    missing_revenue = int(data["Revenue"].isna().sum())
    return {
        "total_ad_spend": spend,
        "total_revenue": revenue,
        "total_impressions": counts["Impressions"],
        "total_clicks": counts["Clicks"],
        "total_leads": counts["Leads"],
        "total_conversions": counts["Conversions"],
        "ctr_percent": _ratio(counts["Clicks"], counts["Impressions"], 100),
        "conversion_rate_percent": _ratio(counts["Conversions"], counts["Leads"], 100),
        "cac": _ratio(spend, counts["Conversions"]),
        "roas": _ratio(revenue, spend),
        "roi_percent": _ratio(profit, spend, 100),
        "profit": profit,
        "row_count": len(data),
        "missing_revenue_rows": missing_revenue,
        "revenue_coverage_percent": _ratio(len(data) - missing_revenue, len(data), 100),
        "financials_complete": missing_revenue == 0,
    }


def calculate_kpis(data: pd.DataFrame) -> KPIResult:
    """Return finite, unrounded totals and guarded, volume-weighted KPI rates."""
    return _calculate_kpis(validate_data(data))


def _summarize_by(data: pd.DataFrame, column: str) -> pd.DataFrame:
    if column == "Month":
        data = data.assign(Month=data["Date"].dt.to_period("M").astype(str))
    rows = [
        {column: key, **_calculate_kpis(group)}
        for key, group in data.groupby(column, sort=True, observed=True, dropna=False)
    ]
    return pd.DataFrame.from_records(rows, columns=[column, *KPI_COLUMNS])


def summarize_by(data: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Summarize channel, campaign, age_group, gender, or month (YYYY-MM).

    The corresponding source column names are also accepted. The grouping key
    is a regular column; metric names match calculate_kpis. Monthly rows sort
    chronologically. Empty selections retain the same result column schema.
    """
    column = GROUP_DIMENSIONS.get(dimension, dimension)
    if column not in GROUP_DIMENSIONS.values():
        raise ValueError(f"Unsupported dimension {dimension!r}; choose {', '.join(GROUP_DIMENSIONS)}")
    return _summarize_by(validate_data(data), column)


def grouped_summaries(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return all five dashboard summaries, validating the input only once."""
    normalized = validate_data(data)
    return {name: _summarize_by(normalized, column) for name, column in GROUP_DIMENSIONS.items()}


def _insights(data: pd.DataFrame, kpis: KPIResult, min_conversions: int) -> list[dict[str, str]]:
    insights = []

    def add(code: str, severity: str, title: str, message: str, action: str) -> None:
        insights.append(dict(code=code, severity=severity, title=title, message=message, action=action))

    if data.empty:
        add("no_data", "info", "No data in this selection", "No rows match the current filters.",
            "Broaden the date range or select additional channels and campaigns.")
        return insights
    if kpis["missing_revenue_rows"]:
        add("missing_revenue", "warning", "Financial metrics are partial",
            f"{kpis['missing_revenue_rows']} row(s) have missing revenue; totals use known revenue only.",
            "Reconcile missing revenue before using ROI or ROAS to allocate budget.")
    duplicates = int(data.duplicated().sum())
    if duplicates:
        add("duplicate_rows", "warning", "Possible duplicate records",
            f"{duplicates} duplicate row(s) are included in the totals.",
            "Check source identifiers and remove only confirmed duplicates upstream.")
    if kpis["total_ad_spend"] == 0:
        add("zero_spend", "info", "No recorded ad spend", "ROAS and ROI are undefined for this selection.",
            "Verify spend attribution before evaluating paid-campaign efficiency.")
    elif kpis["total_conversions"] == 0:
        add("no_conversions", "warning", "Spend without recorded conversions",
            f"{kpis['total_ad_spend']:,.2f} was spent with no conversions; CAC is undefined.",
            "Audit conversion tracking and review targeting and the landing-page funnel before scaling.")
    if kpis["financials_complete"] and kpis["total_ad_spend"] > 0:
        if kpis["profit"] < 0:
            add("loss_making", "warning", "Revenue is below ad spend",
                f"Revenue minus ad spend is {kpis['profit']:,.2f}.",
                "Review loss-making campaigns, creative, and offer economics before adding budget.")
        elif kpis["profit"] > 0:
            add("profitable", "success", "Revenue exceeds ad spend",
                f"Revenue minus ad spend is {kpis['profit']:,.2f}; other business costs are excluded.",
                "Check margin and attribution, then test incremental budget on proven channels.")
        else:
            add("break_even", "info", "Advertising is at break-even",
                "Recorded revenue equals ad spend before other business costs.",
                "Improve conversion efficiency or offer margin before expanding spend.")

    channels = _summarize_by(data, "Channel")
    complete = channels[channels["financials_complete"] & (channels["total_ad_spend"] > 0)]
    losing = complete[complete["profit"] < 0].sort_values(["profit", "Channel"])
    if not losing.empty:
        row = losing.iloc[0]
        add("underperforming_channel", "warning", f"Review {row['Channel']}",
            f"{row['Channel']} has the largest channel loss: {row['profit']:,.2f} before other costs.",
            "Inspect its campaigns and test a smaller budget while improving targeting and creative.")
    # A threshold is an evidence guard, not a claim of statistical significance.
    candidates = complete[
        (complete["total_conversions"] >= min_conversions) & (complete["roas"] > 1)
    ].sort_values(["roas", "total_conversions", "Channel"], ascending=[False, False, True])
    if not candidates.empty and duplicates == 0:
        row = candidates.iloc[0]
        add("scale_candidate", "info", f"Test incremental investment in {row['Channel']}",
            f"{row['Channel']} has {row['roas']:.2f}x ROAS and {int(row['total_conversions'])} conversions.",
            "Run a limited budget increase and monitor marginal CAC, attribution, and capacity.")
    return insights


def _check_min_conversions(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("min_conversions must be a positive integer")


def generate_insights(data: pd.DataFrame, *, min_conversions: int = 30) -> list[dict[str, str]]:
    """Return factual dashboard cards with code, severity, title, message, action.

    Scale candidates require complete channel revenue, positive spend, ROAS > 1,
    at least min_conversions (default 30), and no duplicate input rows. These are
    exploratory recommendations, not causal or statistically significant claims.
    """
    _check_min_conversions(min_conversions)
    normalized = validate_data(data)
    return _insights(normalized, _calculate_kpis(normalized), min_conversions)


def health_summary(data: pd.DataFrame, *, min_conversions: int = 30) -> dict:
    """Return JSON-safe KPI, date-coverage, data-quality, and actionable health data."""
    _check_min_conversions(min_conversions)
    normalized = validate_data(data)
    kpis = _calculate_kpis(normalized)
    insights = _insights(normalized, kpis, min_conversions)
    if normalized.empty:
        status = "no_data"
    elif any(insight["severity"] == "warning" for insight in insights):
        status = "needs_attention"
    elif kpis["total_ad_spend"] == 0:
        status = "insufficient_data"
    else:
        status = "healthy"
    return {
        "status": status,
        "row_count": len(normalized),
        "start_date": None if normalized.empty else normalized["Date"].min().date().isoformat(),
        "end_date": None if normalized.empty else normalized["Date"].max().date().isoformat(),
        "missing_revenue_rows": kpis["missing_revenue_rows"],
        "revenue_coverage_percent": kpis["revenue_coverage_percent"],
        "duplicate_rows": int(normalized.duplicated().sum()),
        "unknown_age_rows": int(normalized["Age_Group"].str.casefold().eq("unknown").sum()),
        "unknown_gender_rows": int(normalized["Gender"].str.casefold().eq("unknown").sum()),
        "kpis": kpis,
        "insights": insights,
    }
