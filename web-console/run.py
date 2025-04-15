import http.server
import socketserver
import os

LOG_PATH = "/tmp/gagasampler.log"
PORT = 80

class LogRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Gaga Sampler - Log</title>
    <style>
        body { background: #111; color: #0f0; font-family: monospace; padding: 20px; }
        .log-line { margin-bottom: 4px; }
        .start { color: #00ffcc; }
        .win { color: gold; }
        .end { color: #888; }
        .error, .repetida { color: red; }
        .default { color: #0f0; }
    </style>
    <script>
        async function fetchLog() {
            const res = await fetch("/log.html");
            const html = await res.text();
            document.getElementById("log").innerHTML = html;
        }
        setInterval(fetchLog, 1000);
        window.onload = fetchLog;
    </script>
</head>
<body>
    <h2>🎛 Gaga Sampler - Log em tempo real</h2>
    <div id="log">Carregando log...</div>
</body>
</html>"""

            self.wfile.write(html.encode("utf-8"))

        elif self.path == "/log.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            if os.path.exists(LOG_PATH):
                with open(LOG_PATH, "r") as f:
                    lines = f.readlines()
                html_lines = []
                for line in lines:
                    css_class = "default"
                    lower = line.lower()
                    if "start" in lower:
                        css_class = "start"
                    elif "fim" in lower or "final" in lower:
                        css_class = "end"
                    elif "win" in lower or "vitoria" in lower or "vencedor" in lower:
                        css_class = "win"
                    elif "erro" in lower or "repetida" in lower:
                        css_class = "error"
                    html_lines.append(f'<div class="log-line {css_class}">{line.strip()}</div>')
                self.wfile.write("\n".join(html_lines).encode("utf-8"))
            else:
                self.wfile.write("<i>(log ainda não criado)</i>".encode("utf-8"))

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
