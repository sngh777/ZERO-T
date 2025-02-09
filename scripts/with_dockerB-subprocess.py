import os
import time
import json
import docker
import subprocess
from flask import Flask, render_template_string
from find_viaSSH import find_web_containers_via_ssh

# Initialize Docker client
client = docker.from_env()

# Directory to store scan reports
REPORT_DIR = "scan_reports"
os.makedirs(REPORT_DIR, exist_ok=True)

# Flask app setup
app = Flask(__name__)

def run_docker_bench():
    """ Run DockerBench security scan using subprocess and save output."""
    print("Running DockerBench security scan...")
    try:
        command = [
            "docker", "run", "--rm", "--privileged", "--net=host", "--pid=host", "docker/docker-bench-security"
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running Docker Bench Security: {result.stderr}")
        report_path = os.path.join(REPORT_DIR, "docker_bench_report.txt")
        with open(report_path, "w") as f:
            f.write(result.stdout)
        print(f"DockerBench report saved to {report_path}")
    except Exception as e:
        print(f"Error executing Docker Bench Security scan: {e}")


def run_trivy_scan(image_name):
    """ Run Trivy compliance and vulnerability scans and save output."""
    if not image_name or image_name.lower() == "n/a":
        print(f"Skipping scan: Invalid image name '{image_name}'.")
        return

    try:
        client.images.pull("aquasec/trivy")
        logs = client.containers.run(
            image="aquasec/trivy",
            command=f"image {image_name}",
            remove=True,
            volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},
            detach=False
        )
        report_path = os.path.join(REPORT_DIR, f"trivy_report_{image_name.replace(':', '_')}.txt")
        with open(report_path, "w") as f:
            f.write(logs.decode("utf-8"))
        print(f"Trivy report for {image_name} saved to {report_path}")
    except docker.errors.APIError as e:
        print(f"Error running Trivy: {e}")


def run_nmap_scan_dockerized(host, port):
    """ Run Nmap scan using a Dockerized Nmap tool on the host's mapped port."""
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


@app.route('/')
def dashboard():
    """ Render the security scan results on a web dashboard."""
    report_files = [f for f in os.listdir(REPORT_DIR) if f.endswith(".txt")]
    reports = {}
    for file in report_files:
        with open(os.path.join(REPORT_DIR, file), "r") as f:
            reports[file] = f.read()

    # Render basic HTML dashboard
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Security Scan Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            pre { background-color: #f8f9fa; padding: 10px; border-radius: 5px; }
            h2 { color: #007bff; }
        </style>
    </head>
    <body>
        <h1>Security Scan Reports</h1>
        {% for name, content in reports.items() %}
            <h2>{{ name }}</h2>
            <pre>{{ content }}</pre>
        {% endfor %}
    </body>
    </html>
    """
    return render_template_string(html_template, reports=reports)


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
        print(f"Scanning container: {container['name']} at {container['ip']}:{container['host_port']}")

        # Run Trivy scan
        run_trivy_scan(container['image'])
        time.sleep(2)

        # Run Nmap scan
        if container.get('host_port'):
            run_nmap_scan_dockerized(container['ip'], container['host_port'])
        time.sleep(2)

    # Launch the dashboard
    app.run(host="0.0.0.0", port=8080)


if __name__ == '__main__':
    main()
