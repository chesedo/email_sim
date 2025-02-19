#!/usr/bin/env python3

import http.server
import socketserver
import signal
import sys
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

def signal_handler(signum, frame):
    print("Received shutdown signal, closing server...")
    httpd.server_close()
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create and start server
    with socketserver.TCPServer(('', 8080), TimeHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Received keyboard interrupt, closing server...")
            httpd.server_close()
