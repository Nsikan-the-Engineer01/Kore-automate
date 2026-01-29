"""
Gunicorn configuration file for Kore API.

Reads configuration from environment variables with sensible defaults.
"""

import os
import multiprocessing

# Get environment variables safely
def get_env(key, default=None, var_type=str):
    """Get environment variable with type conversion."""
    value = os.environ.get(key, default)
    if value is None:
        return value
    if var_type == int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return int(default) if isinstance(default, int) else default
    elif var_type == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    return value


# Server Socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker Processes
# Calculate optimal worker count: (2 × CPU_CORES) + 1
# or use WEB_CONCURRENCY environment variable
cpu_count = multiprocessing.cpu_count()
default_workers = max((2 * cpu_count) + 1, 3)
workers = get_env('WEB_CONCURRENCY', default_workers, int)

# Worker Class
worker_class = "sync"  # Standard blocking worker
worker_connections = 1000
timeout = get_env('GUNICORN_TIMEOUT', 60, int)
keepalive = 2

# Logging
loglevel = get_env('LOG_LEVEL', 'info').lower()
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "kore-api"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed, configure via environment)
keyfile = get_env('GUNICORN_KEYFILE')
certfile = get_env('GUNICORN_CERTFILE')
ssl_version = get_env('GUNICORN_SSL_VERSION', 'TLS')
cert_reqs = get_env('GUNICORN_CERT_REQS', 0, int)
ca_certs = get_env('GUNICORN_CA_CERTS')
ciphers = get_env('GUNICORN_CIPHERS')

# Application
default_proc_name = "gunicorn"

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print(f"Gunicorn server is starting...")
    print(f"  Workers: {workers}")
    print(f"  Timeout: {timeout}s")
    print(f"  Log level: {loglevel}")
    print(f"  Bind: {bind}")


def when_ready(server):
    """Called just after the server is started."""
    print(f"Gunicorn server is ready. Spawning workers")


def on_exit(server):
    """Called just before a worker is exited."""
    print("Gunicorn worker exited")


# Command line arguments can be passed as environment variables
# Examples:
# WEB_CONCURRENCY=5 gunicorn -c config/gunicorn.conf.py config.wsgi:application
# GUNICORN_TIMEOUT=120 gunicorn -c config/gunicorn.conf.py config.wsgi:application
# LOG_LEVEL=debug gunicorn -c config/gunicorn.conf.py config.wsgi:application
