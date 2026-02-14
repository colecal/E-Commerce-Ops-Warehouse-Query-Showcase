from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
SQL_DIR = BASE_DIR / "sql" / "curated"


@dataclass(frozen=True)
class QueryDef:
    id: str
    title: str
    description: str
    sql_file: str
    # ordered parameter names to bind into $1..$N placeholders
    params: list[str]
    # optional basic chart hints
    chart: dict[str, Any] | None = None


QUERIES: dict[str, QueryDef] = {
    "cohort_retention": QueryDef(
        id="cohort_retention",
        title="Cohort Retention (monthly)",
        description="Customers grouped by first purchase month; retention by months since first order.",
        sql_file="cohort_retention.sql",
        params=["start_month", "end_month"],
        chart={"type": "heatmap_like"},
    ),
    "ltv_by_cohort": QueryDef(
        id="ltv_by_cohort",
        title="LTV by Cohort (12 mo)",
        description="Average cumulative revenue per customer for each cohort over 12 months.",
        sql_file="ltv_by_cohort.sql",
        params=["start_month", "end_month"],
        chart={"type": "line"},
    ),
    "aov_trend": QueryDef(
        id="aov_trend",
        title="AOV Trend", 
        description="Average order value by week; includes rolling 4-week average (window function).",
        sql_file="aov_trend.sql",
        params=["start_date", "end_date"],
        chart={"type": "line"},
    ),
    "conversion_funnel": QueryDef(
        id="conversion_funnel",
        title="Conversion Funnel",
        description="From sessions -> product views -> add to cart -> checkout -> paid orders.",
        sql_file="conversion_funnel.sql",
        params=["start_date", "end_date"],
        chart={"type": "funnel"},
    ),
    "anomaly_daily_revenue": QueryDef(
        id="anomaly_daily_revenue",
        title="Revenue Anomaly Detection",
        description="Daily revenue z-score vs 28-day trailing mean/stddev (window).",
        sql_file="anomaly_daily_revenue.sql",
        params=["start_date", "end_date"],
        chart={"type": "line"},
    ),
    "return_rate_by_category": QueryDef(
        id="return_rate_by_category",
        title="Return Rate by Category",
        description="Refund rate and units returned by product category.",
        sql_file="return_rate_by_category.sql",
        params=["start_date", "end_date"],
        chart={"type": "bar"},
    ),
    "shipping_sla": QueryDef(
        id="shipping_sla",
        title="Shipping SLA Performance",
        description="Shipment delivery time percentiles and SLA breach rate by carrier/service.",
        sql_file="shipping_sla.sql",
        params=["start_date", "end_date"],
        chart={"type": "bar"},
    ),
}


def load_sql(query_id: str) -> str:
    q = QUERIES[query_id]
    path = SQL_DIR / q.sql_file
    return path.read_text(encoding="utf-8")
