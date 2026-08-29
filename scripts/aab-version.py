#!/usr/bin/env python3
"""Read versionCode/versionName back out of a release AAB and check them.

    python3 scripts/aab-version.py [path/to/app-release.aab]

Why this exists: an AAB stores `base/manifest/AndroidManifest.xml` in aapt2's
*protobuf* encoding, not the binary XML that `aapt2 dump xmltree` reads. Pointed
at a bundle it prints nothing and exits 0 — it does not fail, it just says
nothing, which is how PLAN.md 3a shipped a signed artifact carrying versionCode
1 without noticing. So the readback has to decode protobuf, and it has to assert
rather than print.

Exits non-zero if the bundle's versionCode disagrees with `git rev-list --count
HEAD`, which is where app/build.gradle.kts derives it from.
"""

import subprocess
import sys
import zipfile

# Field numbers from aapt2's Resources.proto (XmlNode / XmlElement / XmlAttribute).
# Hard-coded rather than generated: three numbers beat a protoc dependency in a
# script whose whole job is to have no moving parts.
NODE_ELEMENT = 1
ELEM_ATTRIBUTE = 4
ATTR_NAME, ATTR_VALUE, ATTR_COMPILED = 2, 3, 5

WANTED = ("package", "versionCode", "versionName")


def read_varint(buf, i):
    shift = result = 0
    while True:
        byte = buf[i]
        i += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, i
        shift += 7


def fields(buf):
    """Yield (field_number, payload) pairs for one protobuf message.

    Length-delimited payloads come back as bytes (a nested message or a string);
    everything else comes back as an int.
    """
    i = 0
    while i < len(buf):
        key, i = read_varint(buf, i)
        number, wire = key >> 3, key & 7
        if wire == 0:
            value, i = read_varint(buf, i)
            yield number, value
        elif wire == 1:
            yield number, int.from_bytes(buf[i:i + 8], "little")
            i += 8
        elif wire == 2:
            length, i = read_varint(buf, i)
            yield number, buf[i:i + length]
            i += length
        elif wire == 5:
            yield number, int.from_bytes(buf[i:i + 4], "little")
            i += 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire}")


def first_scalar(payload):
    """Unwrap a compiled Item down to the number inside it.

    An integer attribute arrives as Item -> Primitive -> int_decimal_value, and
    the exact nesting is not worth pinning down when the first scalar reached is
    always the value.
    """
    if isinstance(payload, int):
        return payload
    try:
        for _, nested in fields(payload):
            found = first_scalar(nested)
            if found is not None:
                return found
    except (ValueError, IndexError):
        # A compiled *string* item is bytes that happen not to be a message we
        # can walk. Not an error — that attribute simply has no number in it.
        return None
    return None


def manifest_attributes(blob):
    root = next((p for n, p in fields(blob) if n == NODE_ELEMENT), None)
    if root is None:
        sys.exit("no root element in base/manifest/AndroidManifest.xml")

    attrs = {}
    for number, payload in fields(root):
        if number != ELEM_ATTRIBUTE:
            continue
        name = raw = compiled = None
        for anumber, apayload in fields(payload):
            if anumber == ATTR_NAME:
                name = apayload.decode()
            elif anumber == ATTR_VALUE:
                raw = apayload.decode()
            elif anumber == ATTR_COMPILED:
                compiled = first_scalar(apayload)
        if name:
            attrs[name] = raw if raw else compiled
    return attrs


def git_version_code():
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip()) if result.returncode == 0 else None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "app/build/outputs/bundle/release/app-release.aab"
    try:
        with zipfile.ZipFile(path) as bundle:
            blob = bundle.read("base/manifest/AndroidManifest.xml")
    except FileNotFoundError:
        sys.exit(f"no such bundle: {path}\nRun ./gradlew bundleRelease first.")
    except KeyError:
        sys.exit(f"{path} has no base/manifest/AndroidManifest.xml — is it an AAB?")

    attrs = manifest_attributes(blob)
    for key in WANTED:
        print(f"{key:12} {attrs.get(key, '(absent)')}")

    expected = git_version_code()
    if expected is None:
        print("\nno git history here, so versionCode cannot be checked", file=sys.stderr)
        return 0

    # versionCode comes back as the raw string "133"; compare as numbers, or
    # "133" != 133 is true and the check passes nothing while looking like it did.
    raw_code = attrs.get("versionCode")
    found = int(raw_code) if raw_code is not None and str(raw_code).isdigit() else raw_code

    if found != expected:
        print(
            f"\nMISMATCH: bundle carries versionCode {found}, "
            f"git rev-list --count HEAD says {expected}.\n"
            "Do not upload this artifact.",
            file=sys.stderr,
        )
        return 1

    print(f"\nversionCode {found} matches git rev-list --count HEAD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
