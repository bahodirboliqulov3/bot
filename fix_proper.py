import os
import re

# This script safely converts only parse_mode="Markdown" to HTML,
# and converts markdown syntax ONLY inside Python string literals (not import lines)

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    
    original = src
    
    # Step 1: Undo the broken <code> wrapping on import lines
    # <code>import html</code> -> import html
    src = re.sub(r'<code>(import [^<]+)</code>', r'\1', src)
    src = re.sub(r'<code>(from [^<]+)</code>', r'\1', src)
    
    # Step 2: Fix parse_mode Markdown -> HTML  
    src = src.replace('parse_mode="Markdown"', 'parse_mode="HTML"')
    src = src.replace("parse_mode='Markdown'", "parse_mode='HTML'")
    
    # Step 3: Convert markdown syntax safely
    # Only convert **text** -> <b>text</b> inside string content
    # Match triple-quoted strings first, then single-quoted
    def convert_md_in_str(m):
        s = m.group(0)
        # Convert **bold**
        s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
        # Convert __bold__
        s = re.sub(r'__(.+?)__', r'<b>\1</b>', s)
        # Convert backtick code (but not triple backtick)
        s = re.sub(r'(?<!)`?(?!)([^\n]+)`?(?!)', r'<code>\1</code>', s)
        return s
    
    # Match string literals that are message content (not import lines)
    # Process lines: skip import lines, only process string-containing lines
    lines = src.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip import/from lines
        if stripped.startswith('import ') or stripped.startswith('from '):
            new_lines.append(line)
            continue
        # Convert markdown in string content on this line
        # Match f-string and regular string segments
        def replace_str(m):
            full = m.group(0)
            inner = m.group(2)
            prefix = m.group(1)
            quote = m.group(3)
            new_inner = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', inner)
            new_inner = re.sub(r'__(.+?)__', r'<b>\1</b>', new_inner)
            new_inner = re.sub(r'([^\n]+)', r'<code>\1</code>', new_inner)
            return prefix + new_inner + quote
        line = re.sub(r'(f?")([^"\\](?:[^"\\]|\\.)*?)(")', replace_str, line)
        new_lines.append(line)
    src = '\n'.join(new_lines)
    
    # Step 4: Fix misplaced import html (move to top)
    lines = src.split('\n')
    misplaced_idxs = [i for i, l in enumerate(lines) if l.strip() == 'import html' and i > 8]
    has_top_html = any(lines[i].strip() == 'import html' for i in range(9) if i < len(lines))
    if misplaced_idxs:
        for idx in sorted(misplaced_idxs, reverse=True):
            lines.pop(idx)
        if not has_top_html:
            # find last import line near top
            insert_at = 0
            for i, l in enumerate(lines[:20]):
                if l.startswith('import ') or l.startswith('from '):
                    insert_at = i
            lines.insert(insert_at + 1, 'import html')
        src = '\n'.join(lines)
    
    if src != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(src)
        return True
    return False

fixed = 0
for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for fname in files:
        if not fname.endswith('.py'):
            continue
        p = os.path.join(root, fname)
        if fix_file(p):
            fixed += 1
            print(f'FIXED: {p}')

print(f'\nTotal files fixed: {fixed}')

# Verify no syntax errors
import ast
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
            errors.append(f'SYNTAX ERROR {p}:{e.lineno}: {e.msg}')

if errors:
    print('\nSYNTAX ERRORS FOUND:')
    for e in errors:
        print(e)
else:
    print('All files syntax OK!')
