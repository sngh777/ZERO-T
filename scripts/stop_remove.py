import docker

# Initialize Docker client
client = docker.from_env()

def stop_and_remove_containers():
    try:
        # List all running containers
        containers = client.containers.list()

        if not containers:
            print("No running containers found.")
            return

        print(f"Stopping and removing {len(containers)} containers...")

        for container in containers:
            print(f"Stopping container: {container.name} ({container.id})")
            container.stop()  # Stop the container
            print(f"Removing container: {container.name} ({container.id})")
            container.remove()  # Remove the container
        print("All running containers have been stopped and removed.")

    except docker.errors.APIError as e:
        print(f"Error interacting with Docker API: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def prune_docker_resources():
    try:
        # Prune unused Docker networks
        print("Pruning unused networks...")
        client.networks.prune()

        # Prune unused Docker volumes
        print("Pruning unused volumes...")
        client.volumes.prune()

        print("Unused networks and volumes have been pruned.")

    except docker.errors.APIError as e:
        print(f"Error pruning Docker resources: {e}")
    except Exception as e:
        print(f"An error occurred while pruning: {e}")

# Main function to stop and remove containers, then prune networks and volumes
def main():
    # Step 1: Stop and remove all running containers
    stop_and_remove_containers()

    # Step 2: Prune unused networks and volumes
    prune_docker_resources()

if __name__ == "__main__":
    main()
