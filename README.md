# Ops Health Monitor

A small Flask task API deployed the way a production service is: containerized with **Docker**, served behind **Nginx**, monitored with **Prometheus + Grafana**, and shipped to **AWS EC2** by a **GitHub Actions CI/CD** pipeline.

## Architecture

```
GitHub push -> GitHub Actions (pytest -> docker build -> SSH deploy)
                                                        |
                                              AWS EC2 (Ubuntu, Docker Compose)
   Internet -> Nginx :80 -> Flask/Gunicorn :8000 (non-root container, healthcheck)
                                  ^
                  Prometheus scrapes /metrics every 15s -> Grafana :3000
```

- `/health` for health checks, `/api/tasks` (GET, POST, DELETE) for the API
- `/metrics` in Prometheus format (request count, latency, uptime); blocked from the public internet by Nginx
- Unit tests with pytest run on every push and pull request

## Run locally

```bash
docker compose up -d --build
curl localhost/health
curl -X POST localhost/api/tasks -H "Content-Type: application/json" -d '{"title":"hello"}'
# Grafana: http://localhost:3000  (admin / admin, change it)
```

Run the tests: `pip install -r app/requirements.txt pytest && pytest -q`

## Deploy to AWS EC2

1. Launch an **Ubuntu 24.04** EC2 instance (t2.micro or t3.micro is enough). Create a key pair and download the `.pem` file.
2. Security group inbound rules: **22** (your IP only), **80** (anywhere), **3000** (your IP only, for Grafana).
3. SSH in and install Docker:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
   sudo usermod -aG docker ubuntu && exit   # log in again so the group applies
   ```
4. Clone your repo and start it:
   ```bash
   git clone https://github.com/<your-username>/ops-health-monitor.git
   cd ops-health-monitor && docker compose up -d --build
   ```
5. Open `http://<EC2-PUBLIC-IP>/health` to check it works.

## Enable automatic deployment (CI/CD)

In your GitHub repo: Settings -> Secrets and variables -> Actions -> add:

| Secret | Value |
|---|---|
| `EC2_HOST` | the EC2 public IP |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | the full contents of your `.pem` file |

Every push to `main` now runs the tests, builds the image, and deploys to EC2.

## Grafana panels (PromQL)

- Request rate: `sum(rate(app_requests_total[1m]))`
- Error rate: `sum(rate(app_requests_total{status=~"5.."}[1m]))`
- Average latency: `rate(app_request_duration_seconds_sum[1m]) / rate(app_request_duration_seconds_count[1m])`
