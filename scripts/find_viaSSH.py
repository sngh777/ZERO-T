import paramiko
import json
import time

# Hardcoded EC2 instance details
REMOTE_HOST = '34.207.159.185'  
SSH_USER = 'ec2-user'  
SSH_KEY_PATH = '/home/user/Downloads/zta.pem' # Replace with your actual key path


def find_web_containers_via_ssh():
    """Find and list web containers running on a remote Docker host via SSH."""
    web_containers = []
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh_client.connect(REMOTE_HOST, username=SSH_USER, key_filename=SSH_KEY_PATH)
        command = "docker ps -a --format '{{json .}}'"
        stdin, stdout, stderr = ssh_client.exec_command(command)
        containers_data = stdout.read().decode().strip()

        if not containers_data:
            print("No containers found.")
            return []

        web_ports = {80, 443}

        for container_data in containers_data.split("\n"):
            try:
                container_info = json.loads(container_data)
                ports = container_info.get('Ports', '')
                container_name = container_info.get('Names')
                image = container_info.get('Image')

                for port_mapping in ports.split(','):
                    if '->' in port_mapping:
                        host_port = port_mapping.split(':')[1].split('->')[0]
                        container_port = port_mapping.split('->')[1].split('/')[0]
                        if int(container_port) in web_ports:
                            container_details = {
                                'name': container_name,
                                'image': image,
                                'host_port': host_port,
                                'container_port': container_port,
                                'ip': "localhost"
                            }
                            web_containers.append(container_details)
                            print(f"Found web container: {container_details}")
            except (ValueError, KeyError) as parse_err:
                print(f"Error parsing container data: {parse_err}")

    except paramiko.SSHException as ssh_err:
        print(f"Error occurred while connecting via SSH: {ssh_err}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        ssh_client.close()

    return web_containers
