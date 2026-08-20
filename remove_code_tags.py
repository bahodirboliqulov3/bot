import os, re, ast

# Remove ALL <code>...</code> tags from message strings in handler files
# Keep <b> and <i> for bold/italic formatting

fixed = 0
for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if not f.endswith('.py'):
            continue
        p = os.path.join(root, f)
        with open(p, 'r', encoding='utf-8') as fp:
            src = fp.read()

        # Remove <code> and </code> tags but keep the text inside
        new_src = re.sub(r'<code>(.*?)</code>', r'\1', src, flags=re.DOTALL)

        if new_src != src:
            with open(p, 'w', encoding='utf-8') as fp:
                fp.write(new_src)
            fixed += 1
            print(f'FIXED: {p}')

print(f'\nTotal files fixed: {fixed}')

# Syntax check
errors = []
for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if not f.endswith('.py'):
            continue
        p = os.path.join(root, f)
        with open(p, 'r', encoding='utf-8') as fp:
            src = fp.read()
        try:
            ast.parse(src)
        except SyntaxError as e:
            errors.append(f'SYNTAX {p}:{e.lineno}: {e.msg}')

if errors:
    for e in errors:
        print(e)
else:
    print('ALL SYNTAX OK!')
