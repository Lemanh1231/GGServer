#!/usr/bin/env python3
"""Definitive Thrift schema builder.
- (thrift_type, field_id) come from each DTO's Write method disassembly (authoritative wire truth),
  bounded precisely by the next function address (no truncation/overrun).
- field names + container element/struct/map info come from dump.cs (positional zip).
Output: emulator/schema/schema.json"""
import json, struct, bisect
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

SO="/Users/furiri/Downloads/Guitar+Girl_8.0.0_APKPure/config.arm64_v8a/lib/arm64-v8a/libil2cpp.so"
raw=open(SO,'rb').read()
e_phoff=struct.unpack_from('<Q',raw,0x20)[0]; e_phentsize=struct.unpack_from('<H',raw,0x36)[0]; e_phnum=struct.unpack_from('<H',raw,0x38)[0]
segs=[]
for i in range(e_phnum):
    b=e_phoff+i*e_phentsize
    pt,_,po,pv=struct.unpack_from('<IIQQ',raw,b); pfs,_=struct.unpack_from('<QQ',raw,b+0x28)
    if pt==1: segs.append((pv,po,pfs))
def va2off(va):
    for v,o,s in segs:
        if v<=va<v+s: return o+(va-v)
    return None
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM); md.detail=True
TYPENAME={2:'BOOL',3:'BYTE',4:'DOUBLE',6:'I16',8:'I32',10:'I64',11:'STRING',12:'STRUCT',13:'MAP',14:'SET',15:'LIST'}

# sorted function boundaries
S=json.load(open('out/script.json'))
faddrs=sorted({m['Address'] for m in S['ScriptMethod']})
def func_end(va):
    i=bisect.bisect_right(faddrs, va)
    return faddrs[i] if i<len(faddrs) else va+0x4000

def extract_write(va):
    end=func_end(va); off=va2off(va)
    if off is None: return []
    code=raw[off:off+(end-va)]
    regs={}; pend=None; out=[]
    for ins in md.disasm(code, va):
        m=ins.mnemonic; ops=ins.op_str
        if m in ('mov','movz') and ',' in ops:
            d=ops.split(',')[0].strip()
            if '#' in ops:
                try: regs[d]=int(ops.split('#')[-1],0)
                except: pass
            else:
                regs[d]=regs.get(ops.split(',')[1].strip())
        elif m=='movk':
            d=ops.split(',')[0].strip()
            try:
                imm=int(ops.split('#')[1].split(',')[0],0); sh=0
                if 'lsl' in ops: sh=int(ops.split('lsl')[-1].split('#')[-1],0)
                regs[d]=(regs.get(d,0)&~(0xffff<<sh))|(imm<<sh)
            except: pass
        elif m=='strb' and '[sp' in ops:
            r=ops.split(',')[0].strip()
            try: a=int(ops.split('#')[-1].rstrip(']'),0)
            except: a=0
            if r in regs and regs[r] in TYPENAME: pend=(a,regs[r])
        elif m=='strh' and '[sp' in ops:
            r=ops.split(',')[0].strip()
            try: a=int(ops.split('#')[-1].rstrip(']'),0)
            except: a=0
            if pend and a==pend[0]+2 and r in regs:
                out.append((pend[1],regs[r])); pend=None
    return out

raw_sch=json.load(open('../emulator/schema/schema_raw.json'))
# index DTO simple-name -> list of fullnames (for struct ref resolution)
byname={}
for full,c in raw_sch.items():
    byname.setdefault(c['name'],[]).append(full)
def resolve_struct(simple, ns):
    cands=byname.get(simple) or byname.get(simple.split('.')[-1])
    if not cands: return simple
    same=[x for x in cands if raw_sch[x]['ns']==ns]
    return (same or cands)[0]

schema={}; discrep=[]
for full,c in raw_sch.items():
    pairs=extract_write(int(c['write_rva'],0)) if c['write_rva'] else []
    decl=c['fields']
    fields=[]
    for idx,(t,fid) in enumerate(pairs):
        tn=TYPENAME[t]
        d=decl[idx] if idx<len(decl) else None
        f={'id':fid,'type':tn,'name': d['name'] if d else 'f%d'%fid}
        # container/struct detail from dump.cs declared field (positional)
        if d:
            if tn=='LIST' and 'elem' in d and d['elem']:
                et,ee=d['elem']
                f['elem']={'type':et}
                if et=='STRUCT': f['elem']['struct']=resolve_struct(ee, c['ns'])
                elif et=='LIST' and ee: f['elem']['elem']=ee
            elif tn=='MAP' and 'kv' in d and d['kv']:
                kt,vt,ve=d['kv']
                f['key']={'type':kt}; f['val']={'type':vt}
                if vt=='STRUCT': f['val']['struct']=resolve_struct(ve,c['ns'])
            elif tn=='STRUCT' and 'struct' in d and d['struct']:
                f['struct']=resolve_struct(d['struct'], c['ns'])
        fields.append(f)
    if len(pairs)!=len(decl):
        discrep.append((full,len(decl),len(pairs)))
    schema[full]={'ns':c['ns'],'name':c['name'],'fields':fields,
                  'read_rva':c['read_rva'],'write_rva':c['write_rva']}

json.dump(schema, open('../emulator/schema/schema.json','w'), indent=0, ensure_ascii=False)
print("DTOs:",len(schema),"  field-count discrepancies (decl vs wire):",len(discrep))
for d in discrep[:20]: print("  ",d)
# show a struct/list/map example
import textwrap
for k in ('user.userLoginRetDataInfo','main.getSubscribeList'):
    print("\n",k); [print("   ",f) for f in schema[k]['fields']]
