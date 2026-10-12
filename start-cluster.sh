#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting RxVerify cluster..."
minikube start --driver=docker --cpus=4 --memory=8192
eval $(minikube docker-env)
docker build -t rxverify:minikube .
minikube image load rxverify:minikube
kubectl apply -k k8s/
echo "⏳ Waiting for pods to be Ready..."
kubectl wait --for=condition=Ready pods --all -n rxverify -n monitoring --timeout=180s
echo "✅ Cluster ready!"
kubectl get pods -n rxverify -n monitoring