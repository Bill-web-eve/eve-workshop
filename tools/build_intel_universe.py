#!/usr/bin/env python3
"""Extract public topology and ship names from an official CCP JSONL SDE ZIP."""
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from muhely.intel_universe import build
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'data/intel_universe.json');p.add_argument('--build',type=int)
    a=p.parse_args();assert build(a.archive,a.output,a.build),'The archive does not include CCP map data'
    print('Public intel topology saved:',a.output)
