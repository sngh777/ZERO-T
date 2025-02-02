import os
import docker
client = docker.from_env()

def run_dependency_check():
    """
    Run OWASP Dependency-Check to scan the $(HOME)/ZERO-T directory for vulnerabilities in dependencies.
    """
    # Get the home directory and set the scan directory to $(HOME)/ZERO-T
    home_dir = os.path.expanduser("~")
    scan_dir = os.path.join(home_dir, "ZERO-T")

    print(f"Running OWASP Dependency-Check on directory: {scan_dir}...")

    try:
        # Pull the OWASP Dependency-Check image
        print("Pulling OWASP Dependency-Check image...")
        client.images.pull("owasp/dependency-check")

        # Define the output directory for Dependency-Check reports
        output_dir = os.path.join(os.getcwd(), "dependency_check_reports")
        os.makedirs(output_dir, exist_ok=True)  # Create the directory if it doesn't exist
        user = os.environ.get("USER")
        # Run OWASP Dependency-Check scan
        print("Starting OWASP Dependency-Check scan...")
        container = client.containers.run(
            image="owasp/dependency-check",
            environment={"user": user},
            command=f"--project my_project --scan {scan_dir} --out {output_dir}",  # Scan the directory and save reports
            remove=True,  # Remove the container after execution
            volumes={
                scan_dir: {"bind": scan_dir, "mode": "ro"},  # Mount the directory to scan
                output_dir: {"bind": output_dir, "mode": "rw"}  # Mount the output directory
            },
            detach=False  # Run in the foreground
        )
        print(container.decode('utf-8'))  # Print Dependency-Check logs
        print(f"Dependency-Check scan completed. Reports saved in '{output_dir}'.")
    except Exception as e:
        print(f"Error running OWASP Dependency-Check: {e}")
