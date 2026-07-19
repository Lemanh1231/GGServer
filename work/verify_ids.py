#!/usr/bin/env python3
"""Extract (thrift_type, field_id) pairs from a DTO's Write method by tracking
immediate movs feeding `strb [sp,#a]` (type) and `strh [sp,#a+2]` (id)."""
import json, struct, sys
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

SO = "/Users/furiri/Downloads/Guitar+Girl_8.0.0_APKPure/config.arm64_v8a/lib/arm64-v8a/libil2cpp.so"
raw = open(SO,'rb').read()
e_phoff=struct.unpack_from('<Q',raw,0x20)[0]; e_phentsize=struct.unpack_from('<H',raw,0x36)[0]; e_phnum=struct.unpack_from('<H',raw,0x38)[0]
segs=[]
for i in range(e_phnum):
    b=e_phoff+i*e_phentsize
    pt,pf,po,pv=struct.unpack_from('<IIQQ',raw,b); pfs,pms=struct.unpack_from('<QQ',raw,b+0x28)
    if pt==1: segs.append((pv,po,pfs))
def va2off(va):
    for v,o,s in segs:
        if v<=va<v+s: return o+(va-v)
    return None
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM); md.detail=True

TYPENAME={2:'BOOL',3:'BYTE',4:'DOUBLE',6:'I16',8:'I32',10:'I64',11:'STRING',12:'STRUCT',13:'MAP',14:'SET',15:'LIST'}

def extract(va, maxins=2000):
    off=va2off(va)
    if off is None: return None
    code=raw[off:off+maxins*4]
    regs={}
    pending_type=None  # (stack_off, type_val)
    out=[]
    for ins in md.disasm(code, va):
        m=ins.mnemonic; ops=ins.op_str
        if m in ('mov','movz') and ',' in ops:
            d=ops.split(',')[0].strip()
            if '#' in ops:
                try: regs[d]=int(ops.split('#')[-1],0)
                except: pass
            else:
                s=ops.split(',')[1].strip(); regs[d]=regs.get(s)
        elif m=='movk':
            d=ops.split(',')[0].strip()
            try:
                imm=int(ops.split('#')[1].split(',')[0],0); sh=0
                if 'lsl' in ops: sh=int(ops.split('lsl')[-1].split('#')[-1],0)
                regs[d]=(regs.get(d,0) & ~(0xffff<<sh)) | (imm<<sh)
            except: pass
        elif m=='strb' and '[sp' in ops:
            r=ops.split(',')[0].strip()
            try: aoff=int(ops.split('#')[-1].rstrip(']'),0)
            except: aoff=0
            if r in regs and regs[r] in TYPENAME:
                pending_type=(aoff, regs[r])
        elif m=='strh' and '[sp' in ops:
            r=ops.split(',')[0].strip()
            try: aoff=int(ops.split('#')[-1].rstrip(']'),0)
            except: aoff=0
            if pending_type and aoff==pending_type[0]+2 and r in regs:
                out.append((pending_type[1], regs[r]))
                pending_type=None
        elif m=='ret':
            break
    return out

if __name__=='__main__':
    sch=json.load(open('../emulator/schema/schema_raw.json'))
    import random
    keys=[k for k,v in sch.items() if v['write_rva']]
    sample = ['user.userLoginDataInfo','user.userLoginRetDataInfo','user.buyItemRetDataInfo'] + keys[:40]
    mismatch=0; checked=0
    for k in sample:
        c=sch[k]
        if not c['write_rva']: continue
        pairs=extract(int(c['write_rva'],0))
        exp=[(f['type'], f['id']) for f in c['fields']]
        got=[(TYPENAME[t], i) for t,i in pairs]
        checked+=1
        ids_seq = [i for _,i in pairs]
        seq_ok = ids_seq==list(range(1,len(ids_seq)+1))
        if got!=exp:
            mismatch+=1
            if mismatch<=12:
                print(f"DIFF {k}\n   exp={exp}\n   got={got}  ids_sequential={seq_ok}")
    print(f"\nchecked={checked} mismatch={mismatch}")
