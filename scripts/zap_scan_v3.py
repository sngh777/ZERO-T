import time
import subprocess
import socket
from zapv2 import ZAPv2

def find_free_port(start_port=8081):
    """Find a free port on the host starting from the specified port."""
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))  # Try to bind to the port
                return port  # Return the port if binding is successful
            except socket.error:
                port += 1  # Increment port and try again

def start_zap(port):
    """Start ZAP on the specified port."""
    zap_command = [
        'zap.sh',  # Path to ZAP executable (ensure it's in your PATH)
        '-daemon',  # Run in daemon mode
        '-host', '0.0.0.0',  # Bind to all interfaces
        '-port', str(port),  # Use the specified port
        '-config', 'api.disablekey=true'  # Disable API key for simplicity
    ]
    zap_process = subprocess.Popen(zap_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(10)  # Wait for ZAP to initialize
    return zap_process

def run_zap_scan(target_ip: str, target_port: int):
    try:
        # Find a free port for ZAP starting from 8081
        zap_port = find_free_port(start_port=8081)
        print(f"Starting ZAP on port: {zap_port}")

        # Start ZAP
        zap_process = start_zap(zap_port)

        # Ensure ZAP Python API is installed
        try:
            from zapv2 import ZAPv2
        except ImportError:
            print("Installing OWASP ZAP Python API...")
            subprocess.check_call(['pip', 'install', 'python-owasp-zap-v2.4'])
            from zapv2 import ZAPv2

        ZAP_BASE_URL = f'http://localhost:{zap_port}'
        target_url = f'http://{target_ip}:{target_port}'

        # Initialize ZAP with explicit API key (if configured)
        zap = ZAPv2(apikey=None, proxies={'http': ZAP_BASE_URL, 'https': ZAP_BASE_URL})

        # Test ZAP connection
        try:
            print("Checking ZAP connection...")
            print(zap.core.version)  # Simple API call to validate connectivity
        except Exception as e:
            print(f"Failed to connect to ZAP: {e}")
            zap_process.terminate()  # Stop ZAP if connection fails
            return

        # Access target
        try:
            print(f"Accessing target: {target_url}")
            zap.urlopen(target_url)
            time.sleep(2)
        except Exception as e:
            print(f"Failed to access target: {e}")
            zap_process.terminate()  # Stop ZAP if target access fails
            return

        # Spider scan
        try:
            print("Starting Spider scan...")
            spider_scan_id = zap.spider.scan(target_url)
            print(f"Spider Scan ID: {spider_scan_id}")

            while True:
                progress = zap.spider.status(spider_scan_id)
                print(f"Spider progress: {progress}%")
                if int(progress) >= 100:
                    break
                time.sleep(2)
            print("Spider scan completed.")
        except Exception as e:
            print(f"Spider scan failed: {e}")

        # Active scan
        try:
            print("Starting Active scan...")
            active_scan_id = zap.ascan.scan(target_url)
            print(f"Active Scan ID: {active_scan_id}")

            while True:
                progress = zap.ascan.status(active_scan_id)
                print(f"Active scan progress: {progress}%")
                if int(progress) >= 100:
                    break
                time.sleep(5)
            print("Active scan completed.")
        except Exception as e:
            print(f"Active scan failed: {e}")

        # Generate report
        try:
            print("Generating report...")
            report = zap.core.htmlreport()
            with open("zap_scan_report.html", "w") as f:
                f.write(report)
            print("Report saved.")
        except Exception as e:
            print(f"Report generation failed: {e}")

    except Exception as e:
        print(f"Global error: {e}")
    finally:
        # Stop ZAP process
        if 'zap_process' in locals():
            zap_process.terminate()
            print("ZAP process terminated.")

# Example usage
run_zap_scan('172.17.0.2', 8081)
