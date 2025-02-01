#!/usr/bin/env python3
import random
import socket
import subprocess
import time
from zapv2 import ZAPv2

def is_port_in_use(port, host='127.0.0.1'):
    """
    Check if the given port is in use on the specified host.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def get_free_port(low=8000, high=9000):
    """
    Select a random port between low and high that is not currently in use.
    """
    while True:
        port = random.randint(low, high)
        if not is_port_in_use(port):
            return port

def run_zap_scan(target_ip, target_port):
    """
    Start the OWASP ZAP container on a random free host port, scan the target
    identified by target_ip and target_port, and then shutdown the container.
    
    Parameters:
        target_ip (str): The IP address or hostname of the target.
        target_port (int): The port number of the target.
    """
    # Build target URL
    target = f'http://{target_ip}:{target_port}'
    
    # Choose a random host port for mapping ZAP's API port (container port 8080)
    zap_host_port = get_free_port(8000, 9000)
    print(f"Using host port {zap_host_port} for ZAP API mapping.")

    # Start the OWASP ZAP Docker container in daemon mode.
    # You can use either owasp/zap2docker-stable or zaproxy/zap-stable.
    docker_cmd = [
        "docker", "run", "-d", "--rm",
        "-u", "zap",
        "--name", "zap_instance",
        "-p", f"{zap_host_port}:8080",
        "owasp/zap2docker-stable",  # or "zaproxy/zap-stable"
        "zap.sh", "-daemon",
        "-port", "8080",
        "-host", "0.0.0.0",
        "-config", "api.disablekey=true"
    ]
    
    print("Starting ZAP container...")
    try:
        container_id = subprocess.check_output(docker_cmd).decode().strip()
        print(f"ZAP container started with container ID: {container_id}")
    except subprocess.CalledProcessError as e:
        print("Error starting ZAP container:", e)
        return

    # Wait a few seconds to allow ZAP to fully start up.
    time.sleep(10)

    # Configure the ZAP API client to connect via the randomly chosen port.
    zap_proxy = f'http://127.0.0.1:{zap_host_port}'
    zap = ZAPv2(apikey='', proxies={'http': zap_proxy, 'https': zap_proxy})
    
    # Access the target so that ZAP records it in its history.
    print(f"Accessing target: {target}")
    try:
        zap.urlopen(target)
    except Exception as e:
        print(f"Error opening target: {e}")
    time.sleep(2)  # Allow time for the initial request.

    # Spider the target.
    print(f"Spidering target: {target}")
    spider_scan_id = zap.spider.scan(target)
    while int(zap.spider.status(spider_scan_id)) < 100:
        progress = zap.spider.status(spider_scan_id)
        print(f"Spider progress: {progress}%")
        time.sleep(2)
    print("Spidering completed.")

    # Perform an active scan.
    print(f"Starting Active Scan on target: {target}")
    ascan_scan_id = zap.ascan.scan(target)
    while int(zap.ascan.status(ascan_scan_id)) < 100:
        progress = zap.ascan.status(ascan_scan_id)
        print(f"Active scan progress: {progress}%")
        time.sleep(5)
    print("Active scanning completed.")

    # Retrieve and print alerts.
    alerts = zap.core.alerts(baseurl=target)
    if alerts:
        print("Alerts found:")
        for alert in alerts:
            print(f"- {alert['alert']} (Risk: {alert['risk']}) at {alert['url']}")
    else:
        print("No alerts found.")

    print("ZAP scanning completed.")

    # Shutdown the ZAP container.
    print("Stopping ZAP container...")
    try:
        subprocess.run(["docker", "stop", "zap_instance"], check=True)
        print("ZAP container stopped.")
    except subprocess.CalledProcessError as e:
        print("Error stopping ZAP container:", e)

if __name__ == "__main__":
    # Example usage:
    # Provide the target IP and port to scan.
    target_ip = "myapp"     # Replace with target IP or container name
    target_port = 80        # Replace with target port

    run_zap_scan(target_ip, target_port)
