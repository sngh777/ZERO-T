import time
import requests
import docker
from zapv2 import ZAPv2

def start_zap_container():
    """Start ZAP Docker container and return container instance and API port."""
    client = docker.from_env()

    # Start the ZAP container with dynamic port assignment
    try:
        container = client.containers.run(
            image="zaproxy/zap-stable",
            command="zap.sh -daemon -host 0.0.0.0 -port 8080 -config api.addrs.addr.name=0.0.0.0 -config api.addrs.addr.regex=true -config api.disablekey=true",
            ports={'8080/tcp': None},  # Let Docker assign a random host port
            detach=True,
            remove=True,
            environment=["ZAP_JVM_OPTIONS=-Xmx2048m"]
        )
    except docker.errors.APIError as e:
        print(f"Error starting ZAP container: {e}")
        raise RuntimeError("Failed to start ZAP container")

    # Retrieve the dynamically assigned host port
    container.reload()
    host_port = container.attrs['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort']
    print(f"ZAP container started on host port {host_port}")

    # Wait for ZAP to be ready
    zap_proxy = f"http://localhost:{host_port}"
    print(f"Waiting for ZAP API to be ready at {zap_proxy}...")
    for _ in range(120):  # 120 seconds timeout
        try:
            if requests.get(f"{zap_proxy}/JSON/core/view/version/").status_code == 200:
                print("ZAP API is ready.")
                return container, int(host_port)
        except requests.exceptions.ConnectionError:
            time.sleep(1)

    # Print container logs if the API fails to start
    print("ZAP container logs:")
    print(container.logs().decode('utf-8'))
    raise RuntimeError("ZAP container failed to start")

def run_zap_scan(target_url):
    """Run a full ZAP scan against the specified target URL."""
    container = None
    try:
        # Start ZAP container
        container, zap_host_port = start_zap_container()
        zap = ZAPv2(proxies={'http': f'http://localhost:{zap_host_port}', 'https': f'http://localhost:{zap_host_port}'})

        # Start spidering the target
        print(f"Spidering target: {target_url}")
        scan_id = zap.spider.scan(target_url)
        while int(zap.spider.status(scan_id)) < 100:
            print(f"Spider progress: {zap.spider.status(scan_id)}%")
            time.sleep(5)
        print("Spidering completed.")

        # Start active scan
        print(f"Starting active scan on target: {target_url}")
        scan_id = zap.ascan.scan(target_url)
        while int(zap.ascan.status(scan_id)) < 100:
            print(f"Active scan progress: {zap.ascan.status(scan_id)}%")
            time.sleep(5)
        print("Active scan completed.")

        # Generate report
        report_html = zap.core.htmlreport()
        report_filename = f"zap_report_{target_url.replace('://', '_').replace('/', '_')}.html"
        with open(report_filename, "w") as f:
            f.write(report_html)
        print(f"Scan complete! Report saved to {report_filename}")
        return report_filename

    finally:
        # Clean up container
        if container:
            container.stop()
            print("ZAP container stopped.")

