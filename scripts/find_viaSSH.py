import paramiko
import docker
import json

# Hardcoded remote EC2 IP address and SSH login details
REMOTE_HOST = '34.207.159.185'  # Replace with your EC2 public IP
SSH_USER = 'ec2-user'  # Replace with your EC2 username (typically 'ec2-user' for Amazon Linux)
SSH_KEY_PATH = '/home/user/Downloads/zta.pem'  # Path to your private SSH key

def find_web_containers_via_ssh():
    # Create an SSH client instance
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the EC2 instance via SSH using the private key
        ssh_client.connect(REMOTE_HOST, username=SSH_USER, key_filename=SSH_KEY_PATH)

        # Run the command to get the list of Docker containers (including stopped ones)
        stdin, stdout, stderr = ssh_client.exec_command("docker ps -a --format '{{json .}}'")

        containers_data = stdout.read().decode()
        containers_list = containers_data.splitlines()

        web_ports = {80, 443}  # Common web server ports
        web_containers = []

        # Process each container's data
        for container_data in containers_list:
            container_info = json.loads(container_data)
            container_ports = container_info.get('Ports', '')
            container_ip = container_info.get('NetworkSettings', {}).get('IPAddress', 'N/A')

            # Check if the container is exposing web server ports
            for port_str in container_ports.split(','):
                port = int(port_str.split('/')[0]) if '/' in port_str else None
                if port in web_ports:
                    host_port = port_str.split('->')[1].split('/')[0] if '->' in port_str else 'N/A'
                    container_info = {
                        'name': container_info['Names'],  # Container name
                        'image': container_info['Image'],  # Image name or ID
                        'ip': container_ip,
                        'container_port': port,
                        'host_port': host_port
                    }
                    web_containers.append(container_info)
                    # Print the container details
                    print(f"Found web container: {container_info}")

    except Exception as e:
        print(f"Error occurred while connecting via SSH: {e}")
    
    finally:
        # Close the SSH connection
        ssh_client.close()

    return web_containers
