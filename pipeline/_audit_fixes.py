"""Аудит доставки фиксов: для каждого fix-юнита сверяем его файлы с per-mod
дескрипторами родителя. Показывает, какие фикс-файлы НЕ попали в дескриптор
(лаунчер отдаёт базовую версию)."""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
import aggregate as A

FIX_PARENT = {
    'redux_fixes': 'redux_base_installer',
    'original_fixes': 'original_installer',
    'reflection_fixes': 'reflection_installer',
    'universe_fixes_130325': 'universe_community',
    'denmods_fix': 'denmods',
}

def load_manifest(unit_dir):
    cm = A.load_json(unit_dir / 'code.manifest.json', {}).get('files', {})
    am = A.load_json(unit_dir / 'assets.manifest.json', {})
    am = am.get('files', am) if isinstance(am, dict) else {}
    return cm, am

def parent_unit_dir(fix_unit_dir, parent_name):
    # родитель в том же лагере
    cand = fix_unit_dir.parent / parent_name
    if cand.is_dir():
        return cand
    # поиск по всем лагерям
    for d in A.MODS.glob('*/'+parent_name):
        return d
    return None

def install_map(cm, am):
    """{install_rel_lower: (install_rel, sha)} — как файлы лягут на диск."""
    out = {}
    for man in (cm, am):
        for rel, meta in man.items():
            a = A._after_mods(rel)
            if a is None:
                continue
            out[a.lower()] = (a, meta['sha256'])
    return out

cfg = A.load_json(A.CONFIG, {})
fix_units = [u for u in cfg.get('units', []) if u.get('role') == 'fixes']

# ВСЕ sha, встречающиеся в ЛЮБОМ дескрипторе (для проверки «доставлен хоть где-то»)
ALL_DESC_SHA = set()
for jf in (A.REPO / 'descriptors').rglob('*.json'):
    if jf.name == 'catalog.json':
        continue
    d = A.load_json(jf, {})
    for kind in ('code', 'assets'):
        for meta in d.get('files', {}).get(kind, {}).values():
            ALL_DESC_SHA.add(meta['sha256'])

grand = {'delivered': 0, 'stale': 0, 'newfile': 0, 'no_parent_mod': 0}
report = []
for u in fix_units:
    name, camp = u['name'], u['camp']
    fdir = A.MODS / camp / name
    parent = u.get('fix_parent') or FIX_PARENT.get(name)
    pdir = parent_unit_dir(fdir, parent) if parent else None
    fcm, fam = load_manifest(fdir)
    fix_inst = install_map(fcm, fam)

    # родительские mod-roots (папки с ModuleInfo.txt) и их дескрипторы
    pcm, pam = load_manifest(pdir) if pdir else ({}, {})
    roots = []
    for rel in pcm:
        a = A._after_mods(rel)
        if a and a.lower().endswith('/moduleinfo.txt'):
            roots.append(a[:-len('/ModuleInfo.txt')])
    roots.sort(key=len, reverse=True)

    # install-rel -> sha из ВСЕХ дескрипторов родителя (то, что реально отдаёт лаунчер)
    desc_sha = {}   # install_rel_lower -> sha
    desc_dir = A.REPO / 'descriptors' / camp / parent if parent else None
    if desc_dir and desc_dir.is_dir():
        for jf in desc_dir.rglob('*.json'):
            d = A.load_json(jf, {})
            for kind in ('code', 'assets'):
                for rel, meta in d.get('files', {}).get(kind, {}).items():
                    a = A._after_mods(rel)
                    if a:
                        desc_sha[a.lower()] = meta['sha256']

    def root_of(inst_lower):
        for r in roots:
            rl = r.lower()
            if inst_lower == rl or inst_lower.startswith(rl + '/'):
                return r
        return None

    per_mod = {}   # root -> {'stale':[], 'newfile':[], 'delivered':int}
    for il, (inst, fsha) in fix_inst.items():
        r = root_of(il)
        if r is None:
            grand['no_parent_mod'] += 1
            continue
        slot = per_mod.setdefault(r, {'stale': [], 'newfile': [], 'delivered': 0})
        dsha = desc_sha.get(il)
        if dsha == fsha:
            slot['delivered'] += 1; grand['delivered'] += 1
        elif dsha is not None:
            slot['stale'].append(inst); grand['stale'] += 1        # база в дескрипторе — фикс потерян
        elif fsha in ALL_DESC_SHA:
            slot['delivered'] += 1; grand['delivered'] += 1        # доставлен через свой (фикс-юнита) дескриптор
        else:
            slot['newfile'].append(inst); grand['newfile'] += 1    # нигде — реально не доставлен

    broken = {r: v for r, v in per_mod.items() if v['stale'] or v['newfile']}
    report.append((f'{camp}/{name}', parent, len(per_mod), broken))

print("="*70)
for unit, parent, nmods, broken in report:
    print(f"\n### {unit}  (parent={parent})  затрагивает {nmods} модов, "
          f"НЕ доставлено в {len(broken)}:")
    for r in sorted(broken):
        v = broken[r]
        bits = []
        if v['stale']:   bits.append(f"{len(v['stale'])} устаревших")
        if v['newfile']: bits.append(f"{len(v['newfile'])} новых(нет в базе)")
        print(f"    ✗ {r}: " + ", ".join(bits))
        for f in v['stale']:   print(f"        stale : {f}")
        for f in v['newfile']: print(f"        new   : {f}")

print("\n" + "="*70)
print(f"ИТОГО файлов: доставлено={grand['delivered']}  "
      f"устаревших(фикс потерян)={grand['stale']}  "
      f"новых-не-в-базе={grand['newfile']}  вне-модов={grand['no_parent_mod']}")
