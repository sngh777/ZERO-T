import os
import time
import json
import re
import docker
import socket
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from find_viaSSH import find_web_containers_via_ssh

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
        report_path = os.path.join(REPORT_DIR, "docker_bench_report.txt")
        with open(report_path, "w") as f:
            f.write(logs.decode("utf-8"))
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
            detach=False,
         
        )

        compliance_logs.wait()  # Wait for container to finish
    
        compliance_report_path = os.path.join(REPORT_DIR, f"trivy_compliance_report_{sanitize_filename(image_name)}.txt")
        with open(compliance_report_path, "w") as f:
            f.write(compliance_logs.decode('utf-8'))
        print(f"Trivy compliance report for {image_name} saved to {compliance_report_path}")
        compliance_logs.remove()
        print("Running Trivy vulnerability scan...")
        vuln_logs = client.containers.run(
            image="aquasec/trivy",
            command=f"image {image_name}",
            remove=True,
            volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},
            detach=False,
           
        )

        vuln_logs.wait()
        vuln_report_path = os.path.join(REPORT_DIR, f"trivy_vuln_report_{sanitize_filename(image_name)}.txt")
        with open(vuln_report_path, "w") as f:
            f.write(vuln_logs.decode('utf-8'))
        print(f"Trivy vulnerability report for {image_name} saved to {vuln_report_path}")
        vuln_logs.remove()
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
        report_path = os.path.join(REPORT_DIR, f"nmap_report_{host}_{port}.txt")
        with open(report_path, "w") as f:
            f.write(logs.decode("utf-8"))
        print(f"Nmap report for {host}:{port} saved to {report_path}")
    except docker.errors.APIError as e:
        print(f"Error running Nmap: {e}")


def parse_trivy_vuln_report(report_path):
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    try:
        with open(report_path, "r") as f:
            for line in f:
                for severity in severity_counts.keys():
                    if f"{severity}" in line:
                        severity_counts[severity] += 1
    except FileNotFoundError:
        print(f"Report file '{report_path}' not found.")
    return severity_counts


def generate_vuln_graph(severity_counts):
    fig = go.Figure([go.Bar(x=list(severity_counts.keys()), y=list(severity_counts.values()), marker_color='orange')])
    fig.update_layout(title_text="Trivy Vulnerability Severity Counts", xaxis_title="Severity", yaxis_title="Count")
    return fig


app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Security Scan Dashboard", className="text-center text-primary my-4"))),
    dcc.Tabs(id="report-tabs", value='docker_bench_report', children=[
        dcc.Tab(label=report_name, value=report_name) for report_name in os.listdir(REPORT_DIR)
    ]),
    html.Div(id='report-content', style={"whiteSpace": "pre-wrap", "backgroundColor": "#f8f9fa", "padding": "15px", "borderRadius": "5px"}),
    dcc.Graph(id='vuln-graph', style={"display": "none"})
])


@app.callback(
    [Output('report-content', 'children'), Output('vuln-graph', 'figure'), Output('vuln-graph', 'style')],
    Input('report-tabs', 'value')
)
def display_report_content(selected_report):
    report_path = os.path.join(REPORT_DIR, selected_report)
    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            report_content = f.read()

        if selected_report.startswith("trivy_vuln_report"):
            severity_counts = parse_trivy_vuln_report(report_path)
            graph = generate_vuln_graph(severity_counts)
            return report_content, graph, {"display": "block"}

        return report_content, {}, {"display": "none"}

    return "No report content available.", {}, {"display": "none"}


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
