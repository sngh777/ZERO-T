import subprocess
import sys
import os
import getpass

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
        subprocess.run(["docker", "images", "owasp/zap2docker-stable"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("OWASP ZAP Docker image is already available.")
    except subprocess.CalledProcessError:
        print("OWASP ZAP Docker image is not available. Pulling the image...")
        try:
            subprocess.run(["docker", "pull", "owasp/zap2docker-stable"], check=True)
            print("OWASP ZAP Docker image pulled successfully.")
        except Exception as e:
            print(f"Failed to pull OWASP ZAP Docker image: {e}")
            sys.exit(1)

def install_nmap():
    """Install Nmap if it is not already installed."""
    print("Checking if Nmap is installed...")
    try:
        subprocess.run(["nmap", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Nmap is already installed.")
    except subprocess.CalledProcessError:
        print("Nmap is not installed. Installing Nmap...")
        try:
            subprocess.run(["sudo", "apt-get", "install", "-y", "nmap"], check=True)
            print("Nmap installed successfully.")
        except Exception as e:
            print(f"Failed to install Nmap: {e}")
            sys.exit(1)

def main():
    # Install Docker
    install_docker()

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
