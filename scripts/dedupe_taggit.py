#!/usr/bin/env python3
"""
Deduplicate or strip `taggit.TaggedItem` entries from a Django JSON fixture.

Usage:
  python scripts/dedupe_taggit.py input.json output.json [--strip-only]

If `--strip-only` is provided the script will remove all `taggit.taggeditem`
objects. Otherwise it will keep the first occurrence for each (object_id,
content_type, tag) tuple and drop duplicates.
"""
import json
import sys
from pathlib import Path


def main(argv):
    if len(argv) < 3:
        print("Usage: dedupe_taggit.py input.json output.json [--strip-only]")
        return 2

    infile = Path(argv[1])
    outfile = Path(argv[2])
    strip_only = "--strip-only" in argv[3:]

    if not infile.exists():
        print(f"Input file not found: {infile}")
        return 3

    with infile.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("Expected a list-style Django fixture (dumpdata). Exiting.")
        return 4

    out = []
    seen = set()
    total = 0
    removed = 0

    for obj in data:
        total += 1
        model = obj.get("model", "").lower()
        if model == "taggit.taggeditem":
            if strip_only:
                removed += 1
                continue

            fields = obj.get("fields", {})
            # Try common keys used in fixtures for TaggedItem
            object_id = fields.get("object_id") or fields.get("object_pk")
            content_type = fields.get("content_type") or fields.get("content_type_id")
            tag = fields.get("tag") or fields.get("tag_id") or fields.get("tag_name") or json.dumps(fields.get("tag"))

            key = (str(content_type), str(object_id), str(tag))
            if key in seen:
                removed += 1
                continue
            seen.add(key)
            out.append(obj)
        else:
            out.append(obj)

    outfile.parent.mkdir(parents=True, exist_ok=True)
    with outfile.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"Processed {total} objects; removed {removed} taggit.TaggedItem entries; wrote {len(out)} objects to {outfile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
