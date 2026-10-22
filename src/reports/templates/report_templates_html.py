"""
HTML report templates for Retail BI Analyst.
"""

from __future__ import annotations

from typing import Dict, List
from datetime import datetime
import json

import pandas as pd

from core.analytics import KPIResult, RFMScores


def build_html_report(
    kpi: KPIResult,
    rfm: Dict[str, RFMScores],
    df: pd.DataFrame,
) -> str:
    """
    Build an interactive HTML report (single-page dashboard) using embedded data
    and Chart.js.

    - KPI cards at the top.
    - Line chart: revenue by date.
    - Bar chart: customers by RFM segment.
    """
    # --- Prepare data for charts ---

    # time series: revenue by date
    if (
        df is not None
        and not df.empty
        and "sale_date" in df.columns
        and "total_price" in df.columns
    ):
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

    # segment distribution
    segment_counts: Dict[str, int] = {}
    for scores in rfm.values():
        segment_counts[scores.segment] = segment_counts.get(scores.segment, 0) + 1
    segment_labels: List[str] = list(segment_counts.keys())
    segment_values: List[int] = list(segment_counts.values())

    json_revenue_labels = json.dumps(revenue_labels)
    json_revenue_values = json.dumps(revenue_values)
    json_segment_labels = json.dumps(segment_labels)
    json_segment_values = json.dumps(segment_values)

    # --- Build HTML ---
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Retail BI Analyst - Sales dashboard</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      padding: 24px;
      background-color: #f9fafb;
      color: #111827;
    }}
    h1 {{
      margin-bottom: 8px;
    }}
    .subheader {{
      margin-bottom: 24px;
      color: #6b7280;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }}
    .kpi-card {{
      background-color: #ffffff;
      border-radius: 8px;
      padding: 12px 16px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    .kpi-label {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #6b7280;
      margin-bottom: 4px;
    }}
    .kpi-value {{
      font-size: 20px;
      font-weight: 600;
      color: #111827;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 24px;
      align-items: flex-start;
    }}
    .card {{
      background-color: #ffffff;
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
      margin-bottom: 24px;
    }}
    canvas {{
      max-width: 100%;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }}
    th, td {{
      padding: 4px 8px;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
      white-space: nowrap;
    }}
    th {{
      background-color: #f3f4f6;
      font-weight: 600;
    }}
    tbody tr:nth-child(even) {{
      background-color: #f9fafb;
    }}
    .scroll-table {{
      max-height: 320px;
      overflow-y: auto;
    }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>Retail BI Analyst - Sales dashboard</h1>
  <p class="subheader">
    Total revenue: <strong>{kpi.total_revenue:,.2f}</strong>,
    average bill: <strong>{kpi.avg_ticket:,.2f}</strong>,
    transactions: <strong>{kpi.transactions_count}</strong>,
    customers: <strong>{kpi.unique_customers}</strong>
    {f"(up to {latest_date_str})" if latest_date_str else ""}
  </p>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Revenue per month</div>
      <div class="kpi-value">{kpi.revenue_per_month:,.2f}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Revenue per day</div>
      <div class="kpi-value">{kpi.revenue_per_day:,.2f}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Repeat-customer share</div>
      <div class="kpi-value">{kpi.repeat_customer_share:.1%}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Median bill</div>
      <div class="kpi-value">{kpi.median_ticket:,.2f}</div>
    </div>
  </div>

  <div class="layout">
    <div>
      <div class="card">
        <h2>Revenue by date</h2>
        <canvas id="revenueChart"></canvas>
      </div>
      <div class="card">
        <h2>Customers by RFM segment</h2>
        <canvas id="segmentChart"></canvas>
      </div>
    </div>
    <div class="card">
      <h2>RFM table</h2>
      <div class="scroll-table">
        <table>
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
        html += (
            f"<tr><td>{cid}</td>"
            f"<td>{scores.recency_days}</td>"
            f"<td>{scores.frequency}</td>"
            f"<td>{scores.monetary:,.2f}</td>"
            f"<td>{scores.segment}</td></tr>"
        )

    html += """
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const revenueLabels = """ + json_revenue_labels + """;
    const revenueValues = """ + json_revenue_values + """;
    const segmentLabels = """ + json_segment_labels + """;
    const segmentValues = """ + json_segment_values + """;

    if (revenueLabels.length > 0) {
      const ctxRevenue = document.getElementById('revenueChart').getContext('2d');
      new Chart(ctxRevenue, {
        type: 'line',
        data: {
          labels: revenueLabels,
          datasets: [{
            label: 'Revenue',
            data: revenueValues,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59,130,246,0.15)',
            tension: 0.2,
            pointRadius: 2
          }]
        },
        options: {
          scales: {
            x: {
              ticks: {
                maxTicksLimit: 10,
              }
            },
            y: {
              beginAtZero: true
            }
          }
        }
      });
    }

    if (segmentLabels.length > 0) {
      const ctxSegment = document.getElementById('segmentChart').getContext('2d');
      new Chart(ctxSegment, {
        type: 'bar',
        data: {
          labels: segmentLabels,
          datasets: [{
            label: 'Customers',
            data: segmentValues,
            backgroundColor: '#22c55e'
          }]
        },
        options: {
          scales: {
            x: {
              ticks: {
                maxTicksLimit: 6
              }
            },
            y: {
              beginAtZero: true,
              precision: 0
            }
          }
        }
      });
    }
  </script>
</body>
</html>
"""
    return html