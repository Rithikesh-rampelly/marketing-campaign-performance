import json

import numpy as np
import pandas as pd
import pytest

from python.marketing_analytics import (
    KPI_COLUMNS,
    MAX_SAFE_NUMBER,
    calculate_kpis,
    filter_data,
    generate_insights,
    grouped_summaries,
    health_summary,
    load_data,
    summarize_by,
    validate_data,
)


@pytest.fixture
def campaigns():
    """Unequal volumes ensure weighted KPI math differs from averaging rates."""
    return pd.DataFrame(
        [
            ["C1", "Spring", "15-01-2026", "Email", "U1", "25-34", "Female", 1000, 100, 20, 4, 100, 300],
            ["C1", "Spring", "01-02-2026", "Google Ads", "U2", "35-44", "Male", 2000, 100, 10, 1, 200, 100],
            ["C2", "Launch", "28-02-2026", "Email", "U3", "25-34", "Female", 500, 50, 10, 5, 50, 250],
            ["C3", "Test", "01-03-2026", "YouTube", "U4", "55+", "Other", 0, 0, 0, 0, 0, 0],
        ],
        columns=[
            "Campaign_ID", "Campaign_Name", "Date", "Channel", "Customer_ID", "Age_Group", "Gender",
            "Impressions", "Clicks", "Leads", "Conversions", "Ad_Spend", "Revenue",
        ],
    )


def test_kpi_math_uses_aggregate_denominators(campaigns):
    kpis = calculate_kpis(campaigns)
    assert kpis == {
        "total_ad_spend": 350,
        "total_revenue": 650,
        "total_impressions": 3500,
        "total_clicks": 250,
        "total_leads": 40,
        "total_conversions": 10,
        "ctr_percent": pytest.approx(250 / 3500 * 100),
        "conversion_rate_percent": 25,
        "cac": 35,
        "roas": pytest.approx(650 / 350),
        "roi_percent": pytest.approx(300 / 350 * 100),
        "profit": 300,
        "row_count": 4,
        "missing_revenue_rows": 0,
        "revenue_coverage_percent": 100,
        "financials_complete": True,
    }
    json.dumps(kpis, allow_nan=False)


def test_zero_denominators_are_undefined_not_infinite(campaigns):
    kpis = calculate_kpis(campaigns.iloc[[3]])
    for metric in ("ctr_percent", "conversion_rate_percent", "cac", "roas", "roi_percent"):
        assert kpis[metric] is None
    assert kpis["profit"] == 0
    assert kpis["total_revenue"] == 0
    json.dumps(kpis, allow_nan=False)


def test_spend_without_conversions_and_revenue_without_spend(campaigns):
    row = campaigns.iloc[[3]].copy()
    row["Ad_Spend"] = 100
    kpis = calculate_kpis(row)
    assert kpis["cac"] is None
    assert kpis["roas"] == 0
    assert kpis["roi_percent"] == -100
    assert kpis["profit"] == -100
    row["Ad_Spend"] = 0
    row["Revenue"] = 100
    kpis = calculate_kpis(row)
    assert kpis["roas"] is None
    assert kpis["roi_percent"] is None
    assert kpis["profit"] == 100


def test_grouped_summaries_reconcile_and_guard_empty_groups(campaigns):
    summaries = grouped_summaries(campaigns)
    assert set(summaries) == {"channel", "campaign", "age_group", "gender", "month"}
    for summary in summaries.values():
        assert summary["total_ad_spend"].sum() == 350
        assert summary["total_revenue"].sum() == 650
        assert summary["total_conversions"].sum() == 10
        assert not np.isinf(summary.select_dtypes(include="number").to_numpy()).any()
    email = summaries["channel"].set_index("Channel").loc["Email"]
    assert email["conversion_rate_percent"] == 30
    assert email["cac"] == pytest.approx(150 / 9)
    assert email["roas"] == pytest.approx(550 / 150)
    youtube = summaries["channel"].set_index("Channel").loc["YouTube"]
    assert pd.isna(youtube["cac"])
    assert pd.isna(youtube["roi_percent"])
    assert summaries["month"]["Month"].tolist() == ["2026-01", "2026-02", "2026-03"]
    february = summaries["month"].set_index("Month").loc["2026-02"]
    assert february["total_revenue"] == 350
    assert february["roi_percent"] == 40


def test_months_keep_the_year_and_sort_chronologically(campaigns):
    campaigns.loc[0, "Date"] = "2025-02-15"
    assert summarize_by(campaigns, "month")["Month"].tolist() == ["2025-02", "2026-02", "2026-03"]


def test_filters_intersect_and_include_both_date_boundaries(campaigns):
    filtered = filter_data(campaigns, start_date="2026-02-01", end_date="28/02/2026")
    assert filtered["Customer_ID"].tolist() == ["U2", "U3"]
    filtered = filter_data(
        campaigns, start_date="01-02-2026", end_date="2026-02-28",
        channels=" email ", campaigns=[" launch "],
    )
    assert filtered["Customer_ID"].tolist() == ["U3"]
    assert filter_data(campaigns, campaigns="c1")["Customer_ID"].tolist() == ["U1", "U2"]


def test_datetime_filters_are_calendar_day_inclusive(campaigns):
    campaigns["Date"] = pd.to_datetime(campaigns["Date"], format="%d-%m-%Y") + pd.Timedelta(hours=23)
    filtered = filter_data(campaigns, start_date=pd.Timestamp("2026-02-28"), end_date="2026-02-28")
    assert filtered["Customer_ID"].tolist() == ["U3"]


@pytest.mark.parametrize("filters", [{"channels": []}, {"campaigns": []}, {"channels": ["Missing"]}])
def test_empty_selection_has_consistent_metrics_and_health(campaigns, filters):
    filtered = filter_data(campaigns, **filters)
    assert filtered.empty
    kpis = calculate_kpis(filtered)
    assert kpis["total_ad_spend"] == 0
    assert kpis["total_revenue"] == 0
    assert kpis["cac"] is None
    assert kpis["revenue_coverage_percent"] is None
    assert health_summary(filtered)["status"] == "no_data"
    assert generate_insights(filtered)[0]["code"] == "no_data"
    assert list(summarize_by(filtered, "channel")) == ["Channel", *KPI_COLUMNS]


def test_invalid_filter_dates_fail_loudly(campaigns):
    with pytest.raises(ValueError, match="start_date must not be after end_date"):
        filter_data(campaigns, start_date="2026-03-01", end_date="2026-02-01")
    with pytest.raises(ValueError, match="start_date"):
        filter_data(campaigns, start_date="not a date")


def test_input_is_not_mutated_and_duplicate_indexes_are_supported(campaigns):
    campaigns.index = [0, 0, 1, 1]
    original = campaigns.copy(deep=True)
    calculate_kpis(campaigns)
    filter_data(campaigns, channels="Email")
    grouped_summaries(campaigns)
    health_summary(campaigns)
    pd.testing.assert_frame_equal(campaigns, original)


def test_loader_handles_bom_numeric_text_and_whitespace(campaigns, tmp_path):
    campaigns = campaigns.rename(columns={"Revenue": " Revenue "})
    campaigns.loc[0, "Channel"] = " email "
    path = tmp_path / "campaigns.csv"
    campaigns.to_csv(path, encoding="utf-8-sig", index=False)
    loaded = load_data(path)
    assert loaded.loc[0, "Date"] == pd.Timestamp("2026-01-15")
    assert loaded.loc[0, "Channel"] == "Email"
    assert calculate_kpis(loaded)["total_revenue"] == 650


def test_missing_file_and_empty_csv_have_useful_errors(tmp_path):
    with pytest.raises(FileNotFoundError, match="Marketing CSV not found"):
        load_data(tmp_path / "missing.csv")
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="Unable to read marketing CSV"):
        load_data(path)


def test_missing_revenue_is_preserved_and_flagged(campaigns):
    campaigns["Revenue"] = campaigns["Revenue"].astype(float)
    campaigns.loc[0, "Revenue"] = np.nan
    normalized = validate_data(campaigns)
    assert pd.isna(normalized.loc[0, "Revenue"])
    kpis = calculate_kpis(normalized)
    assert kpis["total_revenue"] == 350
    assert kpis["missing_revenue_rows"] == 1
    assert kpis["revenue_coverage_percent"] == 75
    assert kpis["financials_complete"] is False
    health = health_summary(normalized, min_conversions=5)
    assert health["status"] == "needs_attention"
    codes = {insight["code"] for insight in health["insights"]}
    assert "missing_revenue" in codes
    assert "profitable" not in codes
    assert "scale_candidate" not in codes  # The profitable Email channel is incomplete.
    json.dumps(health, allow_nan=False)


def test_all_missing_revenue_is_unknown_not_zero(campaigns):
    campaigns["Revenue"] = np.nan
    kpis = calculate_kpis(campaigns)
    for metric in ("total_revenue", "profit", "roas", "roi_percent"):
        assert kpis[metric] is None
    assert kpis["revenue_coverage_percent"] == 0
    assert summarize_by(campaigns, "channel")["total_revenue"].isna().all()
    json.dumps(health_summary(campaigns), allow_nan=False)


@pytest.mark.parametrize(
    "column,value,error",
    [
        ("Ad_Spend", -1, "Ad_Spend must be between"),
        ("Revenue", np.inf, "Revenue must contain only finite"),
        ("Impressions", -1, "Impressions must be between"),
        ("Clicks", 1.5, "Clicks must contain whole-number"),
        ("Clicks", True, "Clicks contains nonnumeric"),
        ("Leads", None, "Leads contains missing"),
        ("Revenue", "invalid", "Revenue contains nonnumeric"),
        ("Revenue", MAX_SAFE_NUMBER * 2, "Revenue must be between"),
        ("Clicks", 1001, "Clicks cannot exceed Impressions"),
        ("Leads", 101, "Leads cannot exceed Clicks"),
        ("Conversions", 21, "Conversions cannot exceed Leads"),
        ("Date", "31-02-2026", "Date contains"),
        ("Date", "1899-12-31", "Date contains"),
        ("Date", "2101-01-01", "Date contains"),
        ("Date", None, "Date contains"),
    ],
)
def test_validation_rejects_unsafe_data(campaigns, column, value, error):
    campaigns[column] = campaigns[column].astype(object)
    campaigns.loc[0, column] = value
    with pytest.raises(ValueError, match=error):
        validate_data(campaigns)


def test_validation_rejects_unsafe_totals_and_missing_columns(campaigns):
    campaigns["Revenue"] = MAX_SAFE_NUMBER / 2
    with pytest.raises(ValueError, match="Revenue total exceeds"):
        validate_data(campaigns)
    with pytest.raises(ValueError, match="Missing required columns: Leads"):
        validate_data(campaigns.drop(columns="Leads"))


def test_health_insights_have_evidence_and_action(campaigns):
    health = health_summary(campaigns, min_conversions=5)
    assert health["status"] == "needs_attention"  # Google Ads loses money despite healthy overall ROI.
    assert health["start_date"] == "2026-01-15"
    assert health["end_date"] == "2026-03-01"
    cards = {insight["code"]: insight for insight in health["insights"]}
    assert "300.00" in cards["profitable"]["message"]
    assert "Google Ads" in cards["underperforming_channel"]["message"]
    assert "Email" in cards["scale_candidate"]["message"]
    assert "9 conversions" in cards["scale_candidate"]["message"]
    assert all(card["action"] and card["severity"] for card in cards.values())
    assert "scale_candidate" not in {i["code"] for i in generate_insights(campaigns)}
    assert health_summary(filter_data(campaigns, channels="Email"))["status"] == "healthy"


def test_no_conversion_and_zero_spend_insights(campaigns):
    row = campaigns.iloc[[3]].copy()
    assert health_summary(row)["status"] == "insufficient_data"
    assert "zero_spend" in {i["code"] for i in generate_insights(row)}
    row["Ad_Spend"] = 100
    cards = {i["code"]: i for i in generate_insights(row)}
    assert cards["no_conversions"]["severity"] == "warning"
    assert cards["loss_making"]["severity"] == "warning"
    assert "scale_candidate" not in cards


def test_duplicates_are_flagged_without_silent_deduplication(campaigns):
    duplicated = pd.concat([campaigns, campaigns.iloc[[0]]], ignore_index=True)
    health = health_summary(duplicated, min_conversions=5)
    assert health["row_count"] == 5
    assert health["duplicate_rows"] == 1
    assert health["kpis"]["total_ad_spend"] == 450
    codes = {i["code"] for i in health["insights"]}
    assert "duplicate_rows" in codes
    assert "scale_candidate" not in codes


def test_invalid_summary_dimension_and_evidence_threshold(campaigns):
    with pytest.raises(ValueError, match="Unsupported dimension"):
        summarize_by(campaigns, "Customer_ID")
    with pytest.raises(ValueError, match="positive integer"):
        generate_insights(campaigns, min_conversions=0)
