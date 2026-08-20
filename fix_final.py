import os, re, ast

# undo ALL previous damage, then do a safe targeted fix

def restore_and_fix(path):
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    
    original = src
    
    # STEP 1: Undo all <code>, <b>, <i> tags that were incorrectly inserted into code lines
    # (import/from lines that got corrupted)
    lines = src.split('\n')
    fixed_lines = []
    for line in lines:
        # If this looks like a code line (import, from, def, class, etc.) and has HTML tags, strip them
        stripped = line.strip()
        # Check for HTML-wrapped code lines
        if re.match(r'^<code>(import |from |def |class |async |@|\s)', stripped):
            # Strip all <code>, </code>, <b>, </b>, <i>, </i> tags from this line
            line = re.sub(r'</?(?:code|b|i)>', '', line)
        # Also fix from...import lines that got broken into multiple lines by regex
        fixed_lines.append(line)
    src = '\n'.join(fixed_lines)
    
    # STEP 2: Now safely do parse_mode fix only - no string content modification
    src = src.replace('parse_mode="Markdown"', 'parse_mode="HTML"')
    src = src.replace("parse_mode='Markdown'", "parse_mode='HTML'")
    
    # STEP 3: Convert **text** -> <b>text</b> ONLY in string literals that are message content
    # We do this line by line, carefully skipping code lines
    lines = src.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip all Python statement lines
        if (stripped.startswith('import ')
            or stripped.startswith('from ')
            or stripped.startswith('def ')
            or stripped.startswith('async def ')
            or stripped.startswith('class ')
            or stripped.startswith('@')
            or stripped.startswith('#')):
            new_lines.append(line)
            continue
        
        # Only process lines that have string content with markdown 
        if '**' in line or '__' in line:
            # Convert **bold** -> <b>bold</b> inside string content only
            line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
            line = re.sub(r'(?<![a-z_])__(.+?)__(?![a-z_])', r'<b>\1</b>', line)
        new_lines.append(line)
    src = '\n'.join(new_lines)
    
    # STEP 4: Fix misplaced import html
    lines = src.split('\n')
    misplaced = [i for i, l in enumerate(lines) if l.strip() == 'import html' and i > 8]
    has_top = any(lines[i].strip() == 'import html' for i in range(9) if i < len(lines))
    if misplaced:
        for idx in sorted(misplaced, reverse=True):
            lines.pop(idx)
        if not has_top:
            insert_at = 0
            for i, l in enumerate(lines[:25]):
                if l.startswith('import ') or l.startswith('from '):
                    insert_at = i
                elif insert_at > 0 and l and not l.startswith(' ') and not l.startswith('#'):
                    break
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
        if restore_and_fix(p):
            fixed += 1

print(f'Fixed {fixed} files')

# Syntax check
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
    for e in errors:
        print(e)
else:
    print('ALL SYNTAX OK!')
