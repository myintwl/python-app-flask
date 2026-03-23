# python-app-flask

A Flask application containerized with Docker and deployed to Kubernetes (Minikube) using raw manifests and Helm. Includes ArgoCD installation for GitOps-based continuous delivery.

---

## Table of Contents

1. [Repository Structure](#repository-structure)
2. [Prerequisites](#prerequisites)
3. [Flask Application](#flask-application)
4. [Docker Setup](#docker-setup)
5. [Deploy to Kubernetes with Raw Manifests](#deploy-to-kubernetes-with-raw-manifests)
6. [Deploy to Kubernetes with Helm](#deploy-to-kubernetes-with-helm)
7. [Install ArgoCD on Minikube](#install-argocd-on-minikube)
8. [Accessing the App on Mac (Docker Driver)](#accessing-the-app-on-mac-docker-driver)
9. [Useful Commands](#useful-commands)
10. [Troubleshooting](#troubleshooting)

---

## Repository Structure

```
python-app-flask/
├── src/
│   └── pythonflask.py          # Flask application
├── charts/
│   └── python-app/             # Helm chart
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           └── ingress.yaml
├── Dockerfile                  # Docker image definition
├── requirements.txt            # Python dependencies (flask==3.0.3)
├── deployment.yml              # Raw Kubernetes Deployment + Service manifest
├── ingress.yml                 # Raw Kubernetes Ingress manifest
├── argoingress.yml             # ArgoCD Ingress manifest
└── .gitignore
```

---

## Prerequisites

Make sure the following tools are installed before starting:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Minikube](https://minikube.sigs.k8s.io/docs/start/)
- [Helm](https://helm.sh/docs/intro/install/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
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

**`requirements.txt`**

```
flask==3.0.3
```

> ⚠️ Always bind Flask to `0.0.0.0` not `127.0.0.1` — otherwise the app is unreachable from outside the container.

---

## Docker Setup

**`Dockerfile`**

```dockerfile
FROM python:3.10-slim

# Install curl for health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src .

EXPOSE 5000

CMD ["python", "pythonflask.py"]
```

**Step 1 — Build the image:**

```bash
docker build -t myintwl/python-app:v1 .
```

**Step 2 — Test locally before pushing:**

```bash
docker run -p 5000:5000 myintwl/python-app:v1
curl http://localhost:5000/api/v1/health
# Expected: {"status": "healthy"}
```

**Step 3 — Push to Docker Hub:**

```bash
docker push myintwl/python-app:v1
```

---

## Deploy to Kubernetes with Raw Manifests

This approach uses `deployment.yml` and `ingress.yml` directly without Helm.

### Step 1 — Start Minikube and enable Ingress

```bash
minikube start
minikube addons enable ingress
```

### Step 2 — Load image into Minikube

```bash
minikube image load myintwl/python-app:v1

# Verify
minikube image ls | grep python-app
```

### Step 3 — Apply the Deployment and Service

The `deployment.yml` creates a Deployment with 3 replicas and a NodePort Service:

```yaml
# deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: python-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: python-app
  template:
    metadata:
      labels:
        app: python-app
    spec:
      containers:
        - name: python-app
          image: myintwl/python-app:v1
          ports:
            - containerPort: 5000
---
apiVersion: v1
kind: Service
metadata:
  name: python-app
spec:
  type: NodePort
  selector:
    app: python-app
  ports:
    - port: 5000
      targetPort: 5000
```

```bash
kubectl apply -f deployment.yml
```

### Step 4 — Apply the Ingress

The `ingress.yml` routes `python-app.local` traffic to both API endpoints:

```yaml
# ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: python-app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - host: python-app.local
      http:
        paths:
          - path: /api/v1/details
            pathType: Prefix
            backend:
              service:
                name: python-app
                port:
                  number: 5000
          - path: /api/v1/health
            pathType: Prefix
            backend:
              service:
                name: python-app
                port:
                  number: 5000
```

```bash
kubectl apply -f ingress.yml
```

### Step 5 — Verify

```bash
kubectl get pods
kubectl get svc
kubectl get ingress
```

### Step 6 — Access the app via port-forward

```bash
# Terminal 1 - keep running
kubectl port-forward svc/python-app 8080:5000

# Terminal 2 - test
curl http://localhost:8080/api/v1/health
curl http://localhost:8080/api/v1/details
```

---

## Deploy to Kubernetes with Helm

This approach uses the Helm chart in `charts/python-app/`.

### Step 1 — Start Minikube and enable Ingress

```bash
minikube start
minikube addons enable ingress
```

### Step 2 — Load image into Minikube

```bash
minikube image load myintwl/python-app:v1
```

### Step 3 — Configure values.yaml

Key settings to verify in `charts/python-app/values.yaml`:

```yaml
image:
  repository: myintwl/python-app
  tag: "v1"
  pullPolicy: Never          # Use Never since image is loaded into minikube locally

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

# IMPORTANT: probes must point to a valid endpoint
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

> ⚠️ Never set probe path to `/` — Flask has no root route and will return 404, causing `CrashLoopBackOff`.

### Step 4 — Create namespace and install

```bash
kubectl create namespace python-app
helm install python-app -n python-app ./charts/python-app
```

### Step 5 — Verify deployment

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

### Step 6 — Access the app via port-forward

```bash
# Terminal 1 - keep running
kubectl port-forward svc/python-app 8080:5000 -n python-app

# Terminal 2 - test
curl http://localhost:8080/api/v1/health
# {"status": "healthy"}

curl http://localhost:8080/api/v1/details
# {"message": "Hello World"}
```

### Upgrade after changes

```bash
helm upgrade python-app -n python-app ./charts/python-app
```

---

## Install ArgoCD on Minikube

ArgoCD is a GitOps continuous delivery tool for Kubernetes. Follow these steps to install it on Minikube and access the UI.

### Step 1 — Create the ArgoCD namespace

```bash
kubectl create namespace argocd
```

### Step 2 — Add the Argo Helm repo

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
```

### Step 3 — Install ArgoCD via Helm

```bash
helm install argocd argo/argo-cd -n argocd
```

### Step 4 — Wait for all pods to be Running

```bash
kubectl get pods -n argocd -w
```

Wait until all pods show `Running` or `Completed`:

```
NAME                                               READY   STATUS      RESTARTS
argocd-application-controller-0                    1/1     Running     0
argocd-applicationset-controller-xxxxxxxx-xxxxx    1/1     Running     0
argocd-dex-server-xxxxxxxx-xxxxx                   1/1     Running     0
argocd-notifications-controller-xxxxxxxx-xxxxx     1/1     Running     0
argocd-redis-xxxxxxxx-xxxxx                        1/1     Running     0
argocd-repo-server-xxxxxxxx-xxxxx                  1/1     Running     0
argocd-server-xxxxxxxx-xxxxx                       1/1     Running     0
```

### Step 5 — Apply the ArgoCD Ingress

The `argoingress.yml` exposes ArgoCD at `argocd.local` using SSL passthrough:

```yaml
# argoingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-ingress
  namespace: argocd
  annotations:
    nginx.ingress.kubernetes.io/ssl-passthrough: "true"
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
spec:
  ingressClassName: nginx
  rules:
    - host: argocd.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: argocd-server
                port:
                  number: 443
```

```bash
kubectl apply -f argoingress.yml

# Verify
kubectl get ingress -n argocd
```

### Step 6 — Add argocd.local to /etc/hosts

```bash
echo "127.0.0.1 argocd.local" | sudo tee -a /etc/hosts

# Verify
cat /etc/hosts | grep argocd
```

### Step 7 — Port-forward the ArgoCD server

On Mac with the Docker driver, use port-forward to access ArgoCD:

```bash
# Terminal 1 - keep this running
kubectl port-forward svc/argocd-server 8443:443 -n argocd
```

### Step 8 — Get the initial admin password

Open a new terminal and run:

```bash
kubectl get secret argocd-initial-admin-secret \
  -n argocd \
  -o jsonpath="{.data.password}" | base64 -d
```

Copy the output — this is your login password.

### Step 9 — Access the ArgoCD UI

Open your browser and go to:

```
https://localhost:8443
```

> ⚠️ Your browser will show a certificate warning — click **Advanced** then **Proceed to localhost**. This is expected since ArgoCD uses a self-signed certificate by default.

Login with:
- **Username:** `admin`
- **Password:** output from Step 8

### Step 10 — Verify everything is working

```bash
kubectl get all -n argocd
kubectl get ingress -n argocd
```

---

## Accessing the App on Mac (Docker Driver)

When Minikube uses the Docker driver on Mac, the cluster IP `192.168.49.2` is inside a Docker virtual network and **not directly reachable** from the host machine. Always use one of these methods:

### Option 1 — Port-forward (Recommended)

```bash
# Flask app
kubectl port-forward svc/python-app 8080:5000 -n python-app

# ArgoCD
kubectl port-forward svc/argocd-server 8443:443 -n argocd
```

### Option 2 — Minikube Tunnel

```bash
# Update /etc/hosts to use 127.0.0.1
sudo sed -i '' 's/192.168.49.2 python-app.local/127.0.0.1 python-app.local/' /etc/hosts

# Terminal 1 - keep running
sudo minikube tunnel

# Terminal 2 - test
curl http://python-app.local/api/v1/health
```

---

## Useful Commands

```bash
# --- Minikube ---
minikube start
minikube stop
minikube status
minikube ip
minikube image load myintwl/python-app:v1
minikube image ls | grep python-app
minikube addons list | grep ingress

# --- Pods ---
kubectl get pods -n python-app
kubectl get pods -n argocd
kubectl get pods -A                                     # all namespaces
kubectl get pods -n python-app -w                       # watch in real time
kubectl logs -f -l app=python-app -n python-app         # stream logs
kubectl describe pod -n python-app                      # events and details

# --- Services & Ingress ---
kubectl get svc -n python-app
kubectl get ingress -A                                  # all namespaces

# --- Port Forward ---
kubectl port-forward svc/python-app 8080:5000 -n python-app
kubectl port-forward svc/argocd-server 8443:443 -n argocd

# --- Helm ---
helm list -A                                            # all releases
helm upgrade --install python-app -n python-app ./charts/python-app
helm uninstall python-app -n python-app

# --- Cleanup ---
kubectl delete namespace python-app
kubectl delete namespace argocd
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

To disable probes temporarily for debugging:
```bash
helm upgrade python-app -n python-app ./charts/python-app \
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

**Fix:**
```bash
minikube image load myintwl/python-app:v1
```

Set in `values.yaml`:
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

**Fix:**
```bash
kubectl port-forward svc/python-app 8080:5000 -n python-app
curl http://localhost:8080/api/v1/health
```

---

### Release Already Exists

**Symptom:**
```
Error: INSTALLATION FAILED: cannot reuse a name that is still in use
```

**Fix:**
```bash
helm uninstall python-app -n python-app
helm install python-app -n python-app ./charts/python-app

# Or combine into one command:
helm upgrade --install python-app -n python-app ./charts/python-app
```

---

### Path Already Defined in Ingress

**Symptom:**
```
admission webhook denied the request: host "python-app.local" and path
"/api/v1/health" is already defined in ingress default/python-app-ingress
```

**Cause:** A duplicate ingress exists in the `default` namespace.

**Fix:**
```bash
kubectl delete ingress python-app-ingress -n default
helm upgrade python-app -n python-app ./charts/python-app
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

### ArgoCD Browser Certificate Warning

**Symptom:** Browser shows "Your connection is not private" at `https://localhost:8443`.

**This is expected.** ArgoCD uses a self-signed certificate. Click **Advanced → Proceed to localhost** to continue.

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
| ArgoCD cert warning in browser | Self-signed certificate | Click Advanced → Proceed |

**Security scanning summary:**

| Type | Tool | What it scans | When |
|------|------|---------------|------|
| **SAST** | Bandit | Python source code for insecure patterns | Before build |
| **SCA** | Trivy fs | `requirements.txt` dependencies for CVEs | Before build |
| **Container Scan** | Trivy image | Built Docker image layers for CVEs and secrets | After build, before push |
| **DAST** | OWASP ZAP | Live running app for web vulnerabilities | After build, before push |
| **Functional** | curl | API endpoints return correct responses | After build, before push |

**Pipeline flow:**
```
SAST (Bandit) ──┐
                ├──→ Build image → Container Scan (Trivy)
SCA  (Trivy)  ──┘                        ↓
                               DAST (OWASP ZAP) on live container
                                         ↓
                               Functional tests (curl)
                                         ↓
                               Push to Docker Hub ✅