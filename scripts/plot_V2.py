import os
import time
import json
import docker
import socket
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
from find_viaSSH import find_web_containers_via_ssh
import plotly.express as px
import pandas as pd
import re

# Initialize Docker client
client = docker.from_env()

# Directory to store scan reports
REPORT_DIR = "scan_reports"
try:
    os.makedirs(REPORT_DIR, exist_ok=True)
except PermissionError as e:
    print(f"Permission error creating directory '{REPORT_DIR}': {e}")
    exit(1)

# Plotly Dash app setup
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Helper functions
def run_docker_bench():
    print("Running DockerBench security scan...")

    try:
        print("Pulling Docker Bench Security image...")
        client.images.pull("docker/docker-bench-security")

        print("Starting Docker Bench Security scan...")
        logs = client.containers.run(
            image="docker/docker-bench-security",
            remove=True,
            volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},
            tty=True,
            privileged=True
        )
        report_path = os.path.join(REPORT_DIR, "docker_bench_report.json")
        report_data = parse_docker_bench_logs(logs.decode("utf-8"))
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=4)
        print(f"DockerBench report saved to {report_path}")
    except docker.errors.APIError as e:
        print(f"Error running Docker Bench Security: {e}")


def sanitize_filename(name):
    return re.sub(r'[^A-Za-z0-9_.]+', '_', name)


def run_trivy_scan(image_name):
    if not image_name or image_name.lower() == "n/a":
        print(f"Skipping scan: Invalid image name '{image_name}'.")
        return

    print(f"Running Trivy compliance and vulnerability scans on '{image_name}'...")

    try:
        print("Pulling Trivy image...")
        client.images.pull("aquasec/trivy")

        print("Running Trivy compliance scan...")
        compliance_logs = client.containers.run(
            image="aquasec/trivy",
            command=f"image --compliance docker-cis-1.6.0 {image_name}",
            remove=True,
            volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},
            detach=False
        )
        compliance_data = parse_trivy_logs(compliance_logs.decode('utf-8'))
        compliance_report_path = os.path.join(REPORT_DIR, f"trivy_compliance_report_{sanitize_filename(image_name)}.json")
        with open(compliance_report_path, "w") as f:
            json.dump(compliance_data, f, indent=4)
        print(f"Trivy compliance report for {image_name} saved to {compliance_report_path}")

        print("Running Trivy vulnerability scan...")
        vuln_logs = client.containers.run(
            image="aquasec/trivy",
            command=f"image {image_name}",
            remove=True,
            volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},
            detach=False
        )
        vuln_data = parse_trivy_logs(vuln_logs.decode('utf-8'))
        vuln_report_path = os.path.join(REPORT_DIR, f"trivy_vuln_report_{sanitize_filename(image_name)}.json")
        with open(vuln_report_path, "w") as f:
            json.dump(vuln_data, f, indent=4)
        print(f"Trivy vulnerability report for {image_name} saved to {vuln_report_path}")

    except docker.errors.APIError as e:
        print(f"Error running Trivy: {e}")


def run_nmap_scan_dockerized(host, port):
    print(f"Running Dockerized Nmap scan on {host}:{port}...")
    try:
        client.images.pull("instrumentisto/nmap")
        logs = client.containers.run(
            image="instrumentisto/nmap",
            command=f"-sV -Pn {host} -p {port}",
            remove=True,
            network_mode="host",
            detach=False
        )
        report_path = os.path.join(REPORT_DIR, f"nmap_report_{host}_{port}.json")
        report_data = parse_nmap_logs(logs.decode("utf-8"))
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=4)
        print(f"Nmap report for {host}:{port} saved to {report_path}")
    except docker.errors.APIError as e:
        print(f"Error running Nmap: {e}")


def parse_docker_bench_logs(logs):
    parsed = []
    for line in logs.splitlines():
        if "[WARN]" in line or "[INFO]" in line or "[PASS]" in line:
            status = "WARNING" if "[WARN]" in line else ("PASS" if "[PASS]" in line else "INFO")
            parsed.append({"status": status, "message": line})
    return parsed


def parse_trivy_logs(logs):
    issues = []
    for line in logs.splitlines():
        match = re.search(r'(CRITICAL|HIGH|MEDIUM|LOW|UNKNOWN)', line)
        if match:
            issues.append({"severity": match.group(1), "detail": line})
    return issues


def parse_nmap_logs(logs):
    parsed = []
    for line in logs.splitlines():
        if "open" in line or "closed" in line or "filtered" in line:
            parsed.append({"port_status": line.strip()})
    return parsed


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
    web_containers = find_web_containers_via_ssh()

    if not web_containers:
        print("No web containers found.")
        return

    run_docker_bench()
    time.sleep(2)

    for container in web_containers:
        print(f"Scanning container: {container['name']} at 34.207.159.185:{container['host_port']}")
        if container.get('host_port'):
            run_trivy_scan(container['image'])
        time.sleep(2)

        if container.get('host_port'):
            run_nmap_scan_dockerized("34.207.159.185", container['host_port'])
        time.sleep(2)

    available_port = find_available_port(8080)
    print(f"Launching Dash app on port {available_port}")
    app.run_server(host="localhost", port=available_port, debug=False)


if __name__ == '__main__':
    main()
