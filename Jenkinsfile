pipeline {
    agent {
        docker {
            image 'python:3.12-slim'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }
    environment {
        REGISTRY = 'ghcr.io'
        IMAGE_NAME = "${env.GITHUB_REPOSITORY:-yashmahajan11234567/digital-prescription-verification-devops}"
    }
    stages {
        stage('Setup') {
            steps {
                sh 'pip install --upgrade pip'
                sh 'pip install -r requirements.txt'
                sh 'pip install -r requirements-dev.txt'
                sh 'pip install ruff'
            }
        }
        stage('Lint') {
            steps {
                sh 'ruff check app.py tests/'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest -q'
            }
        }
        stage('Security Scan') {
            steps {
                sh 'pip install pip-audit'
                sh 'pip-audit -r requirements.txt'
            }
        }
        stage('Build Docker Image') {
            when {
                branch 'main'
            }
            steps {
                script {
                    docker.withRegistry("https://${REGISTRY}", 'ghcr-credentials') {
                        def image = docker.build("${IMAGE_NAME}:${env.BUILD_NUMBER}")
                        image.push()
                        image.push('latest')
                    }
                }
            }
        }
        stage('Deploy to Minikube') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    kubectl set image deployment/rxverify rxverify=${REGISTRY}/${IMAGE_NAME}:latest -n rxverify
                    kubectl rollout status deployment/rxverify -n rxverify --timeout=120s
                '''
            }
        }
    }
    post {
        always {
            cleanWs()
        }
    }
}