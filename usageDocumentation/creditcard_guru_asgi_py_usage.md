# asgi.py Usage Documentation

## Executive Summary
This document provides usage documentation for the `creditcard_guru/asgi.py` module, which contains the ASGI (Asynchronous Server Gateway Interface) configuration for the Django project. This module provides the ASGI application interface that modern asynchronous web servers use to serve the credit card recommendation platform with support for WebSockets and async features.

## Module Overview
`creditcard_guru/asgi.py` is the ASGI application module that serves as the interface between asynchronous web servers and the Django application. It configures the Django settings module and creates the ASGI application object that modern web servers use for async/WebSocket support.

### Key Responsibilities:
- **ASGI Application Interface**: Provides the standard ASGI application callable that async web servers (Uvicorn, Daphne, etc.) use to serve the Django application
- **Django Settings Configuration**: Sets the DJANGO_SETTINGS_MODULE environment variable to point to the project's settings configuration for async deployment
- **Async Deployment Interface**: Serves as the entry point for modern asynchronous web server deployments with WebSocket and async view support


## Initialization
The `creditcard_guru/asgi.py` file is loaded by ASGI-compatible web servers. It sets up the Django application for async deployment with WebSocket support.

```python
# ASGI server initialization (e.g., Uvicorn, Daphne)
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creditcard_guru.settings')
application = get_asgi_application()
```

## Public API documentation

### ASGI Application Interface
Provides the standard ASGI application callable for modern async web server integration.

#### Core Interface:
- **application**: ASGI application callable that async web servers use to serve requests
- **Async Support**: Enables WebSocket connections and async view support
- **Environment Setup**: Configures Django settings module for async deployment
- **Modern Deployment**: Optimized for modern async web servers like Uvicorn

## Dependencies
Minimal dependencies - standard framework dependencies.

## Practical Code Examples

### Example 1: Uvicorn Production Deployment
How to use asgi.py with Uvicorn for modern async deployment.

```bash
# Production deployment with Uvicorn
uvicorn creditcard_guru.asgi:application --host 0.0.0.0 --port 8000

# With multiple workers for better performance
uvicorn creditcard_guru.asgi:application --host 0.0.0.0 --port 8000 --workers 4
```

### Example 2: Daphne WebSocket Support
How to use asgi.py with Daphne for WebSocket and async view support.

```bash
# Deployment with Daphne for WebSocket support
daphne -b 0.0.0.0 -p 8000 creditcard_guru.asgi:application

# In production with process management
daphne -u /tmp/daphne.sock creditcard_guru.asgi:application
```

