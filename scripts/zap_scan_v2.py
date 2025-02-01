import time
import requests
import docker
import random
import socket

def is_port_busy(port):
    """Check if a port is busy on the host"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))  # Try to bind to the port
            return False  # Port is available
        except socket.error:
            return True  # Port is busy

def get_available_port():
    """Find an available random port on the host"""
    while True:
        port = random.randint(8000, 8999)  # Random port in safe range
        if not is_port_busy(port):  # Check if port is available
            return port

def start_zap_container():
    """Start ZAP Docker container on an available random host port and return container & port"""
    client = docker.from_env()
    
    # Find an available random port
    host_port = get_available_port()
    print(f"Attempting to start ZAP container on port {host_port}...")
    
    # Start the ZAP container
    try:
        container = client.containers.run(
              image="zaproxy/zap-stable",
              command=f"zap.sh -daemon -host 0.0.0.0 -port {host_port} -config api.disablekey=true",
              ports={f"{host_port}/tcp": host_port},  # Bind host and container to the same port
              detach=True,
              remove=Truez
              environment=["ZAP_JVM_OPTIONS=-Xmx2048m"]
        )

    except docker.errors.APIError as e:
        print(f"Error starting ZAP container: {e}")
        raise RuntimeError("Failed to start ZAP container")
    
    # Wait for ZAP to be ready
    zap_proxy = f"http://localhost:{host_port}"
    print(f"Waiting for ZAP API to be ready at {zap_proxy}...")
    for _ in range(120):  # 60 second timeout
        try:
            if requests.get(f"{zap_proxy}/JSON/core/view/version/").status_code == 200:
                print(f"ZAP container started on port {host_port}")
                return container, host_port
        except requests.exceptions.ConnectionError as e:
            print(f"Waiting for ZAP API to start... ({e})")
            time.sleep(1)
    
    # Print container logs if the API fails to start
    print("ZAP container logs:")
    print(container.logs().decode('utf-8'))
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




