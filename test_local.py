#!/usr/bin/env python3
"""Serve index.html locally for testing."""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

os.chdir('/home/ubuntu/booking-repo')

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

srv = HTTPServer(('127.0.0.1', 8899), Handler)
print('serving on 8899')
srv.serve_forever()
