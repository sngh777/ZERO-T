import docker

def find_web_containers():
    client = docker.from_env()
    web_ports = {80, 443}  # Common web server ports
    web_containers = []

    for container in client.containers.list(all=True):
        ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
        ip_address = container.attrs.get('NetworkSettings', {}).get('IPAddress', 'N/A')

        for port_str, port_data in ports.items():
            port = int(port_str.split("/")[0])
            if port in web_ports and port_data:
                host_port = port_data[0].get('HostPort', 'N/A')
                container_info = {
                    'name': container.name,  # Container name
                    'image': container.image.id if not container.image.tags else container.image.tags[0], #If you want to scan untagged images, you can use the container's image ID as a fallback:
                    'ip': ip_address,
                    'container_port': port,
                    'host_port': host_port
                }
                web_containers.append(container_info)
                # Print the container details
                print(f"Found web container: {container_info}")

    return web_containers
