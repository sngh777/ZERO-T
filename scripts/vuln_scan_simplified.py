import os
import time
import docker
from findContainers import find_web_containers
import requests
import random

# Initialize Docker client
client = docker.from_env()

def run_docker_bench():
    print("Running DockerBench security scan...")

    try:
        # Pull the Docker Bench Security image
        print("Pulling Docker Bench Security image...")
        client.images.pull("docker/docker-bench-security")

        # Run Docker Bench Security scan
        print("Starting Docker Bench Security scan...")
        container = client.containers.run(
            image="docker/docker-bench-security",
            remove=True,  # Remove the container after execution
            network_mode="host",  # Use host network
            pid_mode="host",  # Use host PID namespace
            userns_mode="host",  # Use host user namespace
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
        print(container.decode('utf-8'))  # Print container logs
    except docker.errors.APIError as e:
        print(f"Error running Docker Bench Security: {e}")


def start_zap_container():
    """Start ZAP Docker container on a random host port and return container & port"""
    client = docker.from_env()
    
    # Find a random available port on the host
    host_port = random.randint(8000, 8999)  # Random port in safe range
    
    # Start the ZAP container
    container = client.containers.run(
        image="zaproxy/zap-stable",
        command=f"zap.sh -daemon -host 0.0.0.0 -port 8080 -config api.disablekey=true",
        ports={'8080/tcp': host_port},  # Map container port 8080 to random host port
        detach=True,
        remove=True  # Auto-remove container when stopped
    )
    
    # Wait for ZAP to be ready
    zap_proxy = f"http://localhost:{host_port}"
    for _ in range(30):  # 30 second timeout
        try:
            if requests.get(f"{zap_proxy}/JSON/core/view/version/").status_code == 200:
                print(f"ZAP container started on port {host_port}")
                return container, host_port
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    
    raise RuntimeError("ZAP container failed to start")

def run_zap_scan(target_ip, target_port):
    """Run full ZAP scan against specified target"""
    container = None
    try:
        # Start ZAP container
        container, zap_host_port = start_zap_container()
        zap_proxy = f"http://localhost:{zap_host_port}"
        target_url = f"http://{target_ip}:{target_port}"

        # Start active scan
        print(f"Starting scan for {target_url}")
        scan_response = requests.get(
            f"{zap_proxy}/JSON/ascan/action/scan/",
            params={
                "url": target_url,
                "recurse": True,
                "inScopeOnly": True,
                "scanPolicyName": "Default Policy"
            }
        )
        scan_id = scan_response.json().get("scan")

        # Monitor scan progress
        while True:
            status_response = requests.get(
                f"{zap_proxy}/JSON/ascan/view/status/",
                params={"scanId": scan_id}
            )
            status = status_response.json().get("status")
            print(f"Scan progress: {status}%")
            if status == "100":
                break
            time.sleep(5)

        # Generate report
        report_response = requests.get(f"{zap_proxy}/OTHER/core/other/htmlreport/")
        report_filename = f"zap_report_{target_ip}_{target_port}.html"
        with open(report_filename, "wb") as f:
            f.write(report_response.content)
        
        print(f"Scan complete! Report saved to {report_filename}")
        return report_filename

    finally:
        # Clean up container
        if container:
            container.stop()

def run_trivy_scan(image_name):
    if not image_name or image_name.lower() == "n/a":
        print(f"Skipping scan: Invalid image name '{image_name}'.")
        return

    print(f"Running Trivy compliance and vulnerability scans on '{image_name}'...")

    try:
        # Pull the Trivy image
        print("Pulling Trivy image...")
        client.images.pull("aquasec/trivy")

        # Run Trivy compliance scan
        print("Running Trivy compliance scan...")
        compliance_container = client.containers.run(
            image="aquasec/trivy",
            command=f"image --compliance docker-cis-1.6.0 {image_name}",
            remove=True,  # Remove the container after execution
            volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},  # Mount Docker socket
            detach=False  # Run in the foreground
        )
        print(compliance_container.decode('utf-8'))  # Print compliance scan logs

        # Run Trivy vulnerability scan
        print("Running Trivy vulnerability scan...")
        vuln_container = client.containers.run(
            image="aquasec/trivy",
            command=f"image {image_name}",
            remove=True,  # Remove the container after execution
            volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},  # Mount Docker socket
            detach=False  # Run in the foreground
        )
        print(vuln_container.decode('utf-8'))  # Print vulnerability scan logs
    except docker.errors.APIError as e:
        print(f"Error running Trivy: {e}")

def run_nmap_scan(target_ip):
    print("Starting Nmap scan...")

    try:
        # Pull the Nmap image
        print("Pulling Nmap image...")
        client.images.pull("instrumentisto/nmap")

        # Run Nmap scan
        print(f"Scanning target: {target_ip}")
        container = client.containers.run(
            image="instrumentisto/nmap",
            command=f"-sV -Pn {target_ip}",
            remove=True,  # Remove the container after execution
            detach=False  # Run in the foreground
        )
        print(container.decode('utf-8'))  # Print Nmap scan logs
    except docker.errors.APIError as e:
        print(f"Error running Nmap: {e}")

def main():
    # Find all web containers
    web_containers = find_web_containers()

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

        # Run OWASP ZAP scan if IP and port are available
        if container.get('ip') != 'N/A' and container.get('host_port') != 'N/A':
            run_zap_scan(container['ip'], container['host_port'])
        time.sleep(2)

        # Run Nmap scan
        if container.get('ip') != 'N/A':
            run_nmap_scan(container['ip'])
        time.sleep(2)

if __name__ == '__main__':
    main()
