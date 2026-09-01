"""
    Text and HTML report generator
"""

from __future__ import annotations

from typing import Dict, List
from datetime import datetime
import json

import pandas as pd

from src.analytics import KPIResult, RFMScores


def generate_markdown_report(kpi: KPIResult, rfm: Dict[str, RFMScores]) -> str:
    """
    Generate markdown report from metrics.
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
        lines.append(
            f"| {cid} | {scores.recency_days} | {scores.frequency} | "
            f"{scores.monetary:,.2f} | {scores.segment} |"
        )

    lines.append("")
    lines.append("## Conclusions and recommendations")
    lines.append("")

    total_customers = len(rfm)
    if total_customers == 0 or kpi.transactions_count == 0 or kpi.total_revenue == 0:
        lines.append(
            "- The current dataset does not contain enough customer-level activity "
            "to support reliable segmentation. Focus on increasing data volume "
            "and observation period before drawing strategic conclusions."
        )
        return "\n".join(lines)

    segment_counts: Dict[str, int] = {}
    for scores in rfm.values():
        segment_counts[scores.segment] = segment_counts.get(scores.segment, 0) + 1

    best_count = segment_counts.get("Best", 0)
    loyal_count = segment_counts.get("Loyal", 0)
    at_risk_count = segment_counts.get("At risk", 0)
    regular_count = segment_counts.get("Regular", 0)

    def share(count: int) -> float:
        return (count / total_customers * 100.0) if total_customers > 0 else 0.0

    best_share = share(best_count)
    loyal_share = share(loyal_count)
    at_risk_share = share(at_risk_count)
    regular_share = share(regular_count)

    lines.append(
        f"- The analyzed period includes **{kpi.transactions_count}** transactions "
        f"from **{kpi.unique_customers}** unique customers, generating a total "
        f"revenue of **{kpi.total_revenue:,.2f}** and an average bill of "
        f"**{kpi.avg_ticket:,.2f}**."
    )


    if best_count > 0:
        lines.append(
            f"- High-value buyers in the **Best** segment represent approximately "
            f"**{best_share:.0f}%** of the active customer base. This core group "
            "warrants priority service, personalized offers and early access to "
            "new products to protect its contribution to revenue."
        )

    if at_risk_count > 0:
        lines.append(
            f"- Customers classified as **At risk** account for roughly "
            f"**{at_risk_share:.0f}%** of the base. This indicates a tangible "
            "churn exposure. Launch targeted win-back campaigns (time-limited "
            "discounts, reminder emails, reactivation bundles) to reduce "
            "potential revenue loss."
        )

    if loyal_count > 0:
        lines.append(
            f"- The **Loyal** segment, representing about **{loyal_share:.0f}%** "
            "of customers, forms a natural pipeline into the Best segment. "
            "Structured loyalty programs, upsell paths and cross-selling of "
            "higher-margin products can systematically lift their value."
        )

    if regular_count > 0:
        lines.append(
            f"- Regular customers (~**{regular_share:.0f}%** of the base) provide "
            "broad volume but still have room for frequency and basket expansion. "
            "Use simple bundles, targeted messaging and frictionless promotions "
            "to convert part of this group into Loyal buyers."
        )

    lines.append(
        "- Track how the distribution across Best, Loyal, Regular and At risk "
        "segments evolves over time. A shift towards Best and Loyal indicates "
        "effective retention and value management, while growth in At risk "
        "requires immediate corrective action."
    )
    lines.append(
        "- Combine RFM trends with product-level analytics (top categories, "
        "margins, seasonality) to adjust pricing, assortment and service design "
        "in a data-driven way, rather than relying on intuition alone."
    )

    return "\n".join(lines)


def generate_html_report(
    kpi: KPIResult,
    rfm: Dict[str, RFMScores],
    df: pd.DataFrame,
) -> str:
    """
    Generate an interactive HTML report (single-page dashboard)
    using embedded data and Chart.js.

    - KPI cards at the top.
    - Line chart: revenue by date.
    - Bar chart: customers by RFM segment.
    - Embedded CSS and JS, opens in any browser without extra setup.
    """
    # --- Prepare data for charts ---

    # Revenue by date (time series)
    if df is not None and not df.empty and "sale_date" in df.columns and "total_price" in df.columns:
        revenue_series = (
            df.groupby("sale_date")["total_price"].sum().sort_index()
        )
        revenue_labels: List[str] = [
            d.strftime("%Y-%m-%d") if isinstance(d, datetime) else str(d)
            for d in revenue_series.index
        ]
        revenue_values: List[float] = [float(v) for v in revenue_series.values]
        latest_date_str = revenue_labels[-1] if revenue_labels else ""
    else:
        revenue_labels = []
        revenue_values = []
        latest_date_str = ""

    # Customers by RFM segment
    segment_counts: Dict[str, int] = {}
    for scores in rfm.values():
        segment_counts[scores.segment] = segment_counts.get(scores.segment, 0) + 1

    segment_labels: List[str] = list(segment_counts.keys())
    segment_values: List[int] = list(segment_counts.values())

    # Serialize data for JS
    json_revenue_labels = json.dumps(revenue_labels)
    json_revenue_values = json.dumps(revenue_values)
    json_segment_labels = json.dumps(segment_labels)
    json_segment_values = json.dumps(segment_values)

    # --- Build HTML ---

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Retail BI Analyst - Web Report</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- Chart.js CDN -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1"></script>
<style>
:root {{
  --bg-main: #0f172a;
  --bg-card: #1e293b;
  --bg-surface: #020617;
  --accent: #38bdf8;
  --accent-soft: rgba(56, 189, 248, 0.15);
  --text-primary: #f9fafb;
  --text-secondary: #9ca3af;
  --positive: #22c55e;
  --negative: #ef4444;
  --radius: 12px;
  --gap: 20px;
  --shadow-soft: 0 12px 30px rgba(15, 23, 42, 0.6);
}}

body {{
  margin: 0;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: radial-gradient(circle at top left, #1e293b 0, #020617 45%, #000 100%);
  color: var(--text-primary);
}}

.dashboard-container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}}

.dashboard-header {{
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 24px;
}}

.dashboard-header h1 {{
  font-size: 28px;
  margin: 0;
}}

.dashboard-meta {{
  text-align: right;
}}

.dashboard-meta span {{
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
}}

.kpi-row {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--gap);
  margin-bottom: 24px;
}}

.kpi-card {{
  background: var(--bg-card);
  border-radius: var(--radius);
  padding: 18px 20px;
  box-shadow: var(--shadow-soft);
  position: relative;
  overflow: hidden;
}}

.kpi-card::before {{
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, var(--accent-soft), transparent 60%);
  opacity: 0.9;
}}

.kpi-label {{
  font-size: 13px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}}

.kpi-value {{
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 4px;
}}

.kpi-sub {{
  font-size: 13px;
  color: var(--text-secondary);
}}

.chart-row {{
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1.4fr);
  gap: var(--gap);
  margin-bottom: 24px;
}}

@media (max-width: 900px) {{
  .chart-row {{
    grid-template-columns: minmax(0, 1fr);
  }}
}}

.chart-card {{
  background: var(--bg-card);
  border-radius: var(--radius);
  padding: 18px 20px;
  box-shadow: var(--shadow-soft);
}}

.chart-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}}

.chart-title {{
  font-size: 16px;
  margin: 0;
}}

.chart-subtitle {{
  font-size: 12px;
  color: var(--text-secondary);
}}

.chart-container canvas {{
  width: 100%;
  height: 260px;
}}

.table-section {{
  background: var(--bg-card);
  border-radius: var(--radius);
  padding: 18px 20px;
  box-shadow: var(--shadow-soft);
  margin-bottom: 24px;
}}

.table-section h2 {{
  margin: 0 0 10px;
  font-size: 16px;
}}

.table-section p {{
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--text-secondary);
}}

.rfm-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}}

.rfm-table th,
.rfm-table td {{
  padding: 6px 8px;
  text-align: left;
}}

.rfm-table thead {{
  background: rgba(15,23,42,0.8);
}}

.rfm-table tbody tr:nth-child(even) {{
  background: rgba(15,23,42,0.5);
}}

.rfm-segment-Best {{ color: var(--positive); }}
.rfm-segment-At\\ risk {{ color: var(--negative); }}

.dashboard-footer {{
  font-size: 12px;
  color: var(--text-secondary);
  text-align: right;
  margin-top: 8px;
}}
</style>
</head>
<body>
<div class="dashboard-container">
  <header class="dashboard-header">
    <div>
      <h1>Retail BI Analyst &mdash; Web Report</h1>
      <span class="chart-subtitle">Sales performance overview</span>
    </div>
    <div class="dashboard-meta">
      <span>Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
      <span>Data as of: {latest_date_str}</span>
    </div>
  </header>

  <section class="kpi-row">
    <article class="kpi-card">
      <div class="kpi-label">Total Revenue</div>
      <div class="kpi-value">${kpi.total_revenue:,.2f}</div>
      <div class="kpi-sub">Sum of all transactions</div>
    </article>
    <article class="kpi-card">
      <div class="kpi-label">Average Bill</div>
      <div class="kpi-value">${kpi.avg_ticket:,.2f}</div>
      <div class="kpi-sub">Average value per transaction</div>
    </article>
    <article class="kpi-card">
      <div class="kpi-label">Transactions</div>
      <div class="kpi-value">{kpi.transactions_count}</div>
      <div class="kpi-sub">Total number of sales</div>
    </article>
    <article class="kpi-card">
      <div class="kpi-label">Unique Customers</div>
      <div class="kpi-value">{kpi.unique_customers}</div>
      <div class="kpi-sub">Distinct customers in the period</div>
    </article>
  </section>

  <section class="chart-row">
    <article class="chart-card">
      <div class="chart-header">
        <h2 class="chart-title">Revenue Over Time</h2>
        <span class="chart-subtitle">Daily revenue trend</span>
      </div>
      <div class="chart-container">
        <canvas id="revenueChart"></canvas>
      </div>
    </article>

    <article class="chart-card">
      <div class="chart-header">
        <h2 class="chart-title">Customers by Segment</h2>
        <span class="chart-subtitle">RFM segments distribution</span>
      </div>
      <div class="chart-container">
        <canvas id="segmentChart"></canvas>
      </div>
    </article>
  </section>

  <section class="table-section">
    <h2>RFM Analysis Details</h2>
    <p>Each row represents a customer with recency, frequency, monetary, and segment assignment.</p>
    <table class="rfm-table">
      <thead>
        <tr>
          <th>Customer</th>
          <th>Recency (days)</th>
          <th>Frequency</th>
          <th>Monetary</th>
          <th>Segment</th>
        </tr>
      </thead>
      <tbody>
"""

    # RFM table rows
    for cid, scores in rfm.items():
        segment_class = f"rfm-segment-{scores.segment.replace(' ', '_')}"
        html += (
            f"<tr>"
            f"<td>{cid}</td>"
            f"<td>{scores.recency_days}</td>"
            f"<td>{scores.frequency}</td>"
            f"<td>${scores.monetary:,.2f}</td>"
            f"<td class=\"{segment_class}\">{scores.segment}</td>"
            f"</tr>\n"
        )

    html += f"""      </tbody>
    </table>
  </section>

  <footer class="dashboard-footer">
    <span>Insights powered by Retail BI Analyst</span>
  </footer>
</div>

<script>
const revenueLabels = {json_revenue_labels};
const revenueData = {json_revenue_values};
const segmentLabels = {json_segment_labels};
const segmentData = {json_segment_values};

// Revenue chart (line)
const revenueCtx = document.getElementById('revenueChart');
if (revenueCtx && revenueLabels.length > 0) {{
  new Chart(revenueCtx, {{
    type: 'line',
    data: {{
      labels: revenueLabels,
      datasets: [{{
        label: 'Revenue',
        data: revenueData,
        borderColor: '#38bdf8',
        backgroundColor: 'rgba(56, 189, 248, 0.15)',
        tension: 0.25,
        fill: true,
        pointRadius: 3,
      }}],
    }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{
          display: true,
        }},
        tooltip: {{
          callbacks: {{
            label: function(ctx) {{
              const value = ctx.parsed.y || 0;
              return 'Revenue: $' + value.toLocaleString();
            }}
          }}
        }}
      }},
      scales: {{
        x: {{
          ticks: {{
            maxRotation: 60,
            minRotation: 30
          }}
        }},
        y: {{
          beginAtZero: true
        }}
      }}
    }},
  }});
}} else {{
  if (revenueCtx) {{
    revenueCtx.parentElement.innerHTML =
      '<p style="font-size:13px;color:#9ca3af;">No revenue time series available for this dataset.</p>';
  }}
}}

// Segment chart (bar)
const segmentCtx = document.getElementById('segmentChart');
if (segmentCtx && segmentLabels.length > 0) {{
  new Chart(segmentCtx, {{
    type: 'bar',
    data: {{
      labels: segmentLabels,
      datasets: [{{
        label: 'Customers',
        data: segmentData,
        backgroundColor: ['#22c55e', '#3b82f6', '#ef4444', '#e5e7eb'],
        borderRadius: 6,
      }}],
    }},
    options: {{
      indexAxis: 'y',
      responsive: true,
      plugins: {{
        legend: {{
          display: false
        }},
        tooltip: {{
          callbacks: {{
            label: function(ctx) {{
              const value = ctx.parsed.x || 0;
              return 'Customers: ' + value.toLocaleString();
            }}
          }}
        }}
      }},
      scales: {{
        x: {{
          beginAtZero: true
        }},
        y: {{
          ticks: {{
            color: '#e5e7eb'
          }}
        }}
      }}
    }},
  }});
}} else {{
  if (segmentCtx) {{
    segmentCtx.parentElement.innerHTML =
      '<p style="font-size:13px;color:#9ca3af;">No RFM segment data available for this dataset.</p>';
  }}
}}
</script>
</body>
</html>
"""

    return html