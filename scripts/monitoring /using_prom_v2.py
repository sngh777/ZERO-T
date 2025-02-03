import os
import docker
import time
import requests

# Define container names and settings
prometheus_container_name = 'prometheus'
grafana_container_name = 'grafana'

# Get the current working directory to save the prometheus.yml
prometheus_config_path = os.path.join(os.getcwd(), 'prometheus.yml')

# Prometheus config template to scrape all running Docker containers
prometheus_config = """
global:
  scrape_interval: 15s  # Default scrape interval

scrape_configs:
  - job_name: 'docker-containers'
    docker_sd_configs:
      - host: "unix:///var/run/docker.sock"  # Docker socket for service discovery
    relabel_configs:
      - source_labels: [__meta_docker_container_name]
        target_label: container
      - source_labels: [__meta_docker_container_id]
        target_label: container_id
"""

# Initialize Docker client
client = docker.from_env()

# Step 1: Create the Prometheus container
def create_prometheus():
    # Write the Prometheus config file in the current working directory
    with open(prometheus_config_path, 'w') as f:
        f.write(prometheus_config)

    # Run Prometheus container with a specific network
    print("Starting Prometheus container...")
    client.containers.run(
        "prom/prometheus",
        name=prometheus_container_name,
        ports={'9090/tcp': 9090},
        volumes={
            prometheus_config_path: {'bind': '/etc/prometheus/prometheus.yml', 'mode': 'ro'},
            '/var/run/docker.sock': {'bind': '/var/run/docker.sock', 'mode': 'ro'}
        },
        detach=True,
        network="monitoring_network"
    )
    print("Prometheus container started.")

# Step 2: Create the Grafana container
def create_grafana():
    print("Starting Grafana container...")
    client.containers.run(
        "grafana/grafana",
        name=grafana_container_name,
        ports={'3000/tcp': 3000},
        environment={"GF_SECURITY_ADMIN_PASSWORD": "admin"},
        detach=True,
        network="monitoring_network"  # Use the same network as Prometheus
    )
    print("Grafana container started.")

# Step 3: Check if Prometheus is up
def check_prometheus():
    print("Waiting for Prometheus to be ready...")
    for _ in range(30):  # Retry up to 30 times (5 minutes max)
        try:
            response = requests.get("http://localhost:9090/api/v1/query?query=1+1")
            if response.status_code == 200:
                print("Prometheus is up and ready.")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(10)  # Wait 10 seconds before trying again
    print("Prometheus is not responding.")
    return False

# Step 4: Configure Grafana Data Source
def configure_grafana():
    # Ensure Prometheus is up before configuring Grafana
    if not check_prometheus():
        print("Prometheus is not ready. Exiting.")
        return

    # Wait for Grafana to start up
    print("Waiting for Grafana to initialize...")
    time.sleep(15)  # Wait for the Grafana container to initialize

    # Access Grafana API to configure data source (assuming default login)
    grafana_api_url = 'http://localhost:3000/api/datasources'
    payload = {
        "name": "Prometheus",
        "type": "prometheus",
        "url": "http://prometheus:9090",  # Use the container name as the URL
        "access": "proxy",
        "isDefault": True
    }

    # Basic Authentication header for Grafana (admin/admin)
    headers = {
        'Authorization': 'Basic YWRtaW46YWRtaW4='  # Basic auth for admin/admin
    }

    # Send POST request to configure Grafana data source
    response = requests.post(grafana_api_url, json=payload, headers=headers)

    if response.status_code == 200:
        print("Grafana data source configured successfully.")
    else:
        print(f"Failed to configure Grafana: {response.text}")

# Step 5: Set up Prometheus and Grafana
def setup_monitoring():
    # Create a custom network for Prometheus and Grafana to communicate
    client.networks.create("monitoring_network", driver="bridge")

    create_prometheus()
    create_grafana()
    configure_grafana()
    print("Prometheus and Grafana setup completed!")

if __name__ == '__main__':
    setup_monitoring()
