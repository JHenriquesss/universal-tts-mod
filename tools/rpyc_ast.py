"""
Extrai dados do AST compilado de um jogo Ren'Py 8 (arquivos .rpyc / RPC2).

Os jogos Ren'Py 8 so distribuiem .rpyc compilado. O slot 2 do arquivo guarda o
AST (estrutura de nos) e o slot 1 guarda os metadados. Como o proprio jogo
embute um Python 3.9 com o pacote `renpy`, dá para carregar os nos reais do
AST e extrair personagens, falas e menus sem depender de fonte .rpy.
"""
import io
import os
import pickle
import struct
import sys
import types
import zlib

HEADER = b"RENPY RPC2"


class _AutoMeta(type):
    """Metaclasse: qualquer atributo de classe vira a propria classe stub."""

    def __getattr__(cls, item):
        if item.startswith("__"):
            raise AttributeError(item)
        return cls

    def __iter__(cls):
        return iter(())

    def __len__(cls):
        return 0


class _Auto(object, metaclass=_AutoMeta):
    """
    Stub generico do runtime do Ren'Py.

    Serve como classe (para `class X(renpy.ui.Addable)`) e como instancia
    (para `renpy.config.layers`), sem exigir o runtime completo do jogo.
    """

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, item):
        if item.startswith("__"):
            raise AttributeError(item)
        return _Auto()

    def __call__(self, *args, **kwargs):
        return _Auto()

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 0

    def __bool__(self):
        return False

    def __repr__(self):
        return "<auto stub>"


class _AutoModule(types.ModuleType):
    def __getattr__(self, item):
        if item.startswith("__"):
            raise AttributeError(item)
        value = _Auto
        setattr(self, item, value)
        return value


def bootstrap_renpy(game_root):
    """Cria um pacote `renpy` falso para importar os modulos reais do jogo."""
    import importlib

    pkg = types.ModuleType("renpy")
    pkg.__path__ = [os.path.join(game_root, "renpy")]
    pkg.update_path = lambda *a, **kw: None

    # PEP 562: qualquer `renpy.<algo>` desconhecido vira um stub generico, o
    # que evita perseguir uma a uma as dependencias do runtime completo.
    def _renpy_getattr(name):
        if name.startswith("__"):
            raise AttributeError(name)
        value = _Auto
        setattr(pkg, name, value)
        return value

    pkg.__getattr__ = _renpy_getattr
    sys.modules["renpy"] = pkg

    # `renpy/__init__.py` so funciona dentro do launcher do Ren'Py, entao os
    # submodulos sao importados um a um e publicados no pacote falso.
    for name in ("revertable", "object", "compat", "scriptedit", "ast"):
        module = importlib.import_module("renpy.{}".format(name))
        setattr(pkg, name, module)

    # `renpy.ast` consulta `renpy.game.script` ao desserializar blocos python.
    script = types.SimpleNamespace(
        record_pycode=False,
        all_pycode=[],
        all_pyexpr=None,
    )
    pkg.game = types.SimpleNamespace(script=script)
    pkg.game.log = types.SimpleNamespace(mutated={})
    pkg.game.post_init = []
    pkg.game.context = lambda *args, **kwargs: _Auto()

    # `renpy.config` e consultado por `renpy.revertable` na criacao de classes.
    config = _AutoModule("renpy.config")
    config.developer = ""
    pkg.config = config
    sys.modules["renpy.config"] = config

    # `renpy.log` redireciona o stdout e cria o arquivo "log" no diretorio
    # atual, o que nao serve para uma extracao offline.
    log = _AutoModule("renpy.log")
    pkg.log = log
    sys.modules["renpy.log"] = log

    # `renpy.ios` indica execucao em iOS e e consultado por `renpy.log`.
    pkg.ios = False

    # Flags de plataforma consultadas em tempo de importacao pelo runtime.
    for flag in ("emscripten", "macapp", "android", "web", "wii", "switch",
                 "ps4", "xbox", "sdl2", "steam", "lang_translations"):
        setattr(pkg, flag, False)

    # `renpy.display.displayable` cria um Style padrao em tempo de importacao.
    # Um stub generico basta: para o unpickle do AST das telas so importa que
    # as classes existam.
    class _Style(object):
        def __init__(self, *args, **kwargs):
            pass

        def __getattr__(self, item):
            return _Style()

    style = _AutoModule("renpy.style")
    style.Style = _Style
    pkg.style = style
    sys.modules["renpy.style"] = style

    # Os pacotes reais do runtime sao tornados permissivos: assim
    # `renpy.display.behavior` e afins resolvem sem ser importados um a um.
    def _make_permissive(module):
        def getattr_(name):
            if name.startswith("__"):
                raise AttributeError(name)
            return _Auto

        module.__getattr__ = getattr_
        return module

    for package_name in ("renpy.display", "renpy.sl2", "renpy.ui"):
        try:
            module = importlib.import_module(package_name)
            _make_permissive(module)
            setattr(pkg, package_name.split(".")[-1], module)
        except Exception:
            pass

    # `renpy.display.core` e importado antes de `renpy.display.layout`, que o
    # usa em tempo de importacao.
    try:
        display_core = importlib.import_module("renpy.display.core")
        pkg.display_core = display_core
    except Exception:
        pass

    return pkg


def read_slots(path):
    """Le os slots comprimidos de um .rpyc v2 (RPC2)."""
    with open(path, "rb") as f:
        header_data = f.read(1024)
        if header_data[:len(HEADER)] != HEADER:
            raise ValueError("formato .rpyc nao suportado: {}".format(path))
        pos = len(HEADER)
        slots = {}
        while True:
            slot, start, length = struct.unpack("III", header_data[pos:pos + 12])
            if slot == 0:
                break
            f.seek(start)
            slots[slot] = zlib.decompress(f.read(length))
            pos += 12
    return slots


def load_ast(path):
    """Retorna a lista de nos do AST gravada no slot 2."""
    slots = read_slots(path)
    data = slots.get(2)
    if data is None:
        raise ValueError("slot 2 (AST) ausente em {}".format(path))
    payload = pickle.loads(data)
    # O payload e a tupla `(metadados, nos)`.
    if isinstance(payload, tuple) and len(payload) == 2:
        return payload[1]
    return payload


def iter_nodes(stmts):
    """Percorre nos e filhos, tolerando a API variavel entre versoes do Ren'Py."""
    stack = list(stmts or [])
    seen = set()
    while stack:
        node = stack.pop()
        if node is None or id(node) in seen:
            continue
        seen.add(id(node))
        yield node
        children = getattr(node, "all_children", None)
        if callable(children):
            try:
                stack.extend(children())
                continue
            except Exception:
                pass
        for attr in ("next", "block", "body", "stmts", "statements"):
            value = getattr(node, attr, None)
            if isinstance(value, (list, tuple)):
                stack.extend(value)


def node_kind(node):
    return type(node).__name__


if __name__ == "__main__":
    game_root = sys.argv[1]
    rpyc = sys.argv[2]
    bootstrap_renpy(game_root)
    stmts = load_ast(rpyc)
    print("root stmts:", len(stmts))
    kinds = {}
    for node in iter_nodes(stmts):
        kinds[node_kind(node)] = kinds.get(node_kind(node), 0) + 1
    for kind, count in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print("  {:<28} {}".format(kind, count))
