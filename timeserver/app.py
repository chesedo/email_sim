#!/usr/bin/env python3

import http.server
import socketserver
from datetime import datetime
import json

class TimeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/time':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            response = {'current_time': current_time}
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'status': 'healthy'}
            self.wfile.write(json.dumps(response).encode())
        else:
            super().do_GET()

with socketserver.TCPServer(('', 8080), TimeHandler) as httpd:
    httpd.serve_forever()
