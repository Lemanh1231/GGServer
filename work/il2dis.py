#!/usr/bin/env python3
"""Disassemble specific il2cpp methods by VA, annotating BL targets (method names),
and ADRP/LDR loads of string-literal / metadata pointer slots (their values)."""
import json, struct, sys
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

import os
SO = os.environ.get('GG_SO', "/home/leman/guitargirl_project/bundle/libs/lib/arm64-v8a/libil2cpp.so")
raw = open(SO, 'rb').read()

# --- parse ELF64 program headers for VA<->offset ---
e_phoff = struct.unpack_from('<Q', raw, 0x20)[0]
e_phentsize = struct.unpack_from('<H', raw, 0x36)[0]
e_phnum = struct.unpack_from('<H', raw, 0x38)[0]
segs = []
for i in range(e_phnum):
    b = e_phoff + i*e_phentsize
    p_type, p_flags, p_offset, p_vaddr = struct.unpack_from('<IIQQ', raw, b)
    p_filesz, p_memsz = struct.unpack_from('<QQ', raw, b+0x28)
    if p_type == 1:  # PT_LOAD
        segs.append((p_vaddr, p_offset, p_filesz))

def va2off(va):
    for vaddr, off, sz in segs:
        if vaddr <= va < vaddr + sz:
            return off + (va - vaddr)
    return None

# --- load symbol maps from script.json ---
print("loading script.json ...", file=sys.stderr)
S = json.load(open('out/script.json'))
methods = {m['Address']: m['Name'] for m in S['ScriptMethod']}
sigs = {m['Address']: m.get('Signature','') for m in S['ScriptMethod']}
strings = {s['Address']: s['Value'] for s in S['ScriptString']}
meta = {m['Address']: m['Name'] for m in S['ScriptMetadata']}
metam = {m['Address']: m['Name'] for m in S['ScriptMetadataMethod']}
print(f"methods={len(methods)} strings={len(strings)} meta={len(meta)}", file=sys.stderr)

md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
md.detail = True

def name_at(va):
    if va in methods: return methods[va]
    if va in metam: return metam[va]
    return None

def ptr_note(addr):
    if addr in strings: return 'STR "%s"' % strings[addr].replace('\n','\\n')
    if addr in meta:    return 'META %s' % meta[addr]
    if addr in methods: return 'MREF %s' % methods[addr]
    if addr in metam:   return 'MREF %s' % metam[addr]
    return None

def disasm(va, n=160, name=''):
    off = va2off(va)
    if off is None:
        print("VA %#x not mapped" % va); return
    code = raw[off:off+n*4]
    regs = {}  # reg -> resolved address (from adrp/add/ldr)
    print(f"\n===== {name}  VA={va:#x} off={off:#x} =====")
    for ins in md.disasm(code, va):
        line = f"  {ins.address:#010x}  {ins.mnemonic:8} {ins.op_str}"
        note = ''
        m = ins.mnemonic
        if m == 'adrp':
            try:
                rd = ins.op_str.split(',')[0].strip()
                imm = int(ins.op_str.split('#')[-1], 0)
                regs[rd] = imm
            except: pass
        elif m == 'add' and '#' in ins.op_str:
            parts = [p.strip() for p in ins.op_str.split(',')]
            if len(parts) >= 3 and parts[1] in regs:
                try:
                    base = regs[parts[1]]; imm = int(parts[2].split('#')[-1],0)
                    regs[parts[0]] = base+imm
                    nt = ptr_note(base+imm)
                    if nt: note = ' ; '+nt
                except: pass
        elif m == 'ldr':
            parts = ins.op_str.split(',')
            if len(parts) >= 2 and '[' in ins.op_str:
                basereg = parts[1].strip().lstrip('[').strip()
                imm = 0
                if '#' in ins.op_str:
                    try: imm = int(ins.op_str.split('#')[-1].rstrip(']'),0)
                    except: imm=0
                if basereg in regs:
                    addr = regs[basereg]+imm
                    nt = ptr_note(addr)
                    if nt: note = ' ; '+nt
                    regs[parts[0].strip()] = addr
        elif m in ('bl','b'):
            try:
                tgt = int(ins.op_str.split('#')[-1],0)
                nm = name_at(tgt)
                if nm: note = ' ; -> '+nm
            except: pass
        print(line+note)
        if m == 'ret': break

if __name__ == '__main__':
    for a in sys.argv[1:]:
        va = int(a,0)
        disasm(va, 200, name_at(va) or '')
