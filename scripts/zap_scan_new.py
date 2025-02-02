import subprocess
import sys
import os
import shlex

def run_zap_scan(host_port):
    """Pull the zaproxy/zap-stable image and run the ZAP scan on the specified host port."""
    # Pull the zaproxy/zap-stable image
    print("Pulling the zaproxy/zap-stable image...")
    try:
        subprocess.run(["docker", "pull", "zaproxy/zap-stable"], check=True)
        print("Image pulled successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error pulling ZAP image: {e}")
        sys.exit(1)

    # Get current working directory
    current_directory = os.getcwd()

    zap_command_str = f"docker run --network host -v {current_directory}:/zap/wrk/:rw zaproxy/zap-stable zap-baseline.py -t http://localhost:{host_port}"

    # Split the command string using shlex.split()
    zap_command = shlex.split(zap_command_str)

    # Run the ZAP scan using the specified host port
    '''
    zap_command = [
        "docker", "run", "--network", "host", 
        "-v", f"{current_directory}:/zap/wrk/:rw",  # Replace $(pwd) with current_directory
        "zaproxy/zap-stable", 
        "zap-baseline.py", 
        "-t", f"http://localhost:{host_port}"
    ]
'''
    try:
       print(f"Running ZAP scan on http://localhost:{host_port}...")
       result = subprocess.run(zap_command, check=True, capture_output=True, text=True)
       print("ZAP scan completed successfully.")
       print(f"ZAP Scan Output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
       print(f"Error running ZAP scan on port {host_port}: {e}")
       print(f"ZAP Scan Error Output:\n{e.stderr}")


