import http.server
import socketserver
import os
import urllib.parse
import posixpath

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vlibras_local")
PORT = 8765

class VLibrasHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        # normaliza a URL antes de processar
        self.path = self._fix_path(self.path)
        super().do_GET()

    def do_HEAD(self):
        self.path = self._fix_path(self.path)
        super().do_HEAD()

    def _fix_path(self, path):
        # separa querystring
        if "?" in path:
            path, qs = path.split("?", 1)
            qs = "?" + qs
        else:
            qs = ""

        # remove barras duplas: /target//assets -> /target/assets
        while "//" in path:
            path = path.replace("//", "/")

        # remove prefixo duplicado: /target/target/X -> /target/X
        if path.startswith("/target/target/"):
            path = "/target/" + path[len("/target/target/"):]

        return path + qs

    def translate_path(self, path):
        path = urllib.parse.unquote(path.split("?")[0])
        # normaliza separadores do OS
        path = path.lstrip("/")
        return os.path.normpath(os.path.join(BASE_DIR, path))

    def log_message(self, fmt, *args):
        print(self.address_string(), "-", fmt % args)

with socketserver.TCPServer(("", PORT), VLibrasHandler) as httpd:
    httpd.allow_reuse_address = True
    print(f"Servidor rodando em http://localhost:{PORT}")
    print(f"Servindo arquivos de: {BASE_DIR}")
    print(f"Diretório existe? {os.path.isdir(BASE_DIR)}")
    print(f"Conteúdo: {os.listdir(BASE_DIR)}")
    httpd.serve_forever()