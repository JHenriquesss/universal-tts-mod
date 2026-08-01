import argparse
import os
import zipfile
from dataclasses import dataclass

from install_tts_mod import MOD_DIR, REQUIRED_GAME_FILES, ROOT_HELPER_FILES


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PACKAGE_NAME = "renpy-tts-mod"
RELEASE_VERSION = "1.0.0"


@dataclass(frozen=True)
class ReleaseEntry:
    source: str
    destination: str


@dataclass(frozen=True)
class ManifestValidationResult:
    ok: bool
    message: str
    missing: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReleaseArchiveResult:
    archive_path: str
    entries: tuple[ReleaseEntry, ...]


def build_release_manifest():
    entries = []
    for filename in REQUIRED_GAME_FILES:
        entries.append(ReleaseEntry(os.path.join("renpy_mod", filename), os.path.join("game", filename)))
    for filename in ROOT_HELPER_FILES:
        entries.append(ReleaseEntry(os.path.join("renpy_mod", filename), filename))
    return entries


def validate_release_manifest(entries=None):
    entries = build_release_manifest() if entries is None else entries
    missing = []
    for entry in entries:
        source_path = os.path.join(PROJECT_ROOT, entry.source)
        if not os.path.exists(source_path):
            missing.append(entry.source)
    if missing:
        return ManifestValidationResult(False, "missing release source files", tuple(missing))
    return ManifestValidationResult(True, "release manifest check passed")


def default_archive_path(output_dir=None):
    output_dir = os.getcwd() if output_dir is None else output_dir
    return os.path.abspath(os.path.join(output_dir, "{}-{}.zip".format(PACKAGE_NAME, RELEASE_VERSION)))


def build_release_archive(output_path=None, entries=None):
    output_path = default_archive_path() if output_path is None else os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    if not os.path.isdir(output_dir):
        raise ValueError("Archive output parent does not exist: {}".format(output_dir))

    entries = tuple(build_release_manifest() if entries is None else entries)
    result = validate_release_manifest(entries)
    if not result.ok:
        raise ValueError(result.message + ": " + ", ".join(result.missing))

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in entries:
            source_path = os.path.join(PROJECT_ROOT, entry.source)
            archive.write(source_path, entry.destination.replace(os.sep, "/"))
    return ReleaseArchiveResult(output_path, entries)


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Check the TTS-only release manifest without writing files.")
    parser.add_argument("--check", action="store_true", help="Verify that every manifest source exists.")
    parser.add_argument(
        "--archive",
        nargs="?",
        const="",
        help="Build a TTS-only release zip. Omit the value to use the default versioned filename.",
    )
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    entries = build_release_manifest()
    if args.archive is not None:
        result = build_release_archive(args.archive or None, entries)
        print("created: {}".format(result.archive_path))
        return 0
    if args.check:
        result = validate_release_manifest(entries)
        print(result.message)
        for missing in result.missing:
            print("missing: {}".format(missing))
        return 0 if result.ok else 1

    for entry in entries:
        print("{} -> {}".format(entry.source, entry.destination))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
