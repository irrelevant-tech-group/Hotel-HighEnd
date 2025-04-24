#!/bin/bash

# Start nginx in the background
nginx

# Start gunicorn
gunicorn --bind 0.0.0.0:8001 --workers 4 app:app 