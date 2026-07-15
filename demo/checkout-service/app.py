import logging
import os
import random
import sys
import time
import uuid

from flask import Flask, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = Flask(__name__)

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","service":"checkout-service","msg":"%(message)s"}',
)
log = logging.getLogger("checkout-service")

ENABLE_RESPONSE_CACHE = os.environ.get("ENABLE_RESPONSE_CACHE", "false").lower() == "true"
BASE_ERROR_RATE = float(os.environ.get("BASE_ERROR_RATE", "0.01"))

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency")

# Unbounded in-memory cache: introduced by the "response caching for performance" change.
# Nothing ever evicts entries, so resident memory grows with request volume until the
# container hits its memory limit and the kubelet OOM-kills the pod.
_response_cache: dict[str, bytes] = {}


@app.route("/healthz")
def healthz():
    return jsonify(status="ok")


@app.route("/checkout", methods=["POST", "GET"])
def checkout():
    start = time.time()
    order_id = str(uuid.uuid4())

    if ENABLE_RESPONSE_CACHE:
        # ~50KB retained per request, forever.
        _response_cache[order_id] = os.urandom(50_000)

    fail = random.random() < (BASE_ERROR_RATE if not ENABLE_RESPONSE_CACHE else BASE_ERROR_RATE * 8)
    duration = time.time() - start
    REQUEST_LATENCY.observe(duration)

    if fail:
        REQUEST_COUNT.labels(status="500").inc()
        log.error(f"checkout failed order_id={order_id} exception=CheckoutProcessingError cache_entries={len(_response_cache)}")
        return jsonify(error="checkout_failed", order_id=order_id), 500

    REQUEST_COUNT.labels(status="200").inc()
    log.info(f"checkout ok order_id={order_id} duration_ms={duration * 1000:.1f}")
    return jsonify(status="ok", order_id=order_id)


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
