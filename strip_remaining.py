import os, re, ast

# Strip all remaining <code>, <b>, <i> tags from ALL Python files entirely
# These should not be in Python source at all - only in message text string values

def clean_html_tags(src):
    # Remove HTML tags from entire source, being careful about message strings
    # Strategy: remove <code>xxx</code>, <b>xxx</b>, <i>xxx</i> ONLY when they appear 
    # OUTSIDE of string literals that are Telegram message content
    # Actually, the damage is widespread - let's strip ALL HTML tags that are clearly wrong:
    # 1. In cascade= arguments
    # 2. In relationship() string arguments  
    # 3. In back_populates= arguments
    # 4. In class definitions
    # 5. In logging.getLogger(__name__) etc.
    
    # The safest approach: strip <code>, <b>, <i> tags ONLY when not surrounded by HTML message markers
    # Since our strings that SHOULD have HTML are things like "f<b>bold</b>" etc.
    # But cascade="<code>all, delete-orphan</code>" should NOT have tags
    
    # Find all <code>...</code> that wrap text which is NOT a proper HTML message context
    # Simple rule: if inside a Python identifier context (relationship args, logging, etc.), strip
    
    # Strip <code>text</code> -> text (where text doesn't contain angle brackets)
    src = re.sub(r'<code>([^<>]*)</code>', r'\1', src)
    # Strip <b>text</b> -> text  
    src = re.sub(r'<b>([^<>]*)</b>', r'\1', src)
    # Strip <i>text</i> -> text
    src = re.sub(r'<i>([^<>]*)</i>', r'\1', src)
    return src

total_fixed = 0
errors_after = []
for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for fname in files:
        if not fname.endswith('.py'):
            continue
        p = os.path.join(root, fname)
        with open(p, 'r', encoding='utf-8') as f:
            src = f.read()
        
        fixed = clean_html_tags(src)
        if fixed != src:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(fixed)
            total_fixed += 1

print(f'Cleaned {total_fixed} files')

# Syntax check
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
            errors_after.append(f'SYNTAX {p}:{e.lineno}: {e.msg}')

if errors_after:
    for e in errors_after:
        print(e)
else:
    print('ALL SYNTAX OK!')
