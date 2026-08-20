import os, sys
sys.stdout.reconfigure(encoding='utf-8')

for root, dirs, files in os.walk('app'):
    for f in files:
        if not f.endswith('.py'): continue
        p = os.path.join(root, f)
        with open(p, 'r', encoding='utf-8') as fp:
            lines = fp.readlines()
        for i, l in enumerate(lines, 1):
            if 'respublika' in l.lower():
                print(f"{p}:{i}: {l.strip()[:100]}")
