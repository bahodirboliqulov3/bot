import os, re, ast

# Fix __dunder__ that got converted to <b>dunder</b>
# Also fix import html duplicate on test_solver.py line 8

def fix_dunders(src):
    # Fix <b>init</b> -> __init__
    src = re.sub(r'<b>(init|name|repr|str|eq|hash|len|getitem|setitem|delitem|contains|iter|next|call|enter|exit|del|add|sub|mul|div|mod|truediv|floordiv|new|class|doc|dict|slots|all__)</b>', r'__\1__', src)
    src = re.sub(r'<b>([a-zA-Z_]+)</b>', r'__\1__', src)
    return src

total_fixed = 0
for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for fname in files:
        if not fname.endswith('.py'):
            continue
        p = os.path.join(root, fname)
        with open(p, 'r', encoding='utf-8') as f:
            src = f.read()
        
        fixed = fix_dunders(src)
        if fixed != src:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(fixed)
            total_fixed += 1

print(f'Fixed dunders in {total_fixed} files')

# Now fix test_solver.py line 8 duplicate import html
p = 'app/bot/handlers/student/test_solver.py'
with open(p, 'r', encoding='utf-8') as f:
    src = f.read()
# Check if there are duplicate import html lines
lines = src.split('\n')
seen_html = False
new_lines = []
for i, l in enumerate(lines):
    if l.strip() == 'import html':
        if seen_html:
            continue  # skip duplicate
        seen_html = True
    new_lines.append(l)
new_src = '\n'.join(new_lines)
if new_src != src:
    with open(p, 'w', encoding='utf-8') as f:
        f.write(new_src)
    print(f'Fixed duplicate import html in {p}')

# Final syntax check
errors = []
for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for fname in files:
        if not fname.endswith('.py'):
            continue
        p_check = os.path.join(root, fname)
        with open(p_check, 'r', encoding='utf-8') as f:
            src = f.read()
        try:
            ast.parse(src)
        except SyntaxError as e:
            errors.append((p_check, e.lineno, e.msg))
            with open(p_check, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if e.lineno and e.lineno <= len(lines):
                errors.append(('', 0, f'  -> {lines[e.lineno-1].rstrip()}'))

if errors:
    for p_e, ln, msg in errors:
        if p_e:
            print(f'SYNTAX {p_e}:{ln}: {msg}')
        else:
            print(msg)
else:
    print('ALL SYNTAX CLEAN!')
