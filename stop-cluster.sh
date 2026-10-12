#!/usr/bin/env bash
set -euo pipefail

echo "🛑 Stopping RxVerify cluster..."
lsof -ti:5003,9091,3000,3100 | xargs kill -9 2>/dev/null || true
minikube stop
echo "✅ Cluster stopped"