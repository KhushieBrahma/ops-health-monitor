"""Small task API with health checks and Prometheus-format metrics (no extra deps)."""
import threading
import time

from flask import Flask, Response, g, jsonify, request

app = Flask(__name__)

START_TIME = time.time()
_lock = threading.Lock()
_tasks = {}
_next_id = 1
_request_counts = {}  # (method, endpoint, status) -> count
_latency_sum = 0.0
_latency_count = 0


@app.before_request
def _start_timer():
    g.t0 = time.perf_counter()


@app.after_request
def _record_metrics(resp):
    global _latency_sum, _latency_count
    if request.path != "/metrics":
        duration = time.perf_counter() - getattr(g, "t0", time.perf_counter())
        endpoint = request.url_rule.rule if request.url_rule else "unmatched"
        key = (request.method, endpoint, str(resp.status_code))
        with _lock:
            _request_counts[key] = _request_counts.get(key, 0) + 1
            _latency_sum += duration
            _latency_count += 1
    return resp


@app.get("/health")
def health():
    return jsonify(status="ok", uptime_seconds=round(time.time() - START_TIME, 1))


@app.get("/api/tasks")
def list_tasks():
    with _lock:
        return jsonify(list(_tasks.values()))


@app.post("/api/tasks")
def create_task():
    global _next_id
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify(error="title is required"), 400
    with _lock:
        task = {"id": _next_id, "title": title, "done": False}
        _tasks[_next_id] = task
        _next_id += 1
    return jsonify(task), 201


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    with _lock:
        if task_id not in _tasks:
            return jsonify(error="not found"), 404
        del _tasks[task_id]
    return "", 204


@app.get("/metrics")
def metrics():
    lines = [
        "# HELP app_requests_total Total HTTP requests.",
        "# TYPE app_requests_total counter",
    ]
    with _lock:
        for (method, endpoint, status), count in sorted(_request_counts.items()):
            lines.append(
                f'app_requests_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}'
            )
        lines += [
            "# HELP app_request_duration_seconds Request latency.",
            "# TYPE app_request_duration_seconds summary",
            f"app_request_duration_seconds_sum {_latency_sum:.6f}",
            f"app_request_duration_seconds_count {_latency_count}",
            "# HELP app_tasks Current number of tasks.",
            "# TYPE app_tasks gauge",
            f"app_tasks {len(_tasks)}",
        ]
    lines += [
        "# HELP app_uptime_seconds Seconds since the app started.",
        "# TYPE app_uptime_seconds gauge",
        f"app_uptime_seconds {time.time() - START_TIME:.1f}",
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain; version=0.0.4")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
