#!/usr/bin/env python3
"""Parse dump.cs: every `class X : TBase` -> namespace, ordered fields (name, C# type),
Read/Write RVAs. Also handles nested Isset structs and enums used as field types."""
import re, json, sys

DUMP = "out/dump.cs"
lines = open(DUMP, encoding='utf-8').read().split('\n')

# Map TypeDefIndex namespace: dump.cs emits `// Namespace: <ns>` before each type.
classes = {}            # fullname -> dict
enums = set()           # enum type names (treated as I32)
i = 0
cur_ns = ""
n = len(lines)

# First pass: collect enum names (so we can map enum-typed fields to I32)
for ln in lines:
    m = re.match(r'public enum ([\w.<>`]+)', ln)
    if m: enums.add(m.group(1).split('//')[0].strip())

def cs_to_thrift(t):
    t = t.strip()
    base = {
        'bool':'BOOL','sbyte':'BYTE','byte':'BYTE','short':'I16','ushort':'I16',
        'int':'I32','uint':'I32','long':'I64','ulong':'I64','double':'DOUBLE','float':'DOUBLE',
        'string':'STRING','String':'STRING',
    }
    if t in base: return base[t], None
    lm = re.match(r'List<(.+)>$', t)
    if lm:
        et, ee = cs_to_thrift(lm.group(1))
        return 'LIST', (et, ee)
    mm = re.match(r'Dictionary<(.+),\s*(.+)>$', t)
    if mm:
        kt,_ = cs_to_thrift(mm.group(1)); vt, ve = cs_to_thrift(mm.group(2))
        return 'MAP', (kt, vt, ve)
    if t in enums or t.split('.')[-1] in {e.split('.')[-1] for e in enums}:
        return 'I32', None        # enums serialize as I32
    # otherwise assume nested struct (another TBase DTO)
    return 'STRUCT', t

i = 0
while i < n:
    ln = lines[i]
    nm = re.match(r'// Namespace: (.*)$', ln)
    if nm:
        cur_ns = nm.group(1).strip(); i += 1; continue
    cm = re.match(r'public (?:sealed )?class ([\w]+) : TBase', ln)
    if cm:
        cname = cm.group(1)
        ns = cur_ns
        fields = []  # (name, cstype)
        rva = {}
        j = i + 1
        depth_seen = False
        # walk the class body
        while j < n:
            l = lines[j]
            if l.startswith('public class ') or l.startswith('public sealed class ') or l.startswith('public struct ') or l.startswith('public enum ') or re.match(r'// Namespace:', l):
                break
            # field:  private <type> _name; // 0x..
            fm = re.match(r'\s*(?:private|public|internal)\s+([\w.<>`,\s]+?)\s+(_\w+);', l)
            if fm and '__isset' not in l and 'static' not in l:
                ftype = fm.group(1).strip(); fname = fm.group(2)
                fields.append((fname, ftype))
            wm = re.search(r'RVA: (0x[0-9A-Fa-f]+).*\n', l)
            rm = re.match(r'\s*// RVA: (0x[0-9A-Fa-f]+)', l)
            if rm:
                # look ahead for the method name on next non-empty line
                k = j+1
                while k < n and lines[k].strip()=='':
                    k+=1
                sig = lines[k] if k < n else ''
                if 'void Read(TProtocol' in sig:
                    rva['Read'] = rm.group(1)
                elif 'void Write(TProtocol' in sig:
                    rva['Write'] = rm.group(1)
            j += 1
        # build thrift field list (ids assigned 1..N provisionally; refined by disasm later)
        tfields = []
        for idx,(fname,ftype) in enumerate(fields, start=1):
            tt, extra = cs_to_thrift(ftype)
            f = {'name': fname.lstrip('_'), 'raw': fname, 'cs': ftype, 'type': tt, 'id': idx}
            if tt == 'LIST': f['elem'] = extra
            if tt == 'MAP': f['kv'] = extra
            if tt == 'STRUCT': f['struct'] = extra
            tfields.append(f)
        full = (ns + '.' + cname) if ns else cname
        classes[full] = {'ns': ns, 'name': cname, 'fields': tfields,
                         'read_rva': rva.get('Read'), 'write_rva': rva.get('Write')}
        i = j; continue
    i += 1

json.dump(classes, open('../emulator/schema/schema_raw.json','w'), indent=1, ensure_ascii=False)
print("TBase DTO classes:", len(classes))
print("enums seen:", len(enums))
# sanity
for k in ('user.userLoginDataInfo','user.userLoginRetDataInfo','user.buyItemRetDataInfo'):
    c = classes.get(k)
    if c:
        print('\n', k, 'Read', c['read_rva'], 'Write', c['write_rva'])
        for f in c['fields']:
            print('   id=%d %-18s %-10s cs=%s' % (f['id'], f['name'], f['type'], f['cs']))
