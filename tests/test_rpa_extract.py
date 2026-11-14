import os
import pickle
import sys
import tempfile
import unittest
import zlib


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def build_rpa3_archive(entries, key=0x42424242):
    """Monta um .rpa RPA-3.0 sintetico: header, corpo dos arquivos e indice."""
    header_length = 34
    body = b""
    index = {}
    offset = header_length

    for name, data in entries:
        index[name] = [(offset ^ key, len(data) ^ key, b"")]
        body += data
        offset += len(data)

    index_offset = offset
    header = (
        b"RPA-3.0 "
        + ("%016x" % index_offset).encode("ascii")
        + b" "
        + ("%08x" % key).encode("ascii")
        + b"\n"
    )
    return header + body + zlib.compress(pickle.dumps(index))


class TestRpaExtract(unittest.TestCase):
    def test_list_archive_reports_names_and_sizes(self):
        from tools.rpa_extract import list_archive

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "scripts.rpa")
            with open(path, "wb") as handle:
                handle.write(build_rpa3_archive([
                    ("scripts/intro.rpy", b"label start:\n    pass\n"),
                    ("options.rpy", b"define config.name = 'x'\n"),
                ]))

            rows = list_archive(path)

        self.assertEqual(
            [("options.rpy", 25, 1), ("scripts/intro.rpy", 22, 1)],
            rows,
        )

    def test_extract_archive_writes_files_and_keeps_paths(self):
        from tools.rpa_extract import extract_archive

        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = os.path.join(tmpdir, "scripts.rpa")
            with open(archive_path, "wb") as handle:
                handle.write(build_rpa3_archive([
                    ("scripts/intro.rpy", b"label start:\n"),
                    ("options.rpy", b"define x = 1\n"),
                ]))

            out_dir = os.path.join(tmpdir, "out")
            written = extract_archive(archive_path, out_dir)

            self.assertEqual(2, len(written))
            with open(os.path.join(out_dir, "scripts", "intro.rpy"), "rb") as handle:
                self.assertEqual(b"label start:\n", handle.read())
            with open(os.path.join(out_dir, "options.rpy"), "rb") as handle:
                self.assertEqual(b"define x = 1\n", handle.read())

    def test_extract_archive_filters_by_extension(self):
        from tools.rpa_extract import extract_archive

        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = os.path.join(tmpdir, "scripts.rpa")
            with open(archive_path, "wb") as handle:
                handle.write(build_rpa3_archive([
                    ("scripts/intro.rpy", b"label start:\n"),
                    ("scripts/intro.rpyc", b"compiled"),
                    ("options.rpy", b"define x = 1\n"),
                ]))

            out_dir = os.path.join(tmpdir, "out")
            written = extract_archive(archive_path, out_dir, (".rpy",))

        self.assertEqual(
            ["options.rpy", "scripts/intro.rpy"],
            sorted(name for name, _size in written),
        )

    def test_extract_archive_keeps_prefix_bytes_of_split_entries(self):
        from tools.rpa_extract import extract_archive, read_index

        key = 0x42424242
        header_length = 34
        prefix = b"prefix:"
        payload = b"payload"
        body = payload
        index = {"split.rpy": [(header_length ^ key, len(payload) ^ key, prefix)]}
        index_blob = zlib.compress(pickle.dumps(index))
        header = (
            b"RPA-3.0 "
            + ("%016x" % (header_length + len(body))).encode("ascii")
            + b" "
            + ("%08x" % key).encode("ascii")
            + b"\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = os.path.join(tmpdir, "scripts.rpa")
            with open(archive_path, "wb") as handle:
                handle.write(header + body + index_blob)

            self.assertEqual(1, len(read_index(archive_path)))

            out_dir = os.path.join(tmpdir, "out")
            extract_archive(archive_path, out_dir)
            with open(os.path.join(out_dir, "split.rpy"), "rb") as handle:
                self.assertEqual(prefix + payload, handle.read())

    def test_read_index_rejects_unsupported_format(self):
        from tools.rpa_extract import read_index

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "old.rpa")
            with open(path, "wb") as handle:
                handle.write(b"RPA-2.0 " + b"0" * 32)

            with self.assertRaises(ValueError):
                read_index(path)


if __name__ == "__main__":
    unittest.main()
