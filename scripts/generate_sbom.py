"""Generate a file-level CycloneDX SBOM from an actual release ZIP or directory."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
from uuid import uuid5, NAMESPACE_URL
import zipfile


def files_in_artifact(artifact: Path, output: Path):
    if artifact.is_file() and zipfile.is_zipfile(artifact):
        with zipfile.ZipFile(artifact) as archive:
            seen = set()
            for info in archive.infolist():
                if info.is_dir(): continue
                name = PurePosixPath(info.filename)
                if name.is_absolute() or ".." in name.parts or info.filename in seen:
                    raise ValueError(f"unsafe or duplicate artifact path: {info.filename}")
                seen.add(info.filename)
                yield info.filename, archive.read(info), info.file_size
    elif artifact.is_dir():
        for path in sorted(artifact.rglob("*")):
            if path.is_symlink(): raise ValueError(f"symlink in artifact: {path}")
            if path.is_file() and path.resolve() != output.resolve():
                yield path.relative_to(artifact).as_posix(), path.read_bytes(), path.stat().st_size
    else:
        raise ValueError("artifact must be an existing ZIP or directory")


def build(artifact: Path, output: Path):
    components = []
    for name, data, size in files_in_artifact(artifact, output):
        components.append({"type": "file", "name": name,
                           "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(data).hexdigest()}],
                           "properties": [{"name": "template:file-size", "value": str(size)}]})
    components.sort(key=lambda item: item["name"])
    if not components: raise ValueError("artifact has no files")
    fingerprint = hashlib.sha256(json.dumps(components, sort_keys=True).encode()).hexdigest()
    artifact_component = {"type": "application", "name": artifact.name}
    if artifact.is_file():
        artifact_component["hashes"] = [{"alg": "SHA-256", "content": hashlib.sha256(artifact.read_bytes()).hexdigest()}]
    return {"bomFormat": "CycloneDX", "specVersion": "1.6",
            "serialNumber": f"urn:uuid:{uuid5(NAMESPACE_URL, fingerprint)}", "version": 1,
            "metadata": {"timestamp": datetime.now(timezone.utc).isoformat(),
                         "component": artifact_component},
            "components": components}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("--artifact", type=Path, required=True)
    a = p.parse_args(argv)
    try: bom = build(a.artifact, a.output)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"ERROR {exc}")
        return 2
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(bom, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"FILES={len(bom['components'])} OUTPUT={a.output}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
