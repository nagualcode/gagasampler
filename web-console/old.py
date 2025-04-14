import http.server
import socketserver
import threading
import time
import os

LOG_PATH = "/tmp/gagasampler.log"
PORT = 80

class LogRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            self.wfile.write(b"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Gaga Sampler - Log</title>
    <style>
        body { background: #111; color: #0f0; font-family: monospace; padding: 20px; }
        pre { white-space: pre-wrap; }
    </style>
    <script>
        async function fetchLog() {
            const res = await fetch("/log.txt");
            const text = await res.text();
            document.getElementById("log").textContent = text;
        }
        setInterval(fetchLog, 1000); // Atualiza a cada 1s
        window.onload = fetchLog;
    </script>
</head>
<body>
    <h2>🎛 Gaga Sampler - Log em tempo real</h2>
    <pre id="log">Carregando log...</pre>
</body>
</html>""")
        elif self.path == "/log.txt":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            if os.path.exists(LOG_PATH):
                with open(LOG_PATH, "r") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                self.wfile.write(b"(log ainda nao criado)")
        else:
            self.send_error(404, "Arquivo não encontrado")

def start_server():
    with socketserver.TCPServer(("", PORT), LogRequestHandler) as httpd:
        print(f"Servidor HTTP rodando na porta {PORT}...")
        httpd.serve_forever()

if __name__ == "__main__":
    try:
        start_server()
    except PermissionError:
        print("❌ Permissão negada! Rode como sudo para usar a porta 80.")

