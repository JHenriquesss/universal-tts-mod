from __future__ import annotations

import pathlib
import re
import struct
import sys

import pefile


PATTERN = re.compile(
    rb"\x8b\x74\x24\x20\xe9....\x3c\x23\x0f\x85....",
    re.DOTALL,
)


def main() -> int:
    exe = pathlib.Path(sys.argv[1])
    data = exe.read_bytes()
    pe = pefile.PE(data=data, fast_load=True)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    text = next(
        section
        for section in pe.sections
        if section.Name.rstrip(b"\0") == b".text"
    )
    raw_start = text.PointerToRawData
    blob = data[raw_start : raw_start + text.SizeOfRawData]
    matches = list(PATTERN.finditer(blob))
    print(f"matches={len(matches)}")
    for match in matches:
        file_offset = raw_start + match.start()
        block_va = image_base + text.VirtualAddress + match.start()
        hook_va = block_va + 11
        relative = struct.unpack_from("<i", data, file_offset + 13)[0]
        jne_target = block_va + 17 + relative
        matched = data[file_offset : file_offset + 17]
        print(
            f"block=0x{block_va:08X} hook=0x{hook_va:08X} "
            f"jne_target=0x{jne_target:08X} bytes={matched.hex(' ')}"
        )
    return 0 if len(matches) == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
