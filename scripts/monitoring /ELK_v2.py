import docker
import subprocess
import os
import time
import random
import uuid

# Initialize Docker client
client = docker.from_env(timeout=120)  # 120 seconds timeout


# List of Docker images to pull
images = [
    'docker.elastic.co/elasticsearch/elasticsearch:8.17.1',
    'docker.elastic.co/kibana/kibana:8.17.1',
    'docker.elastic.co/logstash/logstash:8.17.1',
    'docker.elastic.co/beats/filebeat:8.17.1',
    'docker.elastic.co/beats/metricbeat:8.17.1'
]

# Pull images from Docker Hub
def pull_images():
    for image in images:
        print(f"Pulling image: {image}")
        client.images.pull(image)
        print(f"Successfully pulled {image}")

# Generate filebeat.yml for log collection
def generate_filebeat_config():
    filebeat_config = """
    filebeat.inputs:
      - type: docker
        containers.ids: '*'  # Automatically collect logs from all running containers

    output.elasticsearch:
      hosts: ["http://elasticsearch:9200"]
    """
    with open('filebeat.yml', 'w') as f:
        f.write(filebeat_config)
    print("Generated filebeat.yml")

# Generate metricbeat.yml for container metrics
def generate_metricbeat_config():
    metricbeat_config = """
    metricbeat.modules:
      - module: docker
        metricsets: ["container", "cpu", "memory"]
        hosts: ["unix:///var/run/docker.sock"]  # Automatically detect all running containers

    output.elasticsearch:
      hosts: ["http://elasticsearch:9200"]
    """
    with open('metricbeat.yml', 'w') as f:
        f.write(metricbeat_config)
    print("Generated metricbeat.yml")

def wait_for_elasticsearch():
    print("Waiting for Elasticsearch to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            response = client.containers.get('elasticsearch').exec_run('curl -X GET http://localhost:9200')
            if b'cluster_name' in response.output:
                print("Elasticsearch is ready.")
                return
        except Exception:
            pass
        time.sleep(2)
    print("Elasticsearch did not become ready in time.")

def get_random_port(start_port=9001, end_port=9999):
    """Returns a random available host port in the specified range."""
    while True:
        port = random.randint(start_port, end_port)
        try:
            # Try to bind to the port using a temporary container to see if it's available
            container = client.containers.run(
                'busybox',
                name=f"check_port_{port}",
                detach=True,
                ports={f"80/tcp": port}
            )
            container.remove()  # Remove temporary container after port is checked
            return port
        except docker.errors.APIError:
            # Port is already in use, retry
            continue

def generate_unique_container_name(base_name):
    """Generate a unique container name by appending a random UUID."""
    return f"{base_name}_{uuid.uuid4().hex[:6]}"

def start_docker_containers():
    try:
        # Start Elasticsearch container
        elasticsearch_host_port = get_random_port()
        elasticsearch_container_name = generate_unique_container_name("elasticsearch_container")
        print(f"Starting Elasticsearch container {elasticsearch_container_name} on host port {elasticsearch_host_port}...")
        elasticsearch_container = client.containers.run(
            'docker.elastic.co/elasticsearch/elasticsearch:8.17.1',
            name=elasticsearch_container_name,
            environment={"discovery.type": "single-node"},
            ports={f'9200/tcp': elasticsearch_host_port},
            detach=True
        )

        # Wait until Elasticsearch is ready
        wait_for_elasticsearch()

        # Start Kibana container
        kibana_host_port = get_random_port()
        kibana_container_name = generate_unique_container_name("kibana")
        print(f"Starting Kibana container {kibana_container_name} on host port {kibana_host_port}...")
        kibana_container = client.containers.run(
            'docker.elastic.co/kibana/kibana:8.17.1',
            name=kibana_container_name,
            environment={"ELASTICSEARCH_URL": f"http://elasticsearch:{elasticsearch_host_port}"},
            ports={f'5601/tcp': kibana_host_port},
            detach=True
        )

        # Start Logstash container
        logstash_host_port = get_random_port()
        logstash_container_name = generate_unique_container_name("logstash")
        print(f"Starting Logstash container {logstash_container_name} on host port {logstash_host_port}...")
        logstash_container = client.containers.run(
            'docker.elastic.co/logstash/logstash:8.17.1',
            name=logstash_container_name,
            volumes={'./logstash/config': {'bind': '/usr/share/logstash/pipeline', 'mode': 'rw'}},
            ports={f'5044/tcp': logstash_host_port},
            detach=True
        )

        # Start Filebeat container
        filebeat_container_name = generate_unique_container_name("filebeat")
        print(f"Starting Filebeat container {filebeat_container_name}...")
        filebeat_container = client.containers.run(
            'docker.elastic.co/beats/filebeat:8.17.1',
            name=filebeat_container_name,
            volumes={'/var/lib/docker/containers': {'bind': '/var/lib/docker/containers', 'mode': 'ro'},
                     './filebeat.yml': {'bind': '/etc/filebeat/filebeat.yml', 'mode': 'ro'}},
            detach=True
        )

        # Start Metricbeat container
        metricbeat_container_name = generate_unique_container_name("metricbeat")
        print(f"Starting Metricbeat container {metricbeat_container_name}...")
        metricbeat_container = client.containers.run(
            'docker.elastic.co/beats/metricbeat:8.17.1',
            name=metricbeat_container_name,
            volumes={'/var/run/docker.sock': {'bind': '/var/run/docker.sock', 'mode': 'ro'},
                     './metricbeat.yml': {'bind': '/etc/metricbeat/metricbeat.yml', 'mode': 'ro'}},
            detach=True
        )

        print("Elastic Stack containers started successfully!")

        # Print the assigned host ports
        print("Access Elasticsearch at http://localhost:{0}".format(elasticsearch_host_port))
        print("Access Kibana at http://localhost:{0}".format(kibana_host_port))
        print("Logstash exposed at port {0}".format(logstash_host_port))

    except Exception as e:
        print(f"Error starting containers: {e}")

# Main function to automate the process
def main():
    # Step 1: Pull Docker images for Elastic Stack
    pull_images()

    # Step 2: Generate Filebeat and Metricbeat config files
    generate_filebeat_config()
    generate_metricbeat_config()

    # Step 3: Start containers
    start_docker_containers()

if __name__ == '__main__':
    main()
