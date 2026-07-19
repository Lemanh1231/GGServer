#!/usr/bin/env python3
"""Minimal IL2CPP global-metadata.dat v31 parser.
Extracts type definitions with their field names and method names."""
import struct, sys, json

PATH = "/Users/furiri/Downloads/Guitar+Girl_8.0.0_APKPure/base_assets/assets/bin/Data/Managed/Metadata/global-metadata.dat"
data = open(PATH, 'rb').read()

# header pairs (offset,size) start at byte 8
def pair(i):
    return struct.unpack_from('<II', data, 8 + i*8)

STR_off, STR_sz = pair(2)          # identifier string heap
FLD_off, FLD_sz = pair(11)         # fields table
MTH_off, MTH_sz = pair(5)          # methods table
TYPE_off, TYPE_sz = pair(19)       # typeDefinitions

def s(idx):
    if idx < 0: return ""
    e = data.index(b'\x00', STR_off + idx)
    return data[STR_off+idx:e].decode('utf-8','replace')

# fields: {nameIndex:i32, typeIndex:i32, token:u32} = 12 bytes
FLD_REC = 12
def field_name(i):
    ni, = struct.unpack_from('<i', data, FLD_off + i*FLD_REC)
    return s(ni)

# methods: 36-byte records, nameIndex@0
MTH_REC = 36
def method_name(i):
    ni, = struct.unpack_from('<i', data, MTH_off + i*MTH_REC)
    return s(ni)

# typeDefinitions: 88-byte records
TY_REC = 88
NTYPES = TYPE_sz // TY_REC
def typedef(i):
    base = TYPE_off + i*TY_REC
    nameIndex, namespaceIndex = struct.unpack_from('<ii', data, base)
    fieldStart, methodStart = struct.unpack_from('<ii', data, base+32), None
    fieldStart, = struct.unpack_from('<i', data, base+32)
    methodStart, = struct.unpack_from('<i', data, base+36)
    method_count, property_count, field_count = struct.unpack_from('<HHH', data, base+64)
    return {
        'name': s(nameIndex), 'ns': s(namespaceIndex),
        'fieldStart': fieldStart, 'field_count': field_count,
        'methodStart': methodStart, 'method_count': method_count,
    }

if __name__ == '__main__':
    want = sys.argv[1] if len(sys.argv) > 1 else 'GuitarGirl'
    out = []
    for i in range(NTYPES):
        t = typedef(i)
        if want.lower() in t['ns'].lower() or want.lower() in t['name'].lower():
            fields = []
            if 0 <= t['fieldStart'] and t['field_count'] < 1000:
                for f in range(t['fieldStart'], t['fieldStart']+t['field_count']):
                    fields.append(field_name(f))
            methods = []
            if 0 <= t['methodStart'] and t['method_count'] < 2000:
                for m in range(t['methodStart'], t['methodStart']+t['method_count']):
                    methods.append(method_name(m))
            out.append({'ns': t['ns'], 'name': t['name'], 'fields': fields, 'methods': methods})
    json.dump(out, open('work/types_%s.json' % want.replace('.','_'), 'w'), indent=1, ensure_ascii=False)
    print("matched types:", len(out))
    # sanity print a few
    for t in out[:3]:
        print("  %s.%s  fields=%d methods=%d" % (t['ns'], t['name'], len(t['fields']), len(t['methods'])))
