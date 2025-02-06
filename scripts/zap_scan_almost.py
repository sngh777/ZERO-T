import subprocess
import sys
import os

def run_zap_scan(host_ip,host_port):
    """Run ZAP scan with proper error handling and permissions"""
    print("Pulling the zaproxy/zap-stable image...")
    try:
        subprocess.run(["docker", "pull", "zaproxy/zap-stable"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error pulling ZAP image: {e}")
        sys.exit(1)

    current_dir = os.getcwd()
    zap_command = [
        "docker", "run", "--network", "host",
        "-v", f"{current_dir}:/zap/wrk/:rw",
        "--user", "root",
        "zaproxy/zap-stable",
        "zap-baseline.py",
        "-t", f"http://{host_ip}:{host_port}",
        "-r", "report.html"  # Explicit output file
    ]

    try:
        print(f"Running ZAP scan on http://{host_ip}:{host_port}...")
        result = subprocess.run(
            zap_command,
            capture_output=True,
            text=True,
            check=False  # Don't throw error on non-zero exit codes
        )
        
        # Always show scan output
        print(f"Scan Output:\n{result.stdout}")
        if result.stderr:
            print(f"Scan Errors:\n{result.stderr}")

        # Handle ZAP's exit codes
        if result.returncode == 0:
            print("Scan completed: No issues found")
        elif result.returncode == 1:
            print("Scan completed: Warnings found")
        elif result.returncode == 2:
            print("Scan completed: FAILURES found")
        else:
            print(f"Unexpected exit code: {result.returncode}")

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)

