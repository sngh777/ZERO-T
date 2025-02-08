import os
import time
import docker
import json
from find_viaSSH import find_web_containers_via_ssh
from zap_scan_almost import run_zap_scan

client = docker.from_env()

def save_to_allure_results(tool_name, report_content):
    os.makedirs("allure-results", exist_ok=True)
    output_path = f"allure-results/{tool_name}_report.json"
    with open(output_path, 'w') as file:
        json.dump(report_content, file)
    print(f"{tool_name} report saved to: {output_path}")

def run_docker_bench():
    print("Running Docker Bench Security scan...")
    try:
        client.images.pull("docker/docker-bench-security")
        container_logs = client.containers.run(
            image="docker/docker-bench-security",
            command="./docker-bench-security.sh",  # Explicit script call
            remove=True,
            network_mode="host",
            pid_mode="host",
            privileged=True,
            userns_mode="host",
            cap_add=["audit_control"],
            environment={"DOCKER_CONTENT_TRUST": os.getenv("DOCKER_CONTENT_TRUST", "")}, 
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
        print(container.decode('utf-8'))  # Print container logs
        report_data = [{"result": line.strip()} for line in container_logs.decode().split("\n") if line]
        save_to_allure_results("docker_bench_security", report_data)
    except docker.errors.APIError as e:
        print(f"Error running Docker Bench Security: {e}")

def run_trivy_scan(image_name):
    if not image_name or image_name.lower() == "n/a":
        print(f"Skipping scan: Invalid image name '{image_name}'.")
        return
    try:
        client.images.pull("aquasec/trivy")
        
        # Run Trivy scan with JSON output
        print(f"Running Trivy scan for image '{image_name}'...")
        scan_logs = client.containers.run(
            image="aquasec/trivy",
            command=f"image --format json {image_name}",
            remove=True,
            volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},
        )
        report_data = json.loads(scan_logs.decode())
        save_to_allure_results(f"trivy_{image_name.replace(':', '_')}", report_data)
    except (docker.errors.APIError, json.JSONDecodeError) as e:
        print(f"Error running Trivy: {e}")

def run_nmap_scan_dockerized(host, port):
    print(f"Running Nmap scan on {host}:{port}...")
    try:
        client.images.pull("instrumentisto/nmap")
        scan_logs = client.containers.run(
            image="instrumentisto/nmap",
            command=f"-sV -Pn -oX - {host} -p {port}",  # Output in XML
            remove=True,
            network_mode="host",
        )
        # Convert XML to a simple JSON-compatible structure
        report_data = {"host": host, "port": port, "scan_output": scan_logs.decode()}
        save_to_allure_results(f"nmap_{host}_{port}", report_data)
    except docker.errors.APIError as e:
        print(f"Error running Nmap: {e}")

def main():
    web_containers = find_web_containers_via_ssh()

    if not web_containers:
        print("No web containers found.")
        return

    run_docker_bench()
    time.sleep(2)

    for container in web_containers:
        print(f"Scanning container: {container['name']} at {container['ip']}:{container['host_port']}")
        run_trivy_scan(container['image'])
        time.sleep(2)

        if container.get('host_port'):
            run_zap_scan("34.207.159.185", container['host_port'])
        time.sleep(2)

        if container.get('host_port'):
            run_nmap_scan_dockerized("34.207.159.185", container['host_port'])
        time.sleep(2)

if __name__ == '__main__':
    main()
