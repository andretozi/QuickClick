"""
Quick Click: lancador unico do sistema (front + back).

Uso:
    python main.py               # prepara o que faltar e sobe tudo em http://127.0.0.1:8080
    REBUILD=1 python main.py     # forca o build do front (PowerShell: $env:REBUILD=1; python main.py)
    NO_BROWSER=1 python main.py  # nao abre o navegador (util em testes automaticos)

O que ele faz, em ordem:
    1. Front (frontend/): roda `npm install` se faltar frontend/node_modules e
       `npm run build` se frontend/dist estiver ausente, desatualizado ou com REBUILD=1.
    2. Back (backend/): instala com pip o que faltar de backend/requirements.txt
       no mesmo Python que esta rodando este arquivo (o interpretador do PyCharm).
    3. Sobe um unico servidor (Uvicorn) em http://127.0.0.1:8080:
       a API em /api (documentacao automatica em /docs) e o front buildado no resto.
    4. Abre o navegador padrao.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"
NODE_MODULES = FRONTEND / "node_modules"
REQUIREMENTS = ROOT / "backend" / "requirements.txt"
PORT = 8080
HOST = "127.0.0.1"


# ---------------------------------------------------------------------------
# front: npm / build
# ---------------------------------------------------------------------------

def _find_npm() -> str:
    """Localiza o executavel npm de forma portavel (Windows usa npm.cmd)."""
    for name in ("npm.cmd", "npm.bat", "npm"):
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit(
        "[main.py] npm nao encontrado no PATH. Instale Node.js (https://nodejs.org) "
        "e reabra o PyCharm ou o terminal."
    )


def _run_npm(npm: str, *args: str) -> None:
    """Roda `npm <args>` dentro de frontend/ mostrando a saida; aborta se falhar."""
    cmd = [npm, *args]
    print(f"[main.py] $ {' '.join(cmd)}  (em frontend/)", flush=True)
    proc = subprocess.run(cmd, cwd=FRONTEND, shell=False)
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
    """True se frontend/dist nao existe ou esta mais antigo que o codigo do front."""
    if not DIST.exists() or not (DIST / "index.html").exists():
        return True
    dist_m = _latest_mtime(DIST)
    watched = (
        FRONTEND / "src",
        FRONTEND / "index.html",
        FRONTEND / "vite.config.js",
        FRONTEND / "package.json",
    )
    return any(_latest_mtime(path) > dist_m for path in watched)


def ensure_frontend_build() -> None:
    force = os.environ.get("REBUILD") == "1"
    npm = _find_npm()

    if not NODE_MODULES.exists():
        print("[main.py] frontend/node_modules ausente: rodando npm install")
        _run_npm(npm, "install")

    if force or _dist_is_stale():
        motivo = "REBUILD=1" if force else "frontend/dist desatualizado"
        print(f"[main.py] Buildando o front ({motivo}): npm run build")
        _run_npm(npm, "run", "build")
    else:
        print("[main.py] frontend/dist ja esta atualizado: pulando build "
              "(use REBUILD=1 para forcar)")


# ---------------------------------------------------------------------------
# back: dependencias Python
# ---------------------------------------------------------------------------

def _required_packages() -> list[str]:
    """Nomes dos pacotes de backend/requirements.txt (sem versao e sem comentarios)."""
    names = []
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        names.append(re.split(r"[\s<>=!~;\[]", line, maxsplit=1)[0])
    return names


def _is_installed(package: str) -> bool:
    try:
        importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def ensure_backend_deps() -> None:
    missing = [name for name in _required_packages() if not _is_installed(name)]
    if not missing:
        print("[main.py] dependencias do back ja instaladas")
        return

    print(f"[main.py] Instalando dependencias do back que faltam: {', '.join(missing)}")
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    print(f"[main.py] $ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, shell=False)
    if proc.returncode != 0:
        raise SystemExit(
            "[main.py] Falhou a instalacao das dependencias do back. Confira a internet e "
            "rode de novo. Se o pip recusar instalar no Python do sistema, crie uma .venv "
            "(python -m venv .venv), escolha ela como interpretador no PyCharm e rode o "
            "main.py de novo."
        )
    importlib.invalidate_caches()


# ---------------------------------------------------------------------------
# servidor unico: API em /api e front buildado no resto
# ---------------------------------------------------------------------------

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
    for _ in range(100):  # ate ~10s (o Uvicorn demora um pouco mais que o http.server)
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

    # So importa o back depois de garantir as dependencias
    import uvicorn

    from backend.app.bootstrap import criar_app

    app = criar_app()
    url = f"http://{HOST}:{PORT}"
    if os.environ.get("NO_BROWSER") != "1":
        threading.Thread(
            target=_open_browser_when_ready, args=(url,), daemon=True
        ).start()

    print(f"[main.py] Servindo em {url}  (API em {url}/api, documentacao em {url}/docs). "
          "Ctrl+C para parar.")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("[main.py] Use Python 3.10 ou mais novo (o projeto usa o 3.14).")
    ensure_frontend_build()
    ensure_backend_deps()
    serve()


if __name__ == "__main__":
    main()
