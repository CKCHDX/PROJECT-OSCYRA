"""Sverkan Qt Client (PyQt5 WebEngine)."""

import os
import sys
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView



import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess

class LocalAppHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        print(f"Received POST request: {self.path}")
        if self.path == '/local-launch':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                app_path = data.get('app_path')
                print(f"Requested app_path: {app_path}")
                if app_path:
                    try:
                        if not os.path.exists(app_path):
                            msg = f"App path not found: {app_path}"
                            print(msg)
                            self.send_response(404)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({'status': 'error', 'error': msg}).encode())
                            return
                        subprocess.Popen(app_path, shell=True)
                        print(f"Launched app: {app_path}")
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'status': 'ok'}).encode())
                    except Exception as e:
                        msg = f"Launch error: {str(e)}"
                        print(msg)
                        self.send_response(500)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'status': 'error', 'error': msg}).encode())
                else:
                    msg = "No app_path provided"
                    print(msg)
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'error', 'error': msg}).encode())
            except Exception as e:
                msg = f"Request error: {str(e)}"
                print(msg)
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'error': msg}).encode())
        else:
            print(f"Unknown POST path: {self.path}")
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'error': 'Unknown path'}).encode())

def run_local_server(port=17345):
    server = HTTPServer(('127.0.0.1', port), LocalAppHandler)
    server.serve_forever()

def main():
    port = int(os.getenv("APP_PORT", 5000))
    url = f"http://sverkan.oscyra.solutions"

    # Start local HTTP server in background thread
    server_thread = threading.Thread(target=run_local_server, daemon=True)
    server_thread.start()

    app = QApplication(sys.argv)
    app.setApplicationName("Sverkan")

    window = QMainWindow()
    window.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint)
    window.showFullScreen()

    view = QWebEngineView()
    view.setUrl(QUrl(url))
    window.setCentralWidget(view)

    # Prevent closing
    def closeEvent(event):
        event.ignore()

    window.closeEvent = closeEvent

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
