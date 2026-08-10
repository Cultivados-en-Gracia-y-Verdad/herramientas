#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from cgv_manager.model import *
t=load_yaml(ROOT/"state.template.yaml")
s=new_state(t,"daniel","Daniel")
a=load_yaml(ROOT/"contracts"/"alignment-attestation.template.yaml")
a["project"]["book"]="daniel"
a["source"].update(path="/missing/source",revision="src1",checksum_sha256="a")
a["alignment"].update(path="/missing/alignment",revision="aln1",checksum_sha256="b")
a["producer"]["status"]="PASS"
for k in a["producer"]["checks"]: a["producer"]["checks"][k]="PASS"
a["independent_verification"]["status"]="PASS"
for k in a["independent_verification"]["checks"]: a["independent_verification"]["checks"][k]="PASS"
a["human_linguistic_review"]["status"]="PASS"
a["attestation"]["status"]="VERIFIED"
assert verify_gate0_attestation(a,"daniel")==[]
accept_gate0(s,a,"test.yaml")
assert s["gates"]["G0_ALIGNMENT"]["status"]=="PASS"
assert s["gates"]["G1_COMPILE"]["status"]=="READY"
print("PASS")
