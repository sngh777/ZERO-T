pipeline {
    agent any

    environment {
        IMAGE_NAME = 'nginx-server:latest'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/sngh777/ZERO-T.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                script {
                    // Run the dependency installation script
                    sh 'python3 scripts/install_dependencies.py'
                }
            }
        }

        stage('Run Container and Find Web Containers') {
            steps {
                script {
                    // Run the build_and_run_container.py script to start the container
                    sh 'python3 build_run_cont.py'
                    
                    // Run the findContainers.py script to list web containers
                    sh 'python3 scripts/findContainers.py'
                }
            }
        }

        stage('Run Vulnerability Scans') {
            steps {
                script {
                    // Run the vulnerability_scan.py script
                    sh 'python3 scripts/vulnerability_scan.py'
                }
            }
        }
    }

    post {
        failure {
            echo 'The build failed due to vulnerabilities found in the Docker image or other errors.'
        }
        success {
            echo 'Build and scans completed successfully!'
        }
    }
}
