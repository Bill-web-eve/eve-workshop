#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from muhely.catalog import import_sde, Catalog

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    if len(sys.argv) != 2:
        raise SystemExit('Használat: python3 tools/build_catalog.py /utvonal/eve-sde.zip')
    target = root/'data/catalog.sqlite3'
    import_sde(sys.argv[1], target)
    c = Catalog(target)
    print(f"SDE {c.meta['buildNumber']}: {len(c.types)} típus, {len(c.recipes)} gyártási/reakciós recept.")
