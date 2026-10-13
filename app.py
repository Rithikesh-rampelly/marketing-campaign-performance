"""Interactive Streamlit dashboard for the marketing campaign project.

Run from the repository root with ``streamlit run app.py``.  The dashboard is
deliberately built from the same validated analytics functions used by the
tests and command-line scripts, so a chart and a KPI card cannot silently use
different business logic.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from python.marketing_analytics import (
    DEFAULT_DATA_PATH,
    filter_data,
    grouped_summaries,
    health_summary,
    load_data,
    validate_data,
)


APP_TITLE = "Marketing Performance Command Center"
ACCENT = "#2563EB"
TEAL = "#0F766E"
ORANGE = "#D97706"
RED = "#DC2626"
TEXT = "#172033"
MUTED = "#64748B"


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { max-width: 1440px; padding-top: 2rem; }
        [data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 1rem 1.1rem;
        }
        [data-testid="stMetricLabel"] { color: #64748b; }
        .hero {
            background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 55%, #ecfeff 100%);
            border: 1px solid #dbeafe;
            border-radius: 20px;
            padding: 1.4rem 1.6rem;
            margin-bottom: 1.2rem;
        }
        .hero h1 { color: #172033; margin: 0 0 .35rem 0; }
        .hero p { color: #475569; margin: 0; font-size: 1.02rem; }
        .small-note { color: #64748b; font-size: .88rem; }
        .insight-card {
            border: 1px solid #e2e8f0;
            border-left: 5px solid #2563eb;
            border-radius: 12px;
            padding: .8rem 1rem;
            margin: .45rem 0;
            background: #ffffff;
        }
        .insight-card.warning { border-left-color: #d97706; }
        .insight-card.success { border-left-color: #0f766e; }
        .insight-card.info { border-left-color: #2563eb; }
        .insight-title { font-weight: 700; color: #172033; }
        .insight-body { color: #475569; margin-top: .2rem; }
        .insight-action { color: #334155; font-size: .9rem; margin-top: .35rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _currency(value: object, compact: bool = False) -> str:
    if value is None or pd.isna(value):
        return "—"
    number = float(value)
    if compact:
        if abs(number) >= 1_000_000:
            return f"₹{number / 1_000_000:.2f}M"
        if abs(number) >= 1_000:
            return f"₹{number / 1_000:.1f}K"
    return f"₹{number:,.0f}"


def _number(value: object, compact: bool = False) -> str:
    if value is None or pd.isna(value):
        return "—"
    number = float(value)
    if compact:
        if abs(number) >= 1_000_000:
            return f"{number / 1_000_000:.2f}M"
        if abs(number) >= 1_000:
            return f"{number / 1_000:.1f}K"
    return f"{number:,.0f}"


def _percent(value: object, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{decimals}f}%"


def _ratio(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.2f}x"


def _read_uploaded(uploaded_file: object) -> pd.DataFrame:
    """Read an uploaded CSV through the same validation as the default data."""
    if uploaded_file is None:
        return load_data()
    try:
        uploaded_file.seek(0)
        frame = pd.read_csv(
            io.BytesIO(uploaded_file.getvalue()),
            encoding="utf-8-sig",
            dtype="string",
            keep_default_na=False,
        )
        return validate_data(frame)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeError) as exc:
        raise ValueError(f"Unable to read the uploaded CSV: {exc}") from exc


@st.cache_data(show_spinner=False)
def _load_default_data() -> pd.DataFrame:
    return load_data(DEFAULT_DATA_PATH)


def _load_source(uploaded_file: object) -> pd.DataFrame:
    return _load_default_data() if uploaded_file is None else _read_uploaded(uploaded_file)


def _select_all_label(values: list[str]) -> str:
    return f"All ({len(values)})"


def _render_insights(insights: list[dict[str, str]]) -> None:
    if not insights:
        st.success("No issues were detected in this selection.")
        return
    for insight in insights:
        severity = insight["severity"]
        st.markdown(
            f"""
            <div class="insight-card {severity}">
              <div class="insight-title">{insight['title']}</div>
              <div class="insight-body">{insight['message']}</div>
              <div class="insight-action"><b>Next step:</b> {insight['action']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _empty_state(message: str = "No rows match the current filters.") -> None:
    st.info(message + " Broaden the date range or choose more channels/campaigns.")


def _format_table(frame: pd.DataFrame, currency_columns: tuple[str, ...] = ()) -> pd.DataFrame:
    display = frame.copy()
    for column in currency_columns:
        if column in display:
            display[column] = display[column].map(lambda value: _currency(value))
    for column in ("ctr_percent", "conversion_rate_percent", "roi_percent", "revenue_coverage_percent"):
        if column in display:
            display[column] = display[column].map(_percent)
    if "roas" in display:
        display["roas"] = display["roas"].map(_ratio)
    if "total_impressions" in display:
        display["total_impressions"] = display["total_impressions"].map(_number)
    for column in ("total_clicks", "total_leads", "total_conversions", "row_count", "missing_revenue_rows"):
        if column in display:
            display[column] = display[column].map(_number)
    if "financials_complete" in display:
        display["financials_complete"] = display["financials_complete"].map(
            lambda value: "Complete" if bool(value) else "Partial"
        )
    return display


def _chart_layout(figure: go.Figure, height: int = 360) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=42, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    figure.update_xaxes(showgrid=False, linecolor="#cbd5e1")
    figure.update_yaxes(gridcolor="#e2e8f0", zeroline=False)
    return figure


def _monthly_chart(monthly: pd.DataFrame) -> go.Figure:
    if monthly.empty:
        return go.Figure()
    chart = monthly.melt(
        id_vars="Month",
        value_vars=["total_ad_spend", "total_revenue"],
        var_name="Metric",
        value_name="Amount",
    )
    chart["Metric"] = chart["Metric"].map(
        {"total_ad_spend": "Ad spend", "total_revenue": "Revenue"}
    )
    figure = px.line(
        chart,
        x="Month",
        y="Amount",
        color="Metric",
        markers=True,
        color_discrete_map={"Ad spend": ORANGE, "Revenue": ACCENT},
        labels={"Amount": "Amount (₹)", "Month": "Month"},
        title="Revenue and spend over time",
    )
    figure.update_traces(hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>")
    return _chart_layout(figure)


def _channel_revenue_chart(channels: pd.DataFrame) -> go.Figure:
    if channels.empty:
        return go.Figure()
    chart = channels.melt(
        id_vars="Channel",
        value_vars=["total_ad_spend", "total_revenue"],
        var_name="Metric",
        value_name="Amount",
    )
    chart["Metric"] = chart["Metric"].map(
        {"total_ad_spend": "Ad spend", "total_revenue": "Revenue"}
    )
    figure = px.bar(
        chart,
        x="Channel",
        y="Amount",
        color="Metric",
        barmode="group",
        color_discrete_map={"Ad spend": ORANGE, "Revenue": ACCENT},
        labels={"Amount": "Amount (₹)"},
        title="Money generated by channel",
    )
    figure.update_traces(hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>")
    return _chart_layout(figure)


def _channel_roas_chart(channels: pd.DataFrame) -> go.Figure:
    if channels.empty:
        return go.Figure()
    chart = channels.dropna(subset=["roas"]).sort_values("roas")
    figure = px.bar(
        chart,
        x="roas",
        y="Channel",
        orientation="h",
        color="roas",
        color_continuous_scale=["#dbeafe", ACCENT, TEAL],
        labels={"roas": "ROAS (revenue per ₹1 spent)", "Channel": ""},
        title="Efficiency by channel",
    )
    figure.add_vline(x=1, line_dash="dash", line_color=RED, annotation_text="Break-even")
    figure.update_traces(hovertemplate="%{y}<br>%{x:.2f}x ROAS<extra></extra>")
    figure.update_coloraxes(showscale=False)
    return _chart_layout(figure)


def _audience_chart(summary: pd.DataFrame, dimension: str, title: str) -> go.Figure:
    if summary.empty:
        return go.Figure()
    key = "Age_Group" if dimension == "age_group" else "Gender"
    chart = summary.sort_values("conversion_rate_percent", ascending=False)
    figure = px.bar(
        chart,
        x=key,
        y="conversion_rate_percent",
        color="roas",
        color_continuous_scale=["#dbeafe", ACCENT, TEAL],
        labels={"conversion_rate_percent": "Lead-to-customer rate (%)", key: ""},
        title=title,
    )
    figure.update_traces(hovertemplate="%{x}<br>%{y:.1f}% conversion rate<extra></extra>")
    figure.update_coloraxes(colorbar_title="ROAS")
    return _chart_layout(figure)


def _metric_cards(kpis: dict) -> None:
    cards = [
        ("Revenue", _currency(kpis["total_revenue"], compact=True), "Known revenue in selection"),
        ("Ad spend", _currency(kpis["total_ad_spend"], compact=True), "Paid media investment"),
        ("ROAS", _ratio(kpis["roas"]), "Revenue per ₹1 spent"),
        ("CAC", _currency(kpis["cac"]), "Spend per conversion"),
        ("Conversion rate", _percent(kpis["conversion_rate_percent"]), "Conversions ÷ leads"),
        ("Revenue coverage", _percent(kpis["revenue_coverage_percent"]), "Rows with known revenue"),
    ]
    columns = st.columns(len(cards))
    for column, (label, value, help_text) in zip(columns, cards):
        column.metric(label, value, help=help_text)


def _render_overview(data: pd.DataFrame, health: dict, summaries: dict[str, pd.DataFrame]) -> None:
    st.subheader("Executive overview")
    st.caption(
        "A decision-ready view of spend, funnel health, and channel efficiency. "
        "Use the filters in the sidebar to move from the full portfolio to one campaign."
    )
    _metric_cards(health["kpis"])

    if health["status"] == "needs_attention":
        st.warning("This selection needs attention. Review the evidence-based cards below before reallocating budget.")
    elif health["status"] == "healthy":
        st.success("This selection is healthy on the recorded metrics. Validate margin and attribution before scaling.")
    elif health["status"] == "insufficient_data":
        st.info("There is not enough spend or conversion data to calculate all efficiency metrics.")

    left, right = st.columns((1.35, 1))
    with left:
        monthly = summaries["month"]
        if monthly.empty:
            _empty_state()
        else:
            st.plotly_chart(_monthly_chart(monthly), width="stretch", key="overview_monthly")
    with right:
        channels = summaries["channel"]
        if channels.empty:
            _empty_state()
        else:
            st.plotly_chart(_channel_roas_chart(channels), width="stretch", key="overview_roas")

    left, right = st.columns((1.35, 1))
    with left:
        channels = summaries["channel"]
        if not channels.empty:
            st.plotly_chart(
                _channel_revenue_chart(channels),
                width="stretch",
                key="overview_channel_money",
            )
    with right:
        st.markdown("#### What should I do next?")
        _render_insights(health["insights"])

    with st.expander("How to interpret this dashboard", expanded=False):
        st.markdown(
            """
            - **ROAS** is recorded revenue divided by ad spend. A value above 1.00x means revenue is above ad spend, not that the business is profitable after product, payroll, tax, or fulfilment costs.
            - **CAC** is ad spend divided by recorded conversions. It is undefined when there are no conversions.
            - **Conversion rate** is conversions divided by leads. Rates are calculated from totals, so large and small campaigns are weighted correctly.
            - **Revenue coverage** tells you how much of the selected data has known revenue. Missing revenue is never silently changed to zero.
            - **Scale candidate** cards are directional tests, not causal recommendations. Run a controlled budget experiment and watch marginal CAC.
            """
        )


def _render_performance(data: pd.DataFrame, summaries: dict[str, pd.DataFrame]) -> None:
    st.subheader("Performance explorer")
    st.caption("Compare channels and campaigns using volume, efficiency, and financial completeness together.")
    channel_tab, campaign_tab = st.tabs(["Channels", "Campaigns"])
    table_columns = [
        "Channel", "total_ad_spend", "total_revenue", "total_conversions",
        "ctr_percent", "conversion_rate_percent", "cac", "roas", "roi_percent",
        "financials_complete",
    ]
    with channel_tab:
        channels = summaries["channel"]
        if channels.empty:
            _empty_state()
        else:
            st.plotly_chart(_channel_roas_chart(channels), width="stretch", key="performance_roas")
            st.dataframe(
                _format_table(channels[table_columns], currency_columns=("total_ad_spend", "total_revenue", "cac")),
                width="stretch",
                hide_index=True,
            )
            csv = channels.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download channel analysis",
                csv,
                file_name="channel_performance.csv",
                mime="text/csv",
                key="download_channels",
            )
    with campaign_tab:
        campaigns = summaries["campaign"]
        if campaigns.empty:
            _empty_state()
        else:
            top = campaigns.sort_values("total_revenue", ascending=False).head(15)
            figure = px.bar(
                top.sort_values("total_revenue"),
                x="total_revenue",
                y="Campaign_Name",
                orientation="h",
                color="roas",
                color_continuous_scale=["#dbeafe", ACCENT, TEAL],
                labels={"total_revenue": "Known revenue (₹)", "Campaign_Name": ""},
                title="Top campaigns by known revenue",
            )
            figure.update_coloraxes(colorbar_title="ROAS")
            figure.update_traces(hovertemplate="%{y}<br>₹%{x:,.0f}<extra></extra>")
            st.plotly_chart(_chart_layout(figure, 420), width="stretch", key="performance_campaigns")
            campaign_columns = [column.replace("Channel", "Campaign_Name") for column in table_columns]
            st.dataframe(
                _format_table(
                    campaigns[campaign_columns],
                    currency_columns=("total_ad_spend", "total_revenue", "cac"),
                ),
                width="stretch",
                hide_index=True,
            )
            st.download_button(
                "Download campaign analysis",
                campaigns.to_csv(index=False).encode("utf-8"),
                file_name="campaign_performance.csv",
                mime="text/csv",
                key="download_campaigns",
            )


def _render_audience_and_trends(summaries: dict[str, pd.DataFrame]) -> None:
    st.subheader("Audience and trends")
    st.caption("Find segments that deserve a message or offer test, without confusing correlation with causation.")
    audience_left, audience_right = st.columns(2)
    with audience_left:
        age = summaries["age_group"]
        if age.empty:
            _empty_state()
        else:
            st.plotly_chart(
                _audience_chart(age, "age_group", "Conversion rate by age group"),
                width="stretch",
                key="audience_age",
            )
    with audience_right:
        gender = summaries["gender"]
        if gender.empty:
            _empty_state()
        else:
            st.plotly_chart(
                _audience_chart(gender, "gender", "Conversion rate by gender"),
                width="stretch",
                key="audience_gender",
            )

    st.markdown("#### Monthly funnel health")
    monthly = summaries["month"]
    if monthly.empty:
        _empty_state()
        return
    trend = monthly.melt(
        id_vars="Month",
        value_vars=["ctr_percent", "conversion_rate_percent"],
        var_name="Metric",
        value_name="Rate",
    )
    trend["Metric"] = trend["Metric"].map(
        {"ctr_percent": "Click-through rate", "conversion_rate_percent": "Lead-to-customer rate"}
    )
    figure = px.line(
        trend,
        x="Month",
        y="Rate",
        color="Metric",
        markers=True,
        color_discrete_map={"Click-through rate": ACCENT, "Lead-to-customer rate": TEAL},
        labels={"Rate": "Rate (%)"},
        title="Funnel rates by month",
    )
    figure.update_traces(hovertemplate="%{x}<br>%{y:.2f}%<extra></extra>")
    st.plotly_chart(_chart_layout(figure), width="stretch", key="audience_trends")

    with st.expander("Audience tables"):
        st.dataframe(
            _format_table(age, currency_columns=("total_ad_spend", "total_revenue", "cac")),
            width="stretch",
            hide_index=True,
        )
        st.dataframe(
            _format_table(gender, currency_columns=("total_ad_spend", "total_revenue", "cac")),
            width="stretch",
            hide_index=True,
        )


def _render_budget_planner(channel_summary: pd.DataFrame) -> None:
    st.subheader("Budget planner")
    st.caption(
        "Explore a transparent what-if scenario using historical channel ROAS. "
        "This is not a forecast: marginal returns usually decline as budgets grow."
    )
    usable = channel_summary[
        channel_summary["financials_complete"]
        & channel_summary["roas"].notna()
        & (channel_summary["total_ad_spend"] > 0)
    ].copy()
    if usable.empty:
        st.info("Budget scenarios need at least one channel with complete revenue and recorded spend.")
        return

    channel = st.selectbox("Channel to test", usable["Channel"].tolist(), key="planner_channel")
    selected = usable[usable["Channel"] == channel].iloc[0]
    default_budget = max(1_000, min(50_000, float(selected["total_ad_spend"]) * 0.1))
    budget = st.number_input(
        "Additional budget (₹)",
        min_value=0.0,
        max_value=10_000_000.0,
        value=float(default_budget),
        step=1_000.0,
        key="planner_budget",
    )
    historical_roas = float(selected["roas"])
    projected_revenue = budget * historical_roas
    projected_profit_before_other_costs = projected_revenue - budget
    planner_columns = st.columns(4)
    planner_columns[0].metric("Historical ROAS", _ratio(historical_roas))
    planner_columns[1].metric("Scenario revenue", _currency(projected_revenue, compact=True))
    planner_columns[2].metric("Spend", _currency(budget, compact=True))
    planner_columns[3].metric(
        "Revenue less spend",
        _currency(projected_profit_before_other_costs, compact=True),
    )
    st.markdown(
        f"Historical reference: **{channel}** produced {_currency(selected['total_revenue'], compact=True)} "
        f"from {_currency(selected['total_ad_spend'], compact=True)} of spend across "
        f"{_number(selected['total_conversions'])} conversions."
    )
    st.warning(
        "Use this as a planning baseline only. Before increasing budget, run a controlled test "
        "and monitor incremental CAC, attribution quality, capacity, and contribution margin."
    )

    comparison = usable[["Channel", "roas", "total_ad_spend", "total_conversions"]].copy()
    comparison["scenario_revenue"] = budget * comparison["roas"]
    comparison = comparison.sort_values("roas", ascending=False)
    st.dataframe(
        _format_table(comparison, currency_columns=("total_ad_spend", "scenario_revenue")),
        width="stretch",
        hide_index=True,
    )


def _render_data_help(data: pd.DataFrame, health: dict) -> None:
    st.subheader("Data, definitions, and downloads")
    st.caption("Keep the analysis reproducible: know what the source contains, what is missing, and what each metric means.")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Data health")
        health_rows = pd.DataFrame(
            {
                "Check": [
                    "Rows in selection",
                    "Date range",
                    "Revenue coverage",
                    "Duplicate rows",
                    "Unknown age group",
                    "Unknown gender",
                ],
                "Value": [
                    _number(health["row_count"]),
                    f"{health['start_date'] or '—'} to {health['end_date'] or '—'}",
                    _percent(health["revenue_coverage_percent"]),
                    _number(health["duplicate_rows"]),
                    _number(health["unknown_age_rows"]),
                    _number(health["unknown_gender_rows"]),
                ],
            }
        )
        st.dataframe(health_rows, width="stretch", hide_index=True)
        st.markdown("#### Export this view")
        st.download_button(
            "Download filtered CSV",
            data.to_csv(index=False).encode("utf-8"),
            file_name="marketing_campaign_filtered.csv",
            mime="text/csv",
            key="download_filtered",
        )
        report = json.dumps(health, indent=2, allow_nan=False).encode("utf-8")
        st.download_button(
            "Download health report (JSON)",
            report,
            file_name="marketing_campaign_health.json",
            mime="application/json",
            key="download_health",
        )
    with right:
        st.markdown("#### Metric dictionary")
        definitions = pd.DataFrame(
            [
                ["Impressions", "Times an ad was shown."],
                ["Clicks", "Recorded clicks on the ad."],
                ["CTR", "Clicks ÷ impressions × 100."],
                ["Leads", "Prospects captured by the campaign."],
                ["Conversions", "Recorded customers/actions after a lead."],
                ["Conversion rate", "Conversions ÷ leads × 100."],
                ["CAC", "Ad spend ÷ conversions."],
                ["ROAS", "Known revenue ÷ ad spend."],
                ["ROI", "(Known revenue − ad spend) ÷ ad spend × 100."],
                ["Revenue coverage", "Rows with known revenue ÷ selected rows."],
            ],
            columns=["Metric", "Plain-English definition"],
        )
        st.dataframe(definitions, width="stretch", hide_index=True)
        st.markdown("#### Assumptions")
        st.markdown(
            """
            - Currency is shown in **Indian rupees (₹)** because the source data uses that convention.
            - Revenue is treated as known only when the source has a value; missing revenue is not converted to zero.
            - ROI/ROAS exclude product cost, discounts, salaries, tax, fulfilment, and other business costs.
            - The dashboard is a historical analysis and does not connect to ad platforms or claim real-time data.
            """
        )


def main() -> None:
    _inject_styles()
    st.markdown(
        f"""
        <div class="hero">
          <h1>{APP_TITLE}</h1>
          <p>Understand what is working, find where the funnel leaks, and plan the next budget test — without needing a data-science background.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Controls")
        uploaded = st.file_uploader("Use another CSV", type=["csv"], help="The file must include the required campaign, date, funnel, spend, and revenue columns.")
        st.caption("The bundled dataset is used when no file is uploaded.")

    try:
        source = _load_source(uploaded)
    except (FileNotFoundError, TypeError, ValueError) as exc:
        st.error(f"The data could not be loaded: {exc}")
        st.info("Use a UTF-8 CSV with Date, Channel, Impressions, Clicks, Leads, Conversions, Ad_Spend, and Revenue columns.")
        st.stop()

    min_date = source["Date"].min().date()
    max_date = source["Date"].max().date()
    all_channels = sorted(source["Channel"].dropna().unique().tolist())
    all_campaigns = sorted(source["Campaign_Name"].dropna().unique().tolist())

    with st.sidebar:
        date_selection = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Both dates are included.",
        )
        selected_channels = st.multiselect(
            "Channels",
            options=all_channels,
            default=all_channels,
            help="Leave all selected for the full portfolio.",
        )
        selected_campaigns = st.multiselect(
            "Campaigns",
            options=all_campaigns,
            default=all_campaigns,
            help="Campaign filters work together with channel and date filters.",
        )
        min_conversions = st.number_input(
            "Minimum conversions for scale tests",
            min_value=1,
            max_value=10_000,
            value=30,
            step=1,
            help="Evidence guard for the directional scale-candidate card; it is not a statistical significance test.",
        )

    if isinstance(date_selection, tuple) and len(date_selection) == 2:
        selected_start, selected_end = date_selection
    else:
        selected_start = selected_end = date_selection

    try:
        data = filter_data(
            source,
            start_date=selected_start,
            end_date=selected_end,
            channels=selected_channels,
            campaigns=selected_campaigns,
        )
        health = health_summary(data, min_conversions=int(min_conversions))
        summaries = grouped_summaries(data)
    except (TypeError, ValueError) as exc:
        st.error(f"The selected data is invalid: {exc}")
        st.stop()

    with st.sidebar:
        st.divider()
        st.caption(f"Showing {_number(len(data))} of {_number(len(source))} source rows")
        st.caption(f"{_select_all_label(all_channels)} channels available")
        if uploaded is not None:
            st.success("Using uploaded CSV")
        else:
            st.caption(f"Bundled source: `{Path(DEFAULT_DATA_PATH).name}`")

    page = st.radio(
        "Dashboard section",
        ["Overview", "Performance explorer", "Audience & trends", "Budget planner", "Data & help"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if data.empty:
        _empty_state()
        st.stop()
    if page == "Overview":
        _render_overview(data, health, summaries)
    elif page == "Performance explorer":
        _render_performance(data, summaries)
    elif page == "Audience & trends":
        _render_audience_and_trends(summaries)
    elif page == "Budget planner":
        _render_budget_planner(summaries["channel"])
    else:
        _render_data_help(data, health)


if __name__ == "__main__":
    main()
