import time
import subprocess

def run_zap_scan(target_ip: str, target_port: int):
    # Ensure the required package is installed
    try:
        from zapv2 import ZAPv2
    except ImportError:
        print("Installing OWASP ZAP Python API...")
        subprocess.check_call(['pip', 'install', 'python-owasp-zap-v2.4'])
        from zapv2 import ZAPv2

    ZAP_BASE_URL = 'http://localhost:8080'
    target_url = f'http://{target_ip}:{target_port}'

    # Initialize ZAP API without an API key
    zap = ZAPv2(proxies={'http': ZAP_BASE_URL, 'https': ZAP_BASE_URL})

    try:
        print(f"Accessing target: {target_url}")
        zap.urlopen(target_url)
        time.sleep(2)  # Allow time for the site to load

        # Start Spider Scan
        print("Starting Spider scan...")
        spider_scan_id = zap.spider.scan(target_url)

        # Wait for the Spider scan to complete
        while int(zap.spider.status(spider_scan_id)) < 100:
            print(f"Spider progress: {zap.spider.status(spider_scan_id)}%")
            time.sleep(2)

        print("Spider scan completed.")

        # Start Active Scan
        print("Starting Active scan...")
        active_scan_id = zap.ascan.scan(target_url)

        # Wait for the Active scan to complete
        while int(zap.ascan.status(active_scan_id)) < 100:
            print(f"Active scan progress: {zap.ascan.status(active_scan_id)}%")
            time.sleep(5)

        print("Active scan completed.")

        # Generate Report
        print("Generating scan report...")
        report = zap.core.htmlreport()
        with open("zap_scan_report.html", "w") as report_file:
            report_file.write(report)
        print("Scan report saved as zap_scan_report.html")

    except Exception as e:
        print(f"An error occurred: {e}")


