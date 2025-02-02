import os
import time
import docker
from findContainers import find_web_containers
#from zap_scan_v2 import run_zap_scan


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

def run_zap_scan(target_host, target_port):
    """
    Run an OWASP ZAP scan on the specified target host and port using the newer zaproxy/zap-stable image.
    
    :param target_host: The host to scan (e.g., 'localhost').
    :param target_port: The port to scan (e.g., 8080).
    """
    print(f"Running OWASP ZAP scan on {target_host}:{target_port}...")

    try:
        # Pull the newer OWASP ZAP image
        print("Pulling OWASP ZAP image (zaproxy/zap-stable)...")
        client.images.pull("zaproxy/zap-stable")

        # Define the output directory for ZAP reports
        output_dir = os.path.join(os.getcwd(), "zap_reports")
        os.makedirs(output_dir, exist_ok=True)  # Create the directory if it doesn't exist

        # Run OWASP ZAP scan
        print("Starting OWASP ZAP scan...")
        container = client.containers.run(
            image="zaproxy/zap-stable",
            command=f"zap-baseline.py -t http://{target_host}:{target_port} -r zap_report.html -J zap_out.json",
            remove=True,  # Remove the container after execution
            volumes={output_dir: {"bind": "/zap/wrk", "mode": "rw"}},  # Mount the output directory
            detach=False  # Run in the foreground
        )
        print(container.decode('utf-8'))  # Print ZAP scan logs
        print(f"ZAP scan completed. Reports saved in '{output_dir}'.")
    except Exception as e:
        print(f"Error running OWASP ZAP: {e}")




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


        

def run_nmap_scan_dockerized(host, port):
    print("Pulling Nmap image...")
    client.images.pull("instrumentisto/nmap")
    """
    Run Nmap scan using a Dockerized Nmap tool on the host's mapped port.
    """
    print(f"Running Dockerized Nmap scan on {host}:{port}...")

    try:
        # Run Nmap scan using the instrumentisto/nmap image
        container = client.containers.run(
            image="instrumentisto/nmap",
            command=f"-sV -Pn {host} -p {port}",  # Scan the host and specific port
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
    '''
    #run_docker_bench()
    time.sleep(2)
    '''

    # Iterate over each web container and run scans
    for container in web_containers:
        #print(f"Scanning container: {container['name']} at {container['ip']}:{container['host_port']}")

        # Run Trivy scan
        #run_trivy_scan(container['image'])
        #time.sleep(2)

        # Run OWASP ZAP scan if IP and port are available
        if container.get('ip') != 'N/A' and container.get('host_port') != 'N/A':
            run_zap_scan(container['ip'], container['host_port'])
        time.sleep(2)

        # Run Nmap scan
        if container.get('ip') != 'N/A' and container.get('host_port') != 'N/A':
            run_nmap_scan_dockerized(container['ip'],container['host_port'])
        time.sleep(2)

if __name__ == '__main__':
    main()
