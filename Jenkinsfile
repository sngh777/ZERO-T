pipeline {
    agent any

    environment {
        IMAGE_NAME = 'nginx-server:latest'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url:'https://github.com/sngh777/ZERO-T.git'
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    sh 'docker build -t nginx-server .'
                }
            }
        }

        stage('Run Vulnerability Scans') {
            steps {
                script {
                    sh 'python3 scripts/vulnerability_scan.py'
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Running Docker container locally'
                sh 'docker run -d -p 8080:80 nginx-server'

            }
        }
    }
    post {
        failure {
            echo 'The build failed due to vulnerabilities found in the Docker image.'
        }
    }
}

