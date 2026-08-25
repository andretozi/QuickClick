"""
Quick Click — lancador unico do site.

Uso:
    python main.py            # build se necessario, sobe em http://localhost:8080
    REBUILD=1 python main.py  # forca rebuild antes de subir (Windows: set REBUILD=1)

O que ele faz, em ordem:
    1. Garante o front buildado em ./dist (roda `npm install` se faltar node_modules
       e `npm run build` se ./dist estiver ausente / desatualizado / REBUILD=1).
    2. Sobe um servidor HTTP na porta 8080 servindo ./dist com fallback SPA
       (rotas desconhecidas caem em index.html).
    3. Abre o navegador padrao em http://localhost:8080.

Zero dependencias Python fora da stdlib.
"""

from __future__ import annotations

import http.server
import os
import posixpath
import shutil
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
SRC = ROOT / "src"
INDEX_HTML = ROOT / "index.html"
PACKAGE_JSON = ROOT / "package.json"
NODE_MODULES = ROOT / "node_modules"
PORT = 8080
HOST = "127.0.0.1"


# ---------------------------------------------------------------------------
# npm / build
# ---------------------------------------------------------------------------

def _find_npm() -> str:
    """Localiza o executavel npm de forma portavel (Windows usa npm.cmd)."""
    for name in ("npm.cmd", "npm.bat", "npm"):
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError(
        "npm nao encontrado no PATH. Instale Node.js (https://nodejs.org) "
        "e reabra o terminal."
    )


def _run_npm(npm: str, *args: str) -> None:
    """Roda `npm <args>` mostrando a saida em tempo real; aborta se falhar."""
    cmd = [npm, *args]
    print(f"[main.py] $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=ROOT, shell=False)
    if proc.returncode != 0:
        raise SystemExit(
            f"[main.py] Falhou: '{' '.join(cmd)}' (exit {proc.returncode}). "
            "Corrija o erro acima e rode 'python main.py' de novo."
        )


def _latest_mtime(path: Path) -> float:
    """Ultimo mtime de qualquer arquivo dentro de `path` (recursivo)."""
    if not path.exists():
        return 0.0
    if path.is_file():
        return path.stat().st_mtime
    latest = 0.0
    for p in path.rglob("*"):
        if p.is_file():
            m = p.stat().st_mtime
            if m > latest:
                latest = m
    return latest


def _dist_is_stale() -> bool:
    """True se dist/ nao existe ou esta mais antigo que src/, index.html, config."""
    if not DIST.exists() or not (DIST / "index.html").exists():
        return True
    dist_m = _latest_mtime(DIST)
    for watched in (SRC, INDEX_HTML, ROOT / "vite.config.js", PACKAGE_JSON):
        if _latest_mtime(watched) > dist_m:
            return True
    return False


def ensure_build() -> None:
    force = os.environ.get("REBUILD") == "1"
    npm = _find_npm()

    if not NODE_MODULES.exists():
        print("[main.py] node_modules/ ausente — rodando npm install")
        _run_npm(npm, "install")

    if force or _dist_is_stale():
        motivo = "REBUILD=1" if force else "dist/ desatualizado"
        print(f"[main.py] Buildando o front ({motivo}) — npm run build")
        _run_npm(npm, "run", "build")
    else:
        print("[main.py] dist/ ja esta atualizado — pulando build "
              "(use REBUILD=1 para forcar)")


# ---------------------------------------------------------------------------
# servidor HTTP com fallback SPA
# ---------------------------------------------------------------------------

class SPARequestHandler(http.server.SimpleHTTPRequestHandler):
    """Serve dist/ e devolve index.html para qualquer path que nao seja arquivo."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(DIST), **kwargs)

    def log_message(self, fmt: str, *args) -> None:  # menos ruido no console
        sys.stderr.write(f"[http] {self.address_string()} {fmt % args}\n")

    def send_head(self):
        path = self._resolve_path(self.path)
        # Fallback SPA: se o path nao aponta para um arquivo real dentro de dist,
        # devolve index.html (comportamento padrao de single-page apps).
        target = Path(path)
        if not target.exists() or target.is_dir():
            index = DIST / "index.html"
            if index.exists():
                self.path = "/index.html"
                return super().send_head()
        return super().send_head()

    def _resolve_path(self, url_path: str) -> str:
        """Copia da logica interna de SimpleHTTPRequestHandler para saber o path
        no disco antes de decidir se e' fallback."""
        parsed = urllib.parse.urlsplit(url_path)
        path = parsed.path
        try:
            path = urllib.parse.unquote(path, errors="surrogatepass")
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)
        words = [w for w in path.split("/") if w and w != ".."]
        resolved = Path(self.directory)
        for word in words:
            resolved = resolved / word
        return str(resolved)


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind((host, port))
        except OSError:
            return False
        return True


def _open_browser_when_ready(url: str) -> None:
    """Espera o servidor aceitar conexao e entao abre o navegador."""
    for _ in range(40):  # ate ~4s
        try:
            with socket.create_connection((HOST, PORT), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    try:
        webbrowser.open(url)
    except Exception:  # navegador nao disponivel nao e' fatal
        pass


def serve() -> None:
    if not _port_is_free(HOST, PORT):
        raise SystemExit(
            f"[main.py] A porta {PORT} ja esta em uso. Feche o outro processo "
            f"(ou identifique com `netstat -ano | findstr :{PORT}` no Windows) "
            f"e rode de novo. Nao vou trocar de porta silenciosamente."
        )

    url = f"http://{HOST}:{PORT}"
    threading.Thread(
        target=_open_browser_when_ready, args=(url,), daemon=True
    ).start()

    with ReusableTCPServer((HOST, PORT), SPARequestHandler) as httpd:
        print(f"[main.py] Servindo {DIST} em {url}  (Ctrl+C para parar)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[main.py] Encerrando.")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    ensure_build()
    serve()


if __name__ == "__main__":
    main()