import os, re

for root, dirs, files in os.walk('app/bot'):
    for f in files:
        if not f.endswith('.py') or f == 'certificates.py': continue
        p = os.path.join(root, f)
        with open(p, 'r', encoding='utf-8') as fp:
            lines = fp.readlines()
        for i, l in enumerate(lines, 1):
            if any(k in l.lower() for k in ['sertifikat', 'certificate']):
                if 'import' not in l and '#' not in l:
                    print(f"{p}:{i}: {l.strip()[:100]}")
