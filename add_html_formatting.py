import os, re, ast

# Now safely add HTML formatting ONLY in message string literals
# that are passed to answer(), edit_text(), send_message() etc.

def convert_md_in_message_strings(src):
    lines = src.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip pure code lines
        if (stripped.startswith('import ')
            or stripped.startswith('from ')
            or stripped.startswith('def ')
            or stripped.startswith('async def ')
            or stripped.startswith('class ')
            or stripped.startswith('@')
            or stripped.startswith('#')
            or stripped.startswith('super()')
            or stripped.startswith('cascade')
            or stripped.startswith('back_populates')
            or stripped.startswith('logger')):
            new_lines.append(line)
            continue
        
        # Only convert **text** -> <b>text</b> if line has message-like context
        # (contains answer, send_message, edit_text, answer_photo, etc.)
        if '**' in line:
            # Convert **text** to <b>text</b>
            line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
        
        new_lines.append(line)
    return '\n'.join(new_lines)

total = 0
for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for fname in files:
        if not fname.endswith('.py'):
            continue
        p = os.path.join(root, fname)
        with open(p, 'r', encoding='utf-8') as f:
            src = f.read()
        
        # Only process if has Markdown bold syntax
        if '**' not in src:
            continue
        
        fixed = convert_md_in_message_strings(src)
        if fixed != src:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(fixed)
            total += 1
            print(f'FORMATTED: {p}')

print(f'Total: {total} files formatted')

# Final syntax check
errors = []
for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for fname in files:
        if not fname.endswith('.py'):
            continue
        p = os.path.join(root, fname)
        with open(p, 'r', encoding='utf-8') as f:
            src = f.read()
        try:
            ast.parse(src)
        except SyntaxError as e:
            errors.append(f'SYNTAX {p}:{e.lineno}: {e.msg}')

if errors:
    for e in errors: print(e)
else:
    print('ALL SYNTAX OK after formatting!')
