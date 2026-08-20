import os, sys
sys.stdout.reconfigure(encoding='utf-8')

keywords = ['test.code', 'cloned.code', 'cert_num', 'certificate_number', 'tg_id', 'user.telegram_id', 'deep_link', 'invite_link']

for root, dirs, files in os.walk('app/bot/handlers'):
    for f in files:
        if not f.endswith('.py'): continue
        p = os.path.join(root, f)
        with open(p, 'r', encoding='utf-8') as fp:
            lines = fp.readlines()
        for i, l in enumerate(lines, 1):
            if any(k in l for k in keywords):
                if 'f"' in l or "f'" in l or 'text' in l:
                    print(f"{p}:{i}: {l.strip()[:110]}")
