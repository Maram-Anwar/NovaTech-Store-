#!/usr/bin/env sh
cd "$(dirname "$0")"
python3 api_server.py || python api_server.py
