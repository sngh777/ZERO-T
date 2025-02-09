import os
import time
import json
import docker
import socket
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from find_viaSSH import find_web_containers_via_ssh
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
        # Pull the Docker Bench Security image
        print("Pulling Docker Bench Security image...")
        client.images.pull("docker/docker-bench-security")

        # Run Docker Bench Security scan
        print("Starting Docker Bench Security scan...")
        logs = client.containers.run(
            image="docker/docker-bench-security",
            remove=True,  # Remove the container after execution
            network_mode="host",  # Use host network
            pid_mode="host",  # Use host PID namespace
            userns_mode="host", # Use host user namespace
            privileged=True,  # Run with privileged mode
            working_dir="/usr/local/bin",
            cap_add=["audit_control"],  # Add audit_control capability
            environment={"DOCKER_CONTENT_TRUST": os.getenv("DOCKER_CONTENT_TRUST", "")},  # Pass environment variable
            volumes={
                "/etc": {"bind": "/etc", "mode": "ro"},
                "/usr/bin/containerd": {"bind": "/usr/bin/containerd", "mode": "ro"},
                "/usr/bin/runc": {"bind": "/usr/bin/runc", "mode": "ro"},
                "/usr/lib/systemd": {"bind": "/usr/lib/systemd", "mode": "ro"},
                "/var/lib": {"bind": "/var/lib", "mode": "ro"},
                "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "ro"}
            },
            labels={"docker_bench_security": ""},  # Add a label
            detach=False  # Run in the foreground
        )
        report_path = os.path.join(REPORT_DIR, "docker_bench_report.txt")
        with open(report_path, "w") as f:
            f.write(logs.decode("utf-8"))
        print(f"DockerBench report saved to {report_path}")
    except docker.errors.APIError as e:
        print(f"Error running Docker Bench Security: {e}")

# Other scanning functions remain unchanged
def sanitize_filename(name):
    # Remove special characters and replace spaces with underscores
    return re.sub(r'[^A-Za-z0-9_.]+', '_', name)

def run_trivy_scan(image_name):
    if not image_name or image_name.lower() == "n/a":
        print(f"Skipping scan: Invalid image name '{image_name}'.")
        return

    sanitized_name = sanitize_filename(image_name)

    try:
        client.images.pull("aquasec/trivy")
        logs = client.containers.run(
            image="aquasec/trivy",
            command=f"image {image_name}",
            remove=True,
            volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},
            detach=False
        )
        report_path = os.path.join(REPORT_DIR, f"trivy_report_{sanitized_name}.txt")
        with open(report_path, "w") as f:
            f.write(logs.decode("utf-8"))
        print(f"Trivy report for {image_name} saved to {report_path}")
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

# Load scan reports
def load_reports():
    report_files = [f for f in os.listdir(REPORT_DIR) if f.endswith(".txt")]
    reports = {}
    for file in report_files:
        with open(os.path.join(REPORT_DIR, file), "r") as f:
            reports[file] = f.read()
    return reports

# Layout for Plotly Dash
app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Security Scan Dashboard", className="text-center text-primary my-4"))),
    dcc.Tabs(id="report-tabs", value='docker_bench_report', children=[
        dcc.Tab(label=report_name, value=report_name) for report_name in load_reports().keys()
    ]),
    html.Div(id='report-content', style={"whiteSpace": "pre-wrap", "backgroundColor": "#f8f9fa", "padding": "15px", "borderRadius": "5px"})
])

# Callback to update report content
@app.callback(
    Output('report-content', 'children'),
    [Input('report-tabs', 'value')]
)
def display_report_content(selected_report):
    reports = load_reports()
    return reports.get(selected_report, "No report content available.")

# Helper to find available port
def find_available_port(start_port=8080):
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("0.0.0.0", port)) != 0:
                return port
            port += 1

# Main execution
def main():
    # Find all web containers
    web_containers = find_web_containers_via_ssh()

    if not web_containers:
        print("No web containers found.")
        return

    # Run Docker Bench security scan
    run_docker_bench()
    time.sleep(2)

    # Iterate over each web container and run scans
    for container in web_containers:
        print(f"Scanning container: {container['name']} at 34.207.159.185:{container['host_port']}")

        # Run Trivy scan
        run_trivy_scan(container['image'])
        time.sleep(2)

        # Run Nmap scan
        if container.get('host_port'):
            run_nmap_scan_dockerized("34.207.159.185", container['host_port'])
        time.sleep(2)

    # Launch the dashboard
    available_port = find_available_port(8080)
    print(f"Launching Dash app on port {available_port}")
    app.run_server(host="0.0.0.0", port=available_port, debug=True)

if __name__ == '__main__':
    main()
