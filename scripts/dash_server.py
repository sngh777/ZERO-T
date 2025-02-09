import json
import os
import socket
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

REPORT_DIR = "scan_reports"

# Plotly Dash app setup
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])


def load_reports():
    report_files = [f for f in os.listdir(REPORT_DIR) if f.endswith(".json")]
    reports = {}
    for file in report_files:
        with open(os.path.join(REPORT_DIR, file), "r") as f:
            reports[file] = json.load(f)
    return reports


def generate_graphs():
    reports = load_reports()
    graph_components = []

    # DockerBench Graph
    docker_bench_data = [
        {"Report": name, "Issues": len(content)}
        for name, content in reports.items() if "docker_bench" in name
    ]
    if docker_bench_data:
        df_docker = pd.DataFrame(docker_bench_data)
        graph_components.append(dcc.Graph(
            figure=px.bar(df_docker, x="Report", y="Issues", title="DockerBench Issues Report")
        ))

    # Trivy Graph
    trivy_data = [
        {"Report": name, "Issues": len(content)}
        for name, content in reports.items() if "trivy" in name
    ]
    if trivy_data:
        df_trivy = pd.DataFrame(trivy_data)
        graph_components.append(dcc.Graph(
            figure=px.bar(df_trivy, x="Report", y="Issues", title="Trivy Issues Report")
        ))

    # Nmap Graph
    nmap_data = [
        {"Report": name, "Issues": len(content)}
        for name, content in reports.items() if "nmap" in name
    ]
    if nmap_data:
        df_nmap = pd.DataFrame(nmap_data)
        graph_components.append(dcc.Graph(
            figure=px.bar(df_nmap, x="Report", y="Issues", title="Nmap Issues Report")
        ))

    return graph_components if graph_components else [html.Div("No graph data available.")]


def find_available_port(start_port=8080):
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("localhost", port)) != 0:
                return port
            port += 1


app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Security Scan Dashboard", className="text-center text-primary my-4"))),
    dcc.Tabs(id="report-tabs", value='docker_bench_report', children=[
        dcc.Tab(label=report_name, value=report_name) for report_name in load_reports().keys()
    ]),
    html.Div(id='report-content', style={"whiteSpace": "pre-wrap", "backgroundColor": "#f8f9fa", "padding": "15px", "borderRadius": "5px"}),
    html.Br(),
    *generate_graphs()
])


@app.callback(
    Output('report-content', 'children'),
    Input('report-tabs', 'value')
)
def display_report_content(selected_report):
    reports = load_reports()
    report_content = reports.get(selected_report, {})
    return json.dumps(report_content, indent=4) if report_content else "No report content available."


if __name__ == '__main__':
    port = find_available_port(8080)
    print(f"Launching Dash app on port {port}")
    app.run_server(host="localhost", port=port, debug=False)
