"""
Quick Click: lancador unico do sistema (front + back).

Uso:
    python main.py               # prepara o que faltar e sobe tudo em http://127.0.0.1:8080
    REBUILD=1 python main.py     # forca o build do front (PowerShell: $env:REBUILD=1; python main.py)
    NO_BROWSER=1 python main.py  # nao abre o navegador (util em testes automaticos)

No PyCharm: Run 'main'. A configuracao fica no projeto, em .run/main.run.xml, e usa
o Python da .venv (.venv/Scripts/python.exe), mesmo que o interpretador do projeto
esteja errado.

O que ele faz, em ordem:
    0. Mostra o Python em uso. Se existir a .venv do projeto e este arquivo estiver
       rodando com outro Python, relanca com o Python da .venv (avisando no console).
       Se a porta 8080 ja for do proprio Quick Click (o /api/health responde), avisa
       que ele ja esta rodando e so abre o navegador.
    1. Front (frontend/): acha o npm no PATH ou, se o PyCharm foi aberto antes de
       instalar o Node, nas pastas comuns do Windows (Arquivos de Programas\\nodejs,
       AppData\\Local\\Programs\\nodejs, link do nvm e o PATH atual do registro).
       Mostra o Node e o npm em uso e confere se o Node e' 18 ou mais novo.
       Roda `npm ci` se faltar frontend/node_modules ou se o package-lock.json for
       mais novo que ele, e `npm run build` se frontend/dist estiver ausente,
       desatualizado ou com REBUILD=1.
    2. Back (backend/): instala com pip o que faltar de backend/requirements.txt
       no mesmo Python que esta rodando este arquivo (a .venv, quando ela existe).
       Se na hora de subir o servidor ainda faltar alguma peca (uma dependencia de
       dependencia, ou uma instalacao que ficou pela metade), ele roda o
       requirements de novo sozinho e tenta mais uma vez, antes de desistir.
    3. Sobe um unico servidor (Uvicorn) em http://127.0.0.1:8080:
       a API em /api (documentacao automatica em /docs) e o front buildado no resto.
    4. Abre o navegador padrao.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"
NODE_MODULES = FRONTEND / "node_modules"
PACKAGE_LOCK = FRONTEND / "package-lock.json"
REQUIREMENTS = ROOT / "backend" / "requirements.txt"
VENV = ROOT / ".venv"
PORT = 8080
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}"
NODE_MINIMO = 18
FOLGA_DO_LOCK_S = 5  # segundos entre o package-lock.json e a instalacao que ainda contam como em dia
RELANCADO = "QUICKCLICK_RELANCADO"  # marca o processo relancado com a .venv (evita laco)


# ---------------------------------------------------------------------------
# python: a .venv do projeto
# ---------------------------------------------------------------------------

def _venv_python() -> Path | None:
    """Python da .venv do projeto, se ela existir (Windows ou Linux e macOS)."""
    for candidate in (VENV / "Scripts" / "python.exe", VENV / "bin" / "python"):
        if candidate.is_file():
            return candidate
    return None


def _running_in_venv() -> bool:
    """True se este processo roda com a .venv do projeto."""
    try:
        return os.path.normcase(Path(sys.prefix).resolve()) == os.path.normcase(VENV.resolve())
    except OSError:
        return False


def ensure_venv_python() -> None:
    """Se existe a .venv e este arquivo roda com outro Python, relanca com o da .venv."""
    venv_python = _venv_python()
    if venv_python is None or _running_in_venv():
        return
    if os.environ.get(RELANCADO) == "1":
        print(f"[main.py] Aviso: a .venv nao assumiu; seguindo com {sys.executable}")
        return

    print(f"[main.py] Este Python ({sys.executable}) nao e' o da .venv do projeto.")
    print(f"[main.py] Relancando com {venv_python}", flush=True)
    env = dict(os.environ, **{RELANCADO: "1"})
    proc = subprocess.Popen([str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]],
                            cwd=ROOT, env=env)
    try:
        code = proc.wait()
    except KeyboardInterrupt:
        # No terminal o Ctrl+C chega aos dois processos: espera o da .venv encerrar.
        try:
            code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            code = proc.wait()
    raise SystemExit(code)


def describe_python() -> None:
    origem = ".venv do projeto" if _running_in_venv() else "fora da .venv"
    print(f"[main.py] Python {sys.version.split()[0]} em {sys.executable} ({origem})")
    if _venv_python() is None:
        print("[main.py] Dica: sem .venv, as dependencias do back vao para este Python. "
              "Para isolar o projeto: py -3.14 -m venv .venv (veja o README).")


# ---------------------------------------------------------------------------
# servidor ja rodando?
# ---------------------------------------------------------------------------

def _quickclick_is_running() -> bool:
    """True se o /api/health de 127.0.0.1:8080 responde como o Quick Click."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # nada de proxy
    try:
        with opener.open(f"{URL}/api/health", timeout=2) as resposta:
            corpo = json.loads(resposta.read().decode("utf-8"))
            return resposta.status == 200 and corpo == {"status": "ok"}
    except (OSError, ValueError):
        return False


def _already_running() -> None:
    print(f"[main.py] O Quick Click ja esta rodando em {URL}: nao vou subir outro.")
    if os.environ.get("NO_BROWSER") != "1":
        print("[main.py] Abrindo o navegador.")
        try:
            webbrowser.open(URL)
        except Exception:  # navegador nao disponivel nao e' fatal
            pass


# ---------------------------------------------------------------------------
# front: node, npm e build
# ---------------------------------------------------------------------------

def _registry_env(name: str) -> str | None:
    """Variavel de ambiente atual do Windows (registro do usuario, depois do sistema).

    Um programa instalado depois de abrir o PyCharm atualiza o registro, mas nao o
    ambiente do PyCharm, que so muda quando ele e' reaberto.
    """
    if os.name != "nt":
        return None
    import winreg

    chaves = (
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    )
    valores = []
    for raiz, caminho in chaves:
        try:
            with winreg.OpenKey(raiz, caminho) as chave:
                valores.append(str(winreg.QueryValueEx(chave, name)[0]))
        except OSError:
            continue
    return os.pathsep.join(valores) if valores else None


def _common_node_dirs() -> list[Path]:
    """Pastas onde o Node costuma estar quando ele nao esta no PATH deste processo."""
    env = os.environ.get
    nvm_link = env("NVM_SYMLINK") or _registry_env("NVM_SYMLINK")
    pastas = [
        nvm_link,                                                    # nvm-windows
        env("ProgramFiles") and os.path.join(env("ProgramFiles"), "nodejs"),
        env("ProgramFiles(x86)") and os.path.join(env("ProgramFiles(x86)"), "nodejs"),
        env("LOCALAPPDATA") and os.path.join(env("LOCALAPPDATA"), "Programs", "nodejs"),
        "/usr/local/bin",
        "/opt/homebrew/bin",
    ]
    path_atual = _registry_env("Path") or ""
    pastas += os.path.expandvars(path_atual).split(os.pathsep)
    return [Path(p.strip()) for p in pastas if p and p.strip()]


def _find_npm() -> str:
    """Acha o npm no PATH ou, se nao estiver, nas pastas comuns do Node.

    Quando ele vem de fora do PATH, a pasta dele entra no PATH deste processo,
    para o `npm run build` (e o Node que ele chama) funcionarem tambem.
    """
    nomes = ("npm.cmd", "npm.bat", "npm") if os.name == "nt" else ("npm",)
    for nome in nomes:
        achado = shutil.which(nome)
        if achado:
            return achado

    for pasta in _common_node_dirs():
        for nome in nomes:
            candidato = pasta / nome
            if candidato.is_file():
                os.environ["PATH"] = str(pasta) + os.pathsep + os.environ.get("PATH", "")
                print(f"[main.py] O npm nao esta no PATH deste processo; usando o de {pasta}. "
                      "Reabra o PyCharm quando puder, para ele enxergar o Node.")
                return str(candidato)

    raise SystemExit(
        "[main.py] npm nao encontrado. Instale o Node.js LTS (https://nodejs.org ou, no "
        "Windows, winget install OpenJS.NodeJS.LTS) e depois feche e reabra o PyCharm "
        "(ou o terminal): um programa instalado com o PyCharm aberto so entra no PATH "
        "dele quando ele e' reaberto."
    )


def _version_of(executable: str) -> str:
    try:
        saida = subprocess.run([executable, "-v"], capture_output=True, text=True,
                               cwd=FRONTEND, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return "?"
    return saida.stdout.strip() or "?"


def check_node(npm: str) -> None:
    """Mostra o Node e o npm em uso e confere se o Node e' novo o bastante."""
    pasta = Path(npm).parent
    vizinhos = [pasta / "node.exe", pasta / "node"]
    node = next((str(p) for p in vizinhos if p.is_file()), None) or shutil.which("node")
    if node is None:
        raise SystemExit(
            f"[main.py] Achei o npm em {npm}, mas nao o node. Reinstale o Node.js LTS "
            "(https://nodejs.org) e reabra o PyCharm."
        )

    versao = _version_of(node)
    print(f"[main.py] Node {versao} em {node}")
    print(f"[main.py] npm {_version_of(npm)} em {npm}")

    numero = re.match(r"v?(\d+)", versao)
    if numero is None or int(numero.group(1)) < NODE_MINIMO:
        raise SystemExit(
            f"[main.py] O front (Vite 5) precisa do Node {NODE_MINIMO} ou mais novo e este e' o "
            f"{versao}. Instale o Node.js LTS (https://nodejs.org ou, no Windows, "
            "winget install OpenJS.NodeJS.LTS), feche e reabra o PyCharm e rode de novo."
        )


def _run_npm(npm: str, *args: str, check: bool = True) -> int:
    """Roda `npm <args>` dentro de frontend/ mostrando a saida; aborta se falhar."""
    cmd = [npm, *args]
    print(f"[main.py] $ {' '.join(cmd)}  (em frontend/)", flush=True)
    proc = subprocess.run(cmd, cwd=FRONTEND, shell=False)
    if check and proc.returncode != 0:
        raise SystemExit(
            f"[main.py] Falhou: '{' '.join(cmd)}' (exit {proc.returncode}). "
            "Corrija o erro acima e rode 'python main.py' de novo."
        )
    return proc.returncode


def _deps_reason() -> str | None:
    """Por que reinstalar o node_modules, ou None se ele esta em dia."""
    if not NODE_MODULES.is_dir():
        return "frontend/node_modules ausente"
    if not PACKAGE_LOCK.is_file():
        return None
    # O npm grava node_modules/.package-lock.json a cada instalacao. A folga cobre o
    # `npm install` feito a mao, que grava os dois arquivos quase ao mesmo tempo.
    marca = NODE_MODULES / ".package-lock.json"
    instalado = marca if marca.is_file() else NODE_MODULES
    if PACKAGE_LOCK.stat().st_mtime > instalado.stat().st_mtime + FOLGA_DO_LOCK_S:
        return "package-lock.json mais novo que o node_modules"
    return None


def ensure_frontend_deps(npm: str) -> None:
    motivo = _deps_reason()
    if motivo is None:
        return
    if PACKAGE_LOCK.is_file():
        print(f"[main.py] {motivo}: rodando npm ci")
        if _run_npm(npm, "ci", check=False) == 0:
            return
        print("[main.py] npm ci falhou; tentando npm install")
    else:
        print(f"[main.py] {motivo}: rodando npm install")
    _run_npm(npm, "install")


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


def ensure_frontend_build(npm: str) -> None:
    ensure_frontend_deps(npm)

    force = os.environ.get("REBUILD") == "1"
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


ERRO_PIP = (
    "[main.py] Falhou a instalacao das dependencias do back. Confira a internet e "
    "rode de novo. Se o pip recusar instalar no Python do sistema, crie uma .venv "
    "(py -3.14 -m venv .venv), escolha ela como interpretador no PyCharm e rode o "
    "main.py de novo."
)


def _pip_install_requirements() -> bool:
    """Roda o `pip install -r` no Python deste processo. True se o pip terminou bem."""
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    print(f"[main.py] $ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, shell=False)
    importlib.invalidate_caches()
    return proc.returncode == 0


def ensure_backend_deps() -> None:
    missing = [name for name in _required_packages() if not _is_installed(name)]
    if not missing:
        print("[main.py] dependencias do back ja instaladas")
        return

    print(f"[main.py] Instalando dependencias do back que faltam: {', '.join(missing)}")
    if not _pip_install_requirements():
        raise SystemExit(ERRO_PIP)


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


def _import_backend():
    """Importa o uvicorn e o criar_app do back."""
    import uvicorn

    from backend.app.bootstrap import criar_app

    return uvicorn, criar_app


def import_backend():
    """O mesmo, mas instalando o requirements e tentando de novo se faltar alguma peca.

    O ensure_backend_deps() confere so os nomes escritos no requirements. Uma
    dependencia dessas (pydantic, starlette, h11...) que falte, ou uma instalacao
    que ficou pela metade, aparece aqui, na hora de importar. Em vez de morrer com
    o ImportError, roda o requirements e tenta mais uma vez.
    """
    try:
        return _import_backend()
    except ImportError as erro:
        print(f"[main.py] Falta uma dependencia do back: {erro}")
        print("[main.py] Instalando o requirements e tentando de novo.", flush=True)
        if not _pip_install_requirements():
            raise SystemExit(ERRO_PIP)

    try:
        return _import_backend()
    except ImportError as erro:
        raise SystemExit(
            f"[main.py] Mesmo depois de instalar o requirements ainda falta algo para "
            f"subir o servidor: {erro}. Instale a mao e rode de novo:\n"
            f"    {sys.executable} -m pip install -r {REQUIREMENTS}"
        )


def serve() -> None:
    if not _port_is_free(HOST, PORT):
        if _quickclick_is_running():
            _already_running()
            return
        raise SystemExit(
            f"[main.py] A porta {PORT} ja esta em uso. Feche o outro processo "
            f"(ou identifique com `netstat -ano | findstr :{PORT}` no Windows) "
            f"e rode de novo. Nao vou trocar de porta silenciosamente."
        )

    # So importa o back depois de garantir as dependencias
    uvicorn, criar_app = import_backend()

    app = criar_app()
    if os.environ.get("NO_BROWSER") != "1":
        threading.Thread(
            target=_open_browser_when_ready, args=(URL,), daemon=True
        ).start()

    print(f"[main.py] Servindo em {URL}  (API em {URL}/api, documentacao em {URL}/docs). "
          "Ctrl+C para parar.")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    ensure_venv_python()
    if sys.version_info < (3, 11):
        raise SystemExit("[main.py] Use Python 3.11 ou mais novo (o projeto usa o 3.14).")
    describe_python()

    if _quickclick_is_running():
        _already_running()
        return

    npm = _find_npm()
    check_node(npm)
    ensure_frontend_build(npm)
    ensure_backend_deps()
    serve()


if __name__ == "__main__":
    main()
