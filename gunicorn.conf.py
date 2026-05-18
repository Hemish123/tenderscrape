# gunicorn.conf.py
"""
Gunicorn configuration for Azure App Service deployment.
The default 30-second worker timeout is too short for AI summarization
calls that can take 60–120 seconds.
"""

import multiprocessing

# Bind to the port Azure provides
bind = "0.0.0.0:8000"

# Worker configuration
workers = multiprocessing.cpu_count() * 2 + 1

# Timeout: Allow up to 300 seconds (5 min) for long-running AI requests
timeout = 300

# Graceful timeout for worker restart
graceful_timeout = 120

# Keep-alive connections
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
