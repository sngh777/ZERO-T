import subprocess
import sys
import os
import shutil
import getpass

def install_pip():
    """Ensure pip is installed for Python 3."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"])
        print("pip is already installed.")
    except subprocess.CalledProcessError:
        print("pip not found. Installing pip...")
        # Install pip using apt
        # subprocess.check_call(["sudo", "apt", "update"])  # Update package list
        subprocess.check_call(["sudo", "apt", "install", "-y", "python3-pip"])  # Install pip

def install_docker_python_module():
    try:
        import docker
    except ImportError:
        print("docker module not found. Installing docker-py...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "docker"])
    else:
        print("docker module is already installed.")

def install_docker():
    """Install Docker if it is not already installed."""
    print("Checking if Docker is installed...")
    try:
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Docker is already installed.")
    except subprocess.CalledProcessError:
        print("Docker is not installed. Installing Docker...")
        try:
            # Install Docker using the official Docker installation script
            subprocess.run(["curl", "-fsSL", "https://get.docker.com", "-o", "get-docker.sh"], check=True)
            subprocess.run(["sudo", "sh", "get-docker.sh"], check=True)
            print("Docker installed successfully.")
        except Exception as e:
            print(f"Failed to install Docker: {e}")
            sys.exit(1)
'''
def add_user_to_docker_group():
    """Add the Jenkins user to the Docker group and set permissions for the Docker socket."""
    print("Adding Jenkins user to Docker group and setting Docker socket permissions...")
    try:
         # Get the current user
        username = getpass.getuser()
        # Add the Jenkins user to the Docker group
        subprocess.run(["sudo", "usermod", "-aG", "docker", "jenkins"], check=True)
        print("Jenkins user added to Docker group.")

        # Set permissions for the Docker socket
        #subprocess.run(["sudo", "chmod", "666", "/var/run/docker.sock"], check=True)
        #print("Docker socket permissions updated to 666.")
       

        # Add the current user to the Docker group
        subprocess.run(["sudo", "usermod", "-aG", "docker", username], check=True)
        print(f"User '{username}' added to Docker group.")

        # Set ownership of the Docker socket to root:docker
        subprocess.run(["sudo", "chown", "root:docker", "/var/run/docker.sock"], check=True)
        print("Docker socket ownership updated to root:docker.")

        # Notify the user to log out and log back in for changes to take effect
        print("Please log out and log back in for the Docker group changes to take effect.")
    except Exception as e:
        print(f"Failed to configure Docker permissions: {e}")
        sys.exit(1)
'''
def install_trivy():
    """Install Trivy if it is not already installed."""
    print("Checking if Trivy is installed...")
    try:
        subprocess.run(["trivy", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Trivy is already installed.")
    except subprocess.CalledProcessError:
        print("Trivy is not installed. Installing Trivy...")
        try:
            # Install Trivy using the official installation script
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "wget", "apt-transport-https", "gnupg", "lsb-release"], check=True)
            subprocess.run(["wget", "-qO", "-", "https://aquasecurity.github.io/trivy-repo/deb/public.key", "|", "sudo", "apt-key", "add", "-"], check=True)
            subprocess.run(["echo", "deb https://aquasecurity.github.io/trivy-repo/deb", "$(lsb_release -sc)", "main", "|", "sudo", "tee", "-a", "/etc/apt/sources.list.d/trivy.list"], check=True)
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "trivy"], check=True)
            print("Trivy installed successfully.")
        except Exception as e:
            print(f"Failed to install Trivy: {e}")
            sys.exit(1)

def install_owasp_zap():
    """Ensure OWASP ZAP Docker image is available."""
    print("Checking if OWASP ZAP Docker image is available...")
    try:
        subprocess.run(["docker", "images", "zaproxy/zap-stable"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("OWASP ZAP Docker image is already available.")
    except subprocess.CalledProcessError:
        print("OWASP ZAP Docker image is not available. Pulling the image...")
        try:
            subprocess.run(["docker", "pull", "zaproxy/zap-stable"], check=True)
            print("OWASP ZAP Docker image pulled successfully.")
        except Exception as e:
            print(f"Failed to pull OWASP ZAP Docker image: {e}")
            sys.exit(1)



def install_nmap():
    if shutil.which("nmap") is None:
        print("nmap not found. Installing nmap...")
        try:
            # Check if user can install without sudo (or do some other check)
            subprocess.run(["sudo","apt-get", "install", "-y", "nmap"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error installing nmap: {e}")
    else:
        print("nmap is already installed.")


def main():
    # Install Docker
    install_docker()
    install_pip()
    install_docker_python_module()

    # Add the Jenkins user to the Docker group and set Docker socket permissions
    #add_user_to_docker_group()

    # Install Trivy
    install_trivy()

    # Install OWASP ZAP Docker image
    install_owasp_zap()

    # Install Nmap
    install_nmap()

    print("All dependencies have been installed successfully. You can now run the scripts.")

if __name__ == "__main__":
    main()
