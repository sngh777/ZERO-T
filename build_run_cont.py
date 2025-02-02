import docker
import socket

def find_free_port(start_port=8080):
    """Function to find a free port starting from a given port."""
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('127.0.0.1', port))  # Check if the port is open
            if result != 0:  # If the port is not in use, it will return a non-zero result
                return port
            port += 1

def build_and_run_container():
    client = docker.from_env()

    # Step 1: Build the Docker image
    print("Building Docker image 'nginx-server'...")
    client.images.build(path=".", tag="nginx-server")

    # Step 2: Find a free port starting from 8080
    free_port = find_free_port(8080)
    print(f"Free port found: {free_port}")

    # Step 3: Run the container with the free port
    print(f"Running container on port {free_port}...")
    container = client.containers.run(
        "nginx-server", 
        detach=True, 
        ports={f"80/tcp": free_port}
    )

    # Check the container's exposed ports
    print(f"Container ports: {container.ports}")

    # Access the host port dynamically
    if '80/tcp' in container.ports:
        host_port = container.ports['80/tcp'][0]['HostPort']
        print(f"Container '{container.name}' is running and can be accessed at http://localhost:{host_port}")
    else:
        print(f"Port 80 is not exposed for container '{container.name}'")

    return container

if __name__ == "__main__":
    container = build_and_run_container()
