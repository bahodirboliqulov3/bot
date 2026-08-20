import os, re, ast

# Remove ALL HTML tags that were incorrectly inserted into Python source code lines
# A proper Python line should NOT start with <code>, <b>, etc.

def strip_html_from_code(src):
    # Remove HTML tags from ALL lines that are Python code (not string literals)
    # Strategy: parse line by line. If a line, when HTML-stripped, becomes valid Python code syntax,
    # then strip it. Otherwise leave it.
    
    # Simple approach: for each line, check if it has HTML tags AND starts with a code pattern
    lines = src.split('\n')
    result = []
    for line in lines:
        # If the line starts with <code>, <b>, <i> immediately (possibly with whitespace)
        if re.match(r'\s*<(?:code|b|i|/code|/b|/i)>', line):
            # Strip all HTML tags from this line
            clean = re.sub(r'</?(?:code|b|i)>', '', line)
            result.append(clean)
        else:
            # Still check if import-like lines have embedded tags that corrupt them
            # e.g. "from app.<b>bot</b>.handlers import foo"
            stripped_test = re.sub(r'</?(?:code|b|i)>', '', line)
            # If stripping HTML makes it look like a proper statement
            st = stripped_test.strip()
            if st.startswith(('import ', 'from ', 'class ', 'def ', 'async def ', '@', 'if ', 'for ', 'while ', 'with ', 'try', 'except', 'return', 'raise', 'yield')):
                if '<' in line and '>' in line:
                    result.append(stripped_test)
                    continue
            result.append(line)
    return '\n'.join(result)

total_fixed = 0
for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for fname in files:
        if not fname.endswith('.py'):
            continue
        p = os.path.join(root, fname)
        with open(p, 'r', encoding='utf-8') as f:
            src = f.read()
        
        cleaned = strip_html_from_code(src)
        if cleaned != src:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(cleaned)
            total_fixed += 1

print(f'Cleaned {total_fixed} files')

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
            errors.append((p, e.lineno, e.msg))

if errors:
    for p, ln, msg in errors:
        print(f'SYNTAX {p}:{ln}: {msg}')
        # Show the bad line
        with open(p, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if ln and ln <= len(lines):
            print(f'  LINE: {lines[ln-1].rstrip()}')
else:
    print('ALL SYNTAX OK!')
