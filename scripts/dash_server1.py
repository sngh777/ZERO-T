import os
import json
import socket
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

# Directory to store scan reports
REPORT_DIR = "scan_reports"

# Plotly Dash app setup
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Helper functions
def load_reports():
    report_files = [f for f in os.listdir(REPORT_DIR) if f.endswith(".json")]
    reports = {}
    for file in report_files:
        with open(os.path.join(REPORT_DIR, file), "r") as f:
            reports[file] = json.load(f)
    return reports


def generate_graphs():
    reports = load_reports()
    graph_data = []

    for name, report_content in reports.items():
        if isinstance(report_content, list):
            issue_count = len(report_content)
            tool = "DockerBench" if "docker_bench" in name else ("Trivy" if "trivy" in name else "Nmap")
            graph_data.append({"Tool": tool, "Report": name, "Issues": issue_count})

    if graph_data:
        df = pd.DataFrame(graph_data)
        return dcc.Graph(figure=px.bar(df, x="Report", y="Issues", color="Tool", title="Security Scan Issues"))
    return html.Div("No graph data available.")


app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Security Scan Dashboard", className="text-center text-primary my-4"))),
    dcc.Tabs(id="report-tabs", value='docker_bench_report', children=[
        dcc.Tab(label=report_name, value=report_name) for report_name in load_reports().keys()
    ]),
    html.Div(id='report-content', style={"whiteSpace": "pre-wrap", "backgroundColor": "#f8f9fa", "padding": "15px", "borderRadius": "5px"}),
    html.Br(),
    html.Div(generate_graphs())
])


@app.callback(
    Output('report-content', 'children'),
    Input('report-tabs', 'value')
)
def display_report_content(selected_report):
    reports = load_reports()
    report_content = reports.get(selected_report, {})
    return json.dumps(report_content, indent=4) if report_content else "No report content available."


def find_available_port(start_port=8080):
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("localhost", port)) != 0:
                return port
            port += 1


def main():
    available_port = find_available_port(8080)
    print(f"Launching Dash app on port {available_port}")
    app.run_server(host="localhost", port=available_port, debug=False)


if __name__ == '__main__':
    main()
