# python-app-flask
# Flask App Deployment on Minikube with Helm

A complete guide to building, containerizing, and deploying a Flask application to a local Kubernetes cluster using Docker and Helm.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Prerequisites](#prerequisites)
3. [Flask Application](#flask-application)
4. [Docker Setup](#docker-setup)
5. [Helm Chart](#helm-chart)
6. [Deploying to Minikube](#deploying-to-minikube)
7. [Accessing the App](#accessing-the-app)
8. [Useful Commands](#useful-commands)
9. [Troubleshooting](#troubleshooting)
10. [Lessons Learned](#lessons-learned)

---

## Project Structure

```
python-cicd/
├── src/
│   └── pythonflask.py
├── charts/
│   └── python-app/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           └── ingress.yaml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Docker Desktop
- Minikube
- Helm
- kubectl
- Python 3.10+

---

## Flask Application

**`src/pythonflask.py`**

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/v1/details', methods=['GET'])
def get_details():
    return jsonify({"message": "Hello World"})

@app.route('/api/v1/health', methods=['GET'])
def get_health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

> ⚠️ **Important:** Always bind to `0.0.0.0` not `127.0.0.1` — otherwise the app is unreachable from outside the container.

**`requirements.txt`**

```
flask
```

---

## Docker Setup

**`Dockerfile`**

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src .

EXPOSE 5000

CMD ["python", "pythonflask.py"]
```

**Build and push to Docker Hub:**

```bash
docker build -t myintwl/python-app:v1 .
docker push myintwl/python-app:v1
```

**Verify image locally:**

```bash
docker run -p 5000:5000 myintwl/python-app:v1
curl http://localhost:5000/api/v1/health
```

---

## Helm Chart

### `values.yaml`

```yaml
image:
  repository: myintwl/python-app
  tag: "v1"
  pullPolicy: Never

service:
  type: ClusterIP
  port: 5000

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: python-app.local
      paths:
        - path: /api/v1/health
          pathType: Prefix
        - path: /api/v1/details
          pathType: Prefix

livenessProbe:
  httpGet:
    path: /api/v1/health
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /api/v1/health
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 10
```

> ⚠️ **Important:** Liveness and readiness probes must point to a valid endpoint. Using `/` when your app has no root route causes `CrashLoopBackOff`.

### `templates/service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}
  namespace: {{ .Release.Namespace }}
spec:
  type: ClusterIP
  selector:
    app: {{ .Release.Name }}
  ports:
    - port: 5000
      targetPort: 5000
```

### `templates/ingress.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .Release.Name }}-ingress
  namespace: {{ .Release.Namespace }}
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - host: python-app.local
      http:
        paths:
          - path: /api/v1/health
            pathType: Prefix
            backend:
              service:
                name: {{ .Release.Name }}
                port:
                  number: 5000
          - path: /api/v1/details
            pathType: Prefix
            backend:
              service:
                name: {{ .Release.Name }}
                port:
                  number: 5000
```

---

## Deploying to Minikube

### Step 1 — Start Minikube and enable Ingress

```bash
minikube start
minikube addons enable ingress
```

### Step 2 — Load Docker image into Minikube

```bash
minikube image load myintwl/python-app:v1

# Verify
minikube image ls | grep python-app
```

### Step 3 — Create namespace and install Helm chart

```bash
kubectl create namespace python-app
helm install python-app -n python-app .
```

### Step 4 — Verify deployment

```bash
kubectl get pods -n python-app
kubectl get svc -n python-app
kubectl get ingress -n python-app
```

Expected output:

```
NAME                        READY   STATUS    RESTARTS   AGE
python-app-xxxxxxxx-xxxxx   1/1     Running   0          30s
```

### Step 5 — Upgrade Helm release (after changes)

```bash
helm upgrade python-app -n python-app .
```

---

## Accessing the App

### Mac with Docker driver (Recommended)

Minikube running on Docker driver means `192.168.49.2` is not directly reachable from macOS. Use port-forward:

```bash
# Terminal 1 - keep running
kubectl port-forward svc/python-app 8080:5000 -n python-app

# Terminal 2 - test
curl http://localhost:8080/api/v1/health
curl http://localhost:8080/api/v1/details
```

### Using Minikube Tunnel (alternative)

```bash
# Add to /etc/hosts
echo "127.0.0.1 python-app.local" | sudo tee -a /etc/hosts

# Terminal 1 - keep running
sudo minikube tunnel

# Terminal 2 - test
curl http://python-app.local/api/v1/health
curl http://python-app.local/api/v1/details
```

---

## Useful Commands

```bash
# Check pod status
kubectl get pods -n python-app

# Watch pods in real time
kubectl get pods -n python-app -w

# View pod logs
kubectl logs -f -l app=python-app -n python-app

# Describe pod for events and errors
kubectl describe pod -n python-app

# List all Helm releases
helm list -A

# Uninstall Helm release
helm uninstall python-app -n python-app

# Delete namespace
kubectl delete namespace python-app

# Stop Minikube
minikube stop
```

---

## Troubleshooting

### CrashLoopBackOff

**Symptom:**
```
NAME                          READY   STATUS             RESTARTS
python-app-xxxxxxxx-xxxxx     0/1     CrashLoopBackOff   6
```

**Cause:** Liveness/readiness probe hitting `/` which returns 404.

**Fix:** Update `values.yaml` probes to use a valid endpoint:
```yaml
livenessProbe:
  httpGet:
    path: /api/v1/health
    port: 5000
readinessProbe:
  httpGet:
    path: /api/v1/health
    port: 5000
```

To temporarily disable probes for debugging:
```bash
helm upgrade python-app -n python-app . \
  --set livenessProbe=null \
  --set readinessProbe=null
```

---

### ImagePullBackOff

**Symptom:**
```
NAME                        READY   STATUS             RESTARTS
python-app-xxxxxxxx-xxxxx   0/1     ImagePullBackOff   0
```

**Fix:** Load image directly into Minikube:
```bash
minikube image load myintwl/python-app:v1
```

Then set `pullPolicy: Never` in `values.yaml`:
```yaml
image:
  pullPolicy: Never
```

---

### Could Not Connect to Server

**Symptom:**
```
curl: (7) Failed to connect to python-app.local port 80
```

**Cause:** Minikube Docker driver on Mac — cluster IP not routable from host.

**Fix:** Use port-forward:
```bash
kubectl port-forward svc/python-app 8080:5000 -n python-app
curl http://localhost:8080/api/v1/health
```

---

### Release Already Exists

**Symptom:**
```
Error: INSTALLATION FAILED: release name check failed: cannot reuse a name that is still in use
```

**Fix:**
```bash
helm uninstall python-app -n python-app
helm install python-app -n python-app .
```

Or use upgrade --install which handles both:
```bash
helm upgrade --install python-app -n python-app .
```

---

### Path Already Defined in Ingress

**Symptom:**
```
admission webhook denied the request: host "python-app.local" and path "/api/v1/health"
is already defined in ingress default/python-app-ingress
```

**Cause:** A duplicate ingress exists in the `default` namespace from manual setup.

**Fix:**
```bash
kubectl delete ingress python-app-ingress -n default
helm upgrade python-app -n python-app .
```

---

### Minikube Tunnel Already Running

**Symptom:**
```
TUNNEL_ALREADY_RUNNING: Another tunnel process is already running
```

**Fix:**
```bash
pkill -f "minikube tunnel"
sudo minikube tunnel
```

---

## Lessons Learned

| Issue | Cause | Fix |
|-------|-------|-----|
| `CrashLoopBackOff` | Liveness probe hitting `/` → 404 | Set probe path to `/api/v1/health` |
| `ImagePullBackOff` | Minikube couldn't reach Docker Hub | `minikube image load` + `pullPolicy: Never` |
| `Could not connect` | Mac Docker driver blocks `192.168.49.2` | Use `kubectl port-forward` |
| `Release already exists` | Old Helm release stuck | `helm uninstall` then reinstall |
| `Path already defined` | Duplicate ingress in `default` namespace | `kubectl delete ingress -n default` |
| `Tunnel already running` | Old tunnel process not terminated | `pkill -f "minikube tunnel"` |
| Flask unreachable in container | Bound to `127.0.0.1` instead of `0.0.0.0` | Set `host='0.0.0.0'` in `app.run()` |
