"""
    Text report generator
"""

from __future__ import annotations
from typing import Dict
from analytics import KPIResult, RFMScores

def generate_markdown_report(kpi: KPIResult, rfm: Dict[str, RFMScores]) -> str:
    """
    Generate markdown report from metrics
    """
    lines: list[str] = []

    lines.append("# Sales report")
    lines.append("")
    lines.append("## Basic metrics (KPI)")
    lines.append(f"- Total revenue: **{kpi.total_revenue:,.2f}**")
    lines.append(f"- Average bill: **{kpi.avg_ticket:,.2f}**")
    lines.append(f"- Transactions counter: **{kpi.transactions_count}**")
    lines.append(f"- Unique customers: **{kpi.unique_customers}**")
    lines.append("")

    lines.append("## RFM-analysis metrics")
    lines.append("")
    lines.append("| Customer | Recency (days) | Frequency | Monetary | Segment |")
    lines.append("| -------- | -------------- | --------- | -------- | ------- |")

    for cid, scores in rfm.items():
        lines.append(f"| {cid} | {scores.recency_days} | {scores.frequency} | {scores.monetary:,.2f} |\
{scores.segment} |")

    lines.append("")
    lines.append("## Conclusions and recommendations")
    lines.append("- Customers from the **Best** segment can be rewarded with personalized offers\
    and a loyalty program.")
    lines.append("- Customers from the **At risk** segment should be brought back using targeted\
    promotions and reminders.")
    lines.append("- Analyzing sales dynamics by product will help optimize product range and inventory.")

    return "\n".join(lines)
