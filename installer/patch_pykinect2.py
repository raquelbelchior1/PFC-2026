"""
patch_pykinect2.py — Aplica automaticamente os patches de compatibilidade
=========================================================================
O ``pykinect2`` 0.1.0 foi escrito para Python 2/3.6 e precisa de 5
correções para funcionar em Python 3.8+ / NumPy 1.24+ / comtypes 1.3.1
(detalhadas no README.md, seção "Solução de Problemas — pykinect2 +
Python 3.12").  Este script aplica todas de forma idempotente: pode ser
executado quantas vezes for necessário sem corromper os arquivos.

Uso (com o Python do venv onde o pykinect2 está instalado):

    python patch_pykinect2.py

Sai com código 0 se todos os patches estão aplicados (agora ou antes),
1 em caso de erro.
"""

import sys
from pathlib import Path


def _localizar_pykinect2() -> Path:
    try:
        import pykinect2  # noqa: F401
    except Exception:
        # O import de pykinect2/__init__.py pode falhar justamente pelos
        # bugs que vamos corrigir — localiza o pacote via importlib.
        import importlib.util

        spec = importlib.util.find_spec("pykinect2")
        if spec is None or not spec.submodule_search_locations:
            raise SystemExit(
                "ERRO: pacote 'pykinect2' nao encontrado neste ambiente Python."
            )
        return Path(list(spec.submodule_search_locations)[0])
    return Path(pykinect2.__file__).parent


def _aplicar(caminho: Path, substituicoes: list[tuple[str, str]]) -> list[str]:
    """Aplica pares (de, para) em ``caminho``; retorna o log de ações."""
    log: list[str] = []
    texto = caminho.read_text(encoding="utf-8", errors="replace")
    original = texto
    for de, para in substituicoes:
        # Quando ``para`` embute ``de`` (caso do try/except do patch 1),
        # a presença do bloco completo indica patch já aplicado — sem
        # essa checagem, reexecutar aninharia o try/except.
        if de in para:
            aplicado = para in texto
        else:
            aplicado = de not in texto and para in texto
        if aplicado:
            log.append(f"  [ja aplicado] {de.splitlines()[0][:60]}")
            continue
        if de not in texto:
            log.append(f"  [AVISO] padrao nao encontrado: {de.splitlines()[0][:60]}")
            continue
        texto = texto.replace(de, para)
        log.append(f"  [corrigido] {de.splitlines()[0][:60]}")
    if texto != original:
        backup = caminho.with_suffix(caminho.suffix + ".orig")
        if not backup.exists():
            backup.write_text(original, encoding="utf-8")
        caminho.write_text(texto, encoding="utf-8")
    return log


def main() -> int:
    pasta = _localizar_pykinect2()
    print(f"pykinect2 localizado em: {pasta}")

    v2 = pasta / "PyKinectV2.py"
    runtime = pasta / "PyKinectRuntime.py"
    if not v2.exists() or not runtime.exists():
        print("ERRO: PyKinectV2.py / PyKinectRuntime.py nao encontrados.")
        return 1

    # --- PyKinectV2.py: 3 correções -------------------------------------
    print("PyKinectV2.py:")
    for linha in _aplicar(
        v2,
        [
            # 1. numpy.distutils removido no NumPy >= 1.26/2.0
            (
                "import numpy.distutils.system_info as sysinfo",
                "try:\n"
                "    import numpy.distutils.system_info as sysinfo\n"
                "except ImportError:\n"
                "    class sysinfo:\n"
                "        platform_bits = 64",
            ),
            # 2. sizeof(tagSTATSTG) e 80 no Python 3.8+ 64-bit.  A copia do
            #    GitHub usa "required_size"; a wheel do PyPI traz 72 fixo.
            (
                "assert sizeof(tagSTATSTG) == required_size, sizeof(tagSTATSTG)",
                "assert sizeof(tagSTATSTG) == 80, sizeof(tagSTATSTG)",
            ),
            (
                "assert sizeof(tagSTATSTG) == 72, sizeof(tagSTATSTG)",
                "assert sizeof(tagSTATSTG) == 80, sizeof(tagSTATSTG)",
            ),
            # 3. _check_version incompatível com comtypes 1.3.1
            (
                "from comtypes import _check_version; _check_version('')",
                "# from comtypes import _check_version; _check_version('')",
            ),
        ],
    ):
        print(linha)

    # --- PyKinectRuntime.py: 2 correções --------------------------------
    print("PyKinectRuntime.py:")
    for linha in _aplicar(
        runtime,
        [
            # 4. time.clock() removido no Python 3.8
            ("time.clock()", "time.perf_counter()"),
            # 5. numpy.object removido no NumPy 1.24
            ("dtype=numpy.object", "dtype=object"),
        ],
    ):
        print(linha)

    # Validação final: os padrões antigos não podem mais existir.
    problemas = []
    texto_v2 = v2.read_text(encoding="utf-8", errors="replace")
    texto_rt = runtime.read_text(encoding="utf-8", errors="replace")
    if (
        "assert sizeof(tagSTATSTG) == required_size" in texto_v2
        or "assert sizeof(tagSTATSTG) == 72" in texto_v2
    ):
        problemas.append("PyKinectV2.py: sizeof(tagSTATSTG) nao corrigido")
    if "\nfrom comtypes import _check_version" in texto_v2:
        problemas.append("PyKinectV2.py: _check_version nao comentado")
    if "time.clock()" in texto_rt:
        problemas.append("PyKinectRuntime.py: time.clock() remanescente")
    if "dtype=numpy.object" in texto_rt:
        problemas.append("PyKinectRuntime.py: dtype=numpy.object remanescente")

    if problemas:
        print("ERRO: patches incompletos:")
        for p in problemas:
            print(f"  - {p}")
        return 1

    print("OK: todos os patches do pykinect2 aplicados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
