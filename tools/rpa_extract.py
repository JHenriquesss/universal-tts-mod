"""
Le e extrai arquivos de um .rpa no formato RPA-3.0 (Ren'Py 8).

A implementacao segue o leitor do proprio runtime do jogo
(renpy/loader.py -> RPAv3ArchiveHandler): o indice fica no fim do arquivo,
comprimido com zlib e serializado com pickle, e cada entrada tem os
offsets embaralhados por XOR com a chave do cabecalho.

Ferramentas que leem o jogo instalado (`tools/rpyc_extract.py`) so acham
scripts .rpyc soltos na pasta game/. Em jogos Ren'Py 8 distribuidos, os
scripts costumam ficar dentro de `game/scripts.rpa`, entao este leitor abre
o arquivo e devolve os .rpy/.rpyc para inspecao e extracao.

Uso:
    python tools/rpa_extract.py list "D:\\Jogo\\game\\scripts.rpa"
    python tools/rpa_extract.py extract "D:\\Jogo\\game\\scripts.rpa" "D:\\out\\game" ".rpy,.rpyc"
"""
import os
import pickle
import sys
import zlib

HEADER = b"RPA-3.0 "


def read_index(path):
    """Indice do .rpa com os offsets ja desembaralhados."""
    with open(path, "rb") as handle:
        header = handle.read(40)
        if not header.startswith(HEADER):
            raise ValueError("formato .rpa nao suportado: {}".format(path))
        index_offset = int(header[8:24], 16)
        key = int(header[25:33], 16)
        handle.seek(index_offset)
        index = pickle.loads(zlib.decompress(handle.read()))

    resolved = {}
    for name, entries in index.items():
        items = []
        for entry in entries:
            if len(entry) == 2:
                offset, length = entry
                start = b""
            else:
                offset, length, start = entry
                if isinstance(start, str):
                    start = start.encode("latin-1")
            items.append((offset ^ key, length ^ key, start))
        resolved[name] = items
    return resolved


def entry_size(items):
    return sum(length + len(start) for _offset, length, start in items)


def list_archive(path):
    """(nome, tamanho em bytes, numero de blocos) de cada arquivo do .rpa."""
    rows = []
    for name, items in read_index(path).items():
        if isinstance(name, bytes):
            name = name.decode("utf-8", "replace")
        rows.append((name, entry_size(items), len(items)))
    rows.sort()
    return rows


def extract_archive(path, out_dir, extensions=None):
    """Extrai os arquivos do .rpa em out_dir, preservando os caminhos."""
    written = []
    with open(path, "rb") as handle:
        for name, items in read_index(path).items():
            if isinstance(name, bytes):
                name = name.decode("utf-8", "replace")
            if extensions and not name.lower().endswith(tuple(extensions)):
                continue
            target = os.path.join(out_dir, *name.split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as out:
                for offset, length, start in items:
                    if start:
                        out.write(start)
                    handle.seek(offset)
                    out.write(handle.read(length))
            written.append((name, os.path.getsize(target)))
    return written


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2

    mode, path = argv[0], argv[1]
    if mode == "list":
        rows = list_archive(path)
        for name, size, chunks in rows:
            print("{:>12}  {:>3}  {}".format(size, chunks, name))
        print("--- total: {} entradas".format(len(rows)))
        return 0

    if mode == "extract":
        if len(argv) < 3:
            print("uso: rpa_extract.py extract <arquivo.rpa> <destino> [exts]")
            return 2
        out_dir = argv[2]
        extensions = None
        if len(argv) > 3 and argv[3]:
            extensions = tuple(ext.lower() for ext in argv[3].split(","))
        written = extract_archive(path, out_dir, extensions)
        for name, size in sorted(written):
            print("{:>12}  {}".format(size, name))
        print("--- extraidos: {} arquivos".format(len(written)))
        return 0

    print("modo desconhecido: {}".format(mode))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
