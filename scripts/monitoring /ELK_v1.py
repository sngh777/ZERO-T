import docker
import subprocess
import os
import time

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

def start_docker_containers():
    try:
        # Start Elasticsearch container
        print("Starting Elasticsearch container...")
        client.containers.run(
            'docker.elastic.co/elasticsearch/elasticsearch:8.17.1',
            name='elasticsearch_container',
            environment={"discovery.type": "single-node"},
            ports={'9200/tcp': 9200},
            detach=True
        )

        # Wait until Elasticsearch is ready
        wait_for_elasticsearch()

        # Start Kibana container
        print("Starting Kibana container...")
        client.containers.run(
            'docker.elastic.co/kibana/kibana:8.17.1',
            name='kibana',
            environment={"ELASTICSEARCH_URL": "http://elasticsearch:9200"},
            ports={'5601/tcp': 5601},
            detach=True
        )

        # Start other containers
        print("Starting Logstash container...")
        client.containers.run(
            'docker.elastic.co/logstash/logstash:8.17.1',
            name='logstash',
            volumes={'./logstash/config': {'bind': '/usr/share/logstash/pipeline', 'mode': 'rw'}},
            ports={'5044/tcp': 5044},
            detach=True
        )

        print("Starting Filebeat container...")
        client.containers.run(
            'docker.elastic.co/beats/filebeat:8.17.1',
            name='filebeat',
            volumes={'/var/lib/docker/containers': {'bind': '/var/lib/docker/containers', 'mode': 'ro'},
                     './filebeat.yml': {'bind': '/etc/filebeat/filebeat.yml', 'mode': 'ro'}},
            detach=True
        )

        print("Starting Metricbeat container...")
        client.containers.run(
            'docker.elastic.co/beats/metricbeat:8.17.1',
            name='metricbeat',
            volumes={'/var/run/docker.sock': {'bind': '/var/run/docker.sock', 'mode': 'ro'},
                     './metricbeat.yml': {'bind': '/etc/metricbeat/metricbeat.yml', 'mode': 'ro'}},
            detach=True
        )

        print("Elastic Stack containers started successfully!")

    except Exception as e:
        print(f"Error starting containers: {e}")

# Run Docker Compose to start the stack if you prefer to use Compose
def start_docker_compose():
    try:
        print("Starting Elastic Stack with Docker Compose...")
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        print("Elastic Stack started with Docker Compose.")
    except subprocess.CalledProcessError as e:
        print(f"Error running docker-compose: {e}")

# Main function to automate the process
def main():
    # Step 1: Pull Docker images for Elastic Stack
    pull_images()

    # Step 2: Generate Filebeat and Metricbeat config files
    generate_filebeat_config()
    generate_metricbeat_config()

    # Step 3: Start containers
    start_docker_containers()

    # Optionally, you can use Docker Compose for starting all containers at once
    # start_docker_compose()

if __name__ == '__main__':
    main()
