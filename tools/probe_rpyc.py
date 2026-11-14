import io
import pickle
import struct
import sys
import zlib

HEADER = b"RENPY RPC2"


def read_slots(path):
    with open(path, "rb") as f:
        header_data = f.read(1024)
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


class Stub(object):
    def __init__(self, *a, **kw):
        pass

    def __setstate__(self, state):
        if isinstance(state, dict):
            self.__dict__.update(state)
        else:
            self._state = state

    def __repr__(self):
        return "<%s %r>" % (type(self).__name__, self.__dict__)


class PermissiveUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        try:
            return super().find_class(module, name)
        except Exception:
            return type(name, (Stub,), {})


def walk(obj, depth=0, seen=None, out=None):
    if seen is None:
        seen = set()
        out = []
    if depth > 12:
        return out
    oid = id(obj)
    if oid in seen:
        return out
    seen.add(oid)
    if isinstance(obj, Stub):
        d = obj.__dict__
        out.append((depth, type(obj).__name__, {k: v for k, v in d.items() if not k.startswith("_") and k != "parent"}))
        for k, v in d.items():
            if k in ("parent", "filename"):
                continue
            walk(v, depth + 1, seen, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            walk(v, depth + 1, seen, out)
    elif isinstance(obj, dict):
        for v in obj.values():
            walk(v, depth + 1, seen, out)
    return out


if __name__ == "__main__":
    path = sys.argv[1]
    slots = read_slots(path)
    print("slots:", {k: len(v) for k, v in slots.items()})
    data = slots[1]
    print("slot1 head:", data[:60])
    obj = PermissiveUnpickler(io.BytesIO(data)).load()
    print("root type:", type(obj).__name__)
    nodes = walk(obj)
    print("nodes:", len(nodes))
    for depth, name, attrs in nodes[:80]:
        print("  " * depth, name, list(attrs.keys())[:12])
