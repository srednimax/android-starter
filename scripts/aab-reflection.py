#!/usr/bin/env python3
"""Assert every class the manifest names for reflection is still in the dex, with its constructor.

    python3 scripts/aab-reflection.py [path/to/app-release.aab]

Why this exists: at 10c, turning R8 on **silently disabled the guided document
scanner**, and every check this repo had passed the artifact. It did not crash —
`MlKitDocumentScanner` catches everything and falls back to the plain camera by
design, so the failure looked exactly like a device without Play services. The
cause was `NoSuchMethodException: CommonComponentRegistrar.<init> []`: ML Kit
names its registrar inside an `<meta-data>` **key**, `aapt_rules.txt` reads
attributes and not meta-data keys, so R8 saw a class nobody constructs and shrank
the no-arg constructor away while keeping the class.

That is the shape of the hazard: a class named only in the manifest, loaded by
`Class.forName` and built with a no-arg constructor, where losing it costs a
feature rather than raising anything at build time. `proguard-rules.pro` now
carries the keep rule, but a keep rule is a statement of intent — this reads the
artifact and checks the intent was met.

**What identifies one is the shape, not the class name.** All three frameworks
doing this here write `name` = the class to instantiate and `value` = who will
instantiate it, and two of them namespace the key — Firebase's registrar arrives
as `com.google.firebase.components:<class>`. So the markers live in MARKERS below
and the class names are read out of the artifact, rather than being kept in a
list here that would go stale on the next dependency bump.

**mapping.txt cannot answer this.** It rides inside the AAB, but R8 writes a bare
`Foo -> Foo:` line for a class it kept unrenamed and lists no members at all —
checked against this artifact, where `CommonComponentRegistrar` has exactly that
one line while its constructor is present in the dex. Absence from mapping.txt is
not absence from the artifact, so the dex is what gets read.

Exits non-zero if a named class is missing from the dex, or is there without a
public no-arg constructor.
"""

import struct
import sys
import zipfile

# The <meta-data> values that mean "the name attribute is a class I will construct
# reflectively". Each is here because this artifact carries it; adding a library
# that discovers classes its own way means adding its marker.
MARKERS = {
    "com.google.firebase.components.ComponentRegistrar": "Firebase component discovery — ML Kit's registrars",
    "androidx.startup": "androidx.startup — App Startup initializers",
    # Not a marker word like the two above but the backend's name, which is why this
    # one is matched on the key's `backend:` namespace instead. Same dependency chain
    # that merged INTERNET at 5g, discovered the same reflective way.
    "cct": "com.google.android.datatransport — a backend factory, built by name",
}

ACC_PUBLIC = 0x1

# dex header offsets, little-endian uint32 throughout. Hard-coded for the same
# reason aab-permissions.py hard-codes protobuf field numbers: a fixed format that
# has not moved since dex 035 beats a parsing dependency.
H_STRING_IDS = 56
H_TYPE_IDS = 64
H_PROTO_IDS = 72
H_METHOD_IDS = 88
H_CLASS_DEFS = 96


def u32(blob, offset):
    return struct.unpack_from("<I", blob, offset)[0]


def table(blob, header_offset):
    """(count, offset) of one of the header's id tables."""
    return u32(blob, header_offset), u32(blob, header_offset + 4)


def uleb128(blob, i):
    shift = result = 0
    while True:
        byte = blob[i]
        i += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, i
        shift += 7


class Dex:
    """Just enough of one dex file to answer "does class C define C()?".

    Only the id tables are read eagerly; a class's method list is walked on demand,
    because the whole point is to ask about a handful of named classes.
    """

    def __init__(self, blob):
        self.blob = blob

        count, offset = table(blob, H_STRING_IDS)
        self.string_offsets = struct.unpack_from(f"<{count}I", blob, offset)

        count, offset = table(blob, H_TYPE_IDS)
        self.type_strings = struct.unpack_from(f"<{count}I", blob, offset)

        self.proto_count, self.proto_offset = table(blob, H_PROTO_IDS)
        self.method_count, self.method_offset = table(blob, H_METHOD_IDS)

        # class_idx -> class_data_off, for the classes this dex *defines*. A type is
        # also in type_ids when it is merely referenced, which is not the same claim.
        count, offset = table(blob, H_CLASS_DEFS)
        self.defined = {}
        for i in range(count):
            entry = offset + i * 32
            self.defined[u32(blob, entry)] = u32(blob, entry + 24)

    def string(self, index):
        """One string_data_item: a uleb128 length in UTF-16 units, then MUTF-8 to a NUL."""
        _, start = uleb128(self.blob, self.string_offsets[index])
        end = self.blob.index(b"\0", start)
        return self.blob[start:end].decode("utf-8", errors="replace")

    def type_index(self, descriptor):
        for index, string_index in enumerate(self.type_strings):
            if self.string(string_index) == descriptor:
                return index
        return None

    def method(self, index):
        """(class_idx, proto_idx, name) of one method_id."""
        class_index, proto_index, name_index = struct.unpack_from(
            "<HHI", self.blob, self.method_offset + index * 8
        )
        return class_index, proto_index, self.string(name_index)

    def takes_no_arguments(self, proto_index):
        # proto_id is shorty_idx, return_type_idx, parameters_off — and an empty
        # parameter list is written as no list at all rather than as an empty one.
        return u32(self.blob, self.proto_offset + proto_index * 12 + 8) == 0

    def direct_methods(self, class_index):
        """(method_id index, access_flags) for each direct method of a defined class.

        Direct means static, private, or a constructor — which is where `<init>` is,
        and reading it is the difference between "the artifact defines it" and "some
        method_id mentions it", the second of which a caller elsewhere could satisfy.
        """
        data_offset = self.defined.get(class_index)
        if not data_offset:  # 0 means a class with no fields and no methods at all
            return
        i = data_offset
        static_fields, i = uleb128(self.blob, i)
        instance_fields, i = uleb128(self.blob, i)
        direct_methods, i = uleb128(self.blob, i)
        _virtual_methods, i = uleb128(self.blob, i)
        for _ in range(static_fields + instance_fields):
            _, i = uleb128(self.blob, i)  # field_idx_diff
            _, i = uleb128(self.blob, i)  # access_flags
        index = 0
        for _ in range(direct_methods):
            diff, i = uleb128(self.blob, i)
            access, i = uleb128(self.blob, i)
            _code_off, i = uleb128(self.blob, i)
            index += diff  # each encoded_method stores its index as a delta
            yield index, access


def descriptor_of(class_name):
    return "L" + class_name.replace(".", "/") + ";"


def constructor_of(dexes, class_name):
    """(found, public) for a class's no-arg constructor across the artifact's dexes.

    Returns (False, False) when the class itself is not defined anywhere — which is
    the other way this fails: R8 renaming the class breaks `Class.forName` just as
    completely as dropping its constructor.
    """
    descriptor = descriptor_of(class_name)
    for dex in dexes:
        index = dex.type_index(descriptor)
        if index is None or index not in dex.defined:
            continue
        for method_index, access in dex.direct_methods(index):
            _, proto_index, name = dex.method(method_index)
            if name == "<init>" and dex.takes_no_arguments(proto_index):
                return True, bool(access & ACC_PUBLIC)
        return False, False
    return False, False


def reflected_classes(manifest_blob):
    """[(class name, marker)] for every <meta-data> naming a class for reflection."""
    import importlib.util

    # aab-permissions.py owns the compiled-manifest walker; importing it by path keeps
    # one decoder rather than two that drift.
    here = __file__.rsplit("/", 1)[0]
    spec = importlib.util.spec_from_file_location("aab_permissions", f"{here}/aab-permissions.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    root = module.as_element(manifest_blob)
    if root is None:
        sys.exit("no root element in base/manifest/AndroidManifest.xml")

    found = []
    for tag, attrs, _raw in module.walk(root):
        if tag == "meta-data" and attrs.get("value") in MARKERS:
            name = attrs.get("name")
            if name:
                # A namespaced key — `com.google.firebase.components:<class>` — carries
                # the class after the colon, and an un-namespaced one *is* the class.
                found.append((name.rsplit(":", 1)[-1], attrs["value"]))
    return found


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "app/build/outputs/bundle/release/app-release.aab"
    try:
        with zipfile.ZipFile(path) as bundle:
            manifest = bundle.read("base/manifest/AndroidManifest.xml")
            names = sorted(n for n in bundle.namelist() if n.startswith("base/dex/") and n.endswith(".dex"))
            dexes = [Dex(bundle.read(name)) for name in names]
    except FileNotFoundError:
        sys.exit(f"no such bundle: {path}\nRun ./gradlew bundleRelease first.")
    except KeyError:
        sys.exit(f"{path} has no base/manifest/AndroidManifest.xml — is it an AAB?")

    if not dexes:
        sys.exit(f"{path} carries no base/dex/*.dex — nothing to check.")

    classes = reflected_classes(manifest)
    if not classes:
        print(f"  !   no <meta-data> names a class for reflection — none of {len(MARKERS)} markers matched")
        print("\nThat is either a dependency change or a broken read; check before trusting it.", file=sys.stderr)
        return 1

    missing, hidden = [], []
    for name, marker in sorted(classes):
        found, public = constructor_of(dexes, name)
        if not found:
            missing.append((name, marker))
        elif not public:
            hidden.append((name, marker))
        state = "ok " if found and public else "GONE" if not found else "HIDDEN"
        print(f"  {state} {name.rsplit('.', 1)[-1]}()  — {MARKERS[marker]}")

    problems = []
    if missing:
        problems.append(
            "named in the manifest for reflection, but the artifact has no such class\n"
            "with a no-arg constructor:\n"
            + "\n".join(f"  {n} — {MARKERS[m]}" for n, m in missing)
            + "\nR8 kept no reference to it because nothing constructs it in code. Add an\n"
            "evidence-backed keep to app/proguard-rules.pro, then re-run this."
        )
    if hidden:
        problems.append(
            "constructor present but not public, so reflection still cannot call it:\n"
            + "\n".join(f"  {n} — {MARKERS[m]}" for n, m in hidden)
        )

    if problems:
        print("\n" + "\n\n".join(problems) + "\n\nDo not upload this artifact.", file=sys.stderr)
        return 1

    print(
        f"\n{len(classes)} classes named for reflection, "
        f"all present in {len(dexes)} dex with a public no-arg constructor"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
