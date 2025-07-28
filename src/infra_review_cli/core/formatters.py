# src/infra_review_cli/formatters.py

import json
import datetime

from markdown_it import MarkdownIt

def format_as_text(findings):
    """Formats findings as plain text for the console."""
    if not findings:
        return "✅ No underutilized EC2 instances found."

    output = [f"🔎 {len(findings)} finding(s) found:\n"]
    for f in findings:
        output.append(
            f"🛠️  Finding ID: {f.finding_id}\n"
            f"🔎 Resource ID: {f.resource_id}\n"
            f"📍 Region     : {f.region}\n"
            f"🏛️  Pillar     : {f.pillar.value}\n"
            f"🚨 Severity   : {f.severity.value}\n"
            f"⚙️  Effort     : {f.effort.value}\n"
            f"🧠 Headline   : {f.headline}\n"
            f"📖 Description: {f.detailed_description}\n"
            f"🛠 Remediation: {f.remediation_steps}\n"

        )

        if f.estimated_savings > 0:
            output.append(f"💰 Estimated monthly savings: ${f.estimated_savings:.2f}")
        output.append("-" * 60)
    return "\n".join(output)

def format_as_json(findings):
    """Formats findings as a JSON string."""
    findings_list = [f.__dict__ for f in findings]
    return json.dumps(findings_list, indent=2)



def format_as_html(findings, logo_url=None, custom_colors=None):
    """
    Formats a list of findings into a modern, customizable HTML report.

    Args:
        findings (list): A list of Finding objects.
        logo_url (str, optional): URL or Base64 data URI for a logo. Defaults to None.
        custom_colors (dict, optional): A dictionary to override default theme colors.
                                         Defaults to None.

    Returns:
        str: A complete HTML document as a string.
    """
    # --- 1. Define Theme Colors (Defaults can be overridden) ---
    colors = {
        '--bg-color': '#f8f9fa',
        '--primary-text-color': '#000000',
        '--secondary-text-color': '#002856',
        '--card-bg-color': '#ffffff',
        '--card-border-color': '#dee2e6',
        '--header-bg-color': '#002856',
        '--header-text-color': '#ffffff',
        '--accent-color': '#002856',
        '--hover-color': '#f1f3f5',
        '--severity-high-bg': '#dc3545',
        '--severity-medium-bg': '#ffc107',
        '--severity-medium-text': '#000',
        '--severity-low-bg': '#0dcaf0',
    }
    if custom_colors:
        colors.update(custom_colors)

    color_vars_style = "; ".join([f"{key}: {value}" for key, value in colors.items()])

    # --- 2. Build Report Header ---
    logo_html = f'<img src="{logo_url}" alt="Company Logo" class="logo">' if logo_url else ''
    total_findings = len(findings)
    total_savings = sum(f.estimated_savings for f in findings)
    report_date = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    # --- 3. Build Report Body (Either Findings Table or "No Findings" Message) ---
    md = MarkdownIt()
    if not findings:
        report_body_html = """
            <div class="card no-findings">
                <h2>✅ No Findings</h2>
                <p>Excellent! No underutilized resources were found during this scan.</p>
            </div>
        """
    else:
        table_rows_html = ""
        for f in findings:
            severity_class = f.severity.value.lower()
            remediation_html = md.render(f.remediation_steps)
            table_rows_html += f"""
                <tr>
                    <td>{f.resource_id}</td>
                    <td>{f.region}</td>
                    <td><span class="severity-badge severity-{severity_class}">{f.severity.value}</span></td>
                    <td>
                        <div class="headline">{f.headline}</div>
                        <div class="finding-id">ID: {f.finding_id}</div>
                    </td>
                    <td class="savings">${f.estimated_savings:,.2f}</td>
                    <td class="remediation">{remediation_html}</td>
                </tr>
            """

        report_body_html = f"""
            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>Resource ID</th>
                            <th>Region</th>
                            <th>Severity</th>
                            <th>Finding</th>
                            <th>Est. Monthly Savings</th>
                            <th>Remediation Steps</th>
                        </tr>
                    </thead>
                    <tbody>{table_rows_html}</tbody>
                </table>
            </div>
        """

    # --- 4. Assemble Final HTML Document ---
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Infrastructure Review Report</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Dosis:wght@400;600&display=swap');
            :root {{ {color_vars_style}; }}

            body {{
                font-family: 'Dosis', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                margin: 0;
                background-color: var(--bg-color);
                color: var(--primary-text-color);
                line-height: 1.6;
            }}
            .report-container {{
                max-width: 1200px;
                margin: 2rem auto;
                padding: 0 1rem;
            }}
            .report-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2rem;
                padding-bottom: 1rem;
                border-bottom: 1px solid var(--card-border-color);
            }}
            .logo {{
                max-height: 50px;
            }}
            .report-title h1 {{
                margin: 0;
                font-size: 1.75rem;
                font-weight: 600;
            }}
            .report-title p {{
                margin: 0;
                color: var(--secondary-text-color);
                font-size: 0.9rem;
            }}
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }}
            .summary-item {{
                background-color: var(--accent-color);
                border: 1px solid var(--card-border-color);
                border-radius: 8px;
                padding: 1.5rem;
                text-align: center;
            }}
            .summary-item .label {{
                font-size: 0.9rem;
                color: var(--secondary-text-color);
                margin-bottom: 0.5rem;
            }}
            .summary-item .value {{
                font-size: 2rem;
                font-weight: 700;
                color: var(--accent-color);
            }}
            .card {{
                background-color: var(--card-bg-color);
                border: 1px solid var(--card-border-color);
                border-radius: 8px;
                overflow: hidden; /* For rounded corners on the table */
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            }}
            .no-findings {{
                padding: 2rem;
                text-align: center;
            }}
            .no-findings h2 {{ margin-top: 0; }}

            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th, td {{
                padding: 12px 16px;
                text-align: left;
                vertical-align: top;
                border-bottom: 1px solid var(--card-border-color);
            }}
            thead {{
                background-color: var(--header-bg-color);
                color: var(--header-text-color);
            }}
            thead th {{
                font-weight: 600;
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            tbody tr:last-child td {{
                border-bottom: none;
            }}
            tbody tr:hover {{
                background-color: var(--hover-color);
            }}
            .headline {{ font-weight: 600; }}
            .finding-id {{ font-size: 0.8rem; color: var(--secondary-text-color); }}
            .savings {{ font-weight: 700; color: var(--accent-color); }}

            .severity-badge {{
                display: inline-block;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 0.8rem;
                font-weight: 700;
                color: #fff;
                text-transform: uppercase;
            }}
            .severity-high {{ background-color: var(--severity-high-bg); }}
            .severity-critical {{ background-color: var(--severity-high-bg); }}
            .severity-medium {{ background-color: var(--severity-medium-bg); color: var(--severity-medium-text); }}
            .severity-low {{ background-color: var(--severity-low-bg); color: var(--severity-medium-text); }}

            .remediation ul {{ margin: 0; padding-left: 20px; }}
            .remediation li {{ margin-bottom: 5px; }}
            .remediation code {{
                background-color: #e9ecef;
                padding: 2px 5px;
                border-radius: 4px;
                font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
            }}
            @media (max-width: 768px) {{
                .report-header {{ flex-direction: column; align-items: flex-start; gap: 1rem; }}
                .card {{ overflow-x: auto; }} /* Allow table to scroll horizontally */
            }}
        </style>
    </head>
    <body>
        <div class="report-container">
            <header class="report-header">
                <div class="report-title">
                    <h1>Infrastructure Review</h1>
                    <p>Generated on {report_date}</p>
                </div>
                {logo_html}
            </header>

            <main>
                <div class="summary-grid">
                    <div class="summary-item">
                        <div class="label">Total Findings</div>
                        <div class="value">{total_findings}</div>
                    </div>
                    <div class="summary-item">
                        <div class="label">Total Estimated Monthly Savings</div>
                        <div class="value">${total_savings:,.2f}</div>
                    </div>
                </div>

                {report_body_html}
            </main>
        </div>
    </body>
    </html>
    """