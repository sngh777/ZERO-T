import time
import requests

# ZAP API configuration
ZAP_PROXY = "http://localhost:8679"  # ZAP API endpoint (mapped to host port 8679)
TARGET_URL = "http://nginx-zap:80"   # Nginx container URL

def run_zap_scan():
    try:
        print("Starting ZAP scan...")

        # Start active scan
        print(f"Starting scan for {TARGET_URL}")
        scan_response = requests.get(
            f"{ZAP_PROXY}/JSON/ascan/action/scan/",
            params={
                "url": TARGET_URL,
                "recurse": True,
                "inScopeOnly": True,
                "scanPolicyName": "Default Policy"
            }
        )
        scan_id = scan_response.json().get("scan")

        # Monitor scan progress
        while True:
            status_response = requests.get(
                f"{ZAP_PROXY}/JSON/ascan/view/status/",
                params={"scanId": scan_id}
            )
            status = status_response.json().get("status")
            print(f"Scan progress: {status}%")
            if status == "100":
                break
            time.sleep(5)

        # Generate HTML report
        print("Generating report...")
        report_response = requests.get(f"{ZAP_PROXY}/OTHER/core/other/htmlreport/")
        report_filename = "zap_report_nginx.html"
        with open(report_filename, "wb") as f:
            f.write(report_response.content)
        
        print(f"Scan complete! Report saved to {report_filename}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_zap_scan()
