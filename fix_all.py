import os
import re
import sys

def md_to_html_in_strings(src):
    # Replace **text** with <b>text</b>
    src = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', src)
    # Replace __text__ with <b>text</b>
    src = re.sub(r'__(.+?)__', r'<b>\1</b>', src)
    # Replace _text_ with <i>text</i>  
    src = re.sub(r'(?<![a-zA-Z_])_(.+?)_(?![a-zA-Z_])', r'<i>\1</i>', src)
    # Replace backtick code with <code>code</code>
    src = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', src)
    src = re.sub(r'([^\n]+)', r'<code>\1</code>', src)
    return src

fixed_files = 0
total_md_fixes = 0
total_import_fixes = 0
total_getbyphone_fixes = 0

for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if not f.endswith('.py'):
            continue
        p = os.path.join(root, f)
        with open(p, 'r', encoding='utf-8') as fp:
            src = fp.read()
        
        original = src
        changes = []

        # 1. Fix parse_mode Markdown -> HTML
        count_md = src.count('parse_mode="Markdown"') + src.count("parse_mode='Markdown'")
        if count_md > 0:
            src = src.replace('parse_mode="Markdown"', 'parse_mode="HTML"')
            src = src.replace("parse_mode='Markdown'", "parse_mode='HTML'")
            # Also convert markdown syntax in string literals
            src = md_to_html_in_strings(src)
            total_md_fixes += count_md
            changes.append(f'{count_md} Markdown->HTML')

        # 2. Fix misplaced import html (move to top after existing imports)
        lines = src.split('\n')
        misplaced = [i for i, l in enumerate(lines) if l.strip() == 'import html' and i > 7]
        if misplaced:
            # Check if import html already at top
            has_top_html = any(lines[i].strip() == 'import html' for i in range(8))
            for idx in sorted(misplaced, reverse=True):
                lines.pop(idx)
                total_import_fixes += 1
            if not has_top_html:
                # insert after first imports block
                insert_at = 0
                for i, l in enumerate(lines):
                    if l.startswith('import ') or l.startswith('from '):
                        insert_at = i
                    elif insert_at > 0 and not (l.startswith('import ') or l.startswith('from ') or l.strip() == ''):
                        break
                lines.insert(insert_at + 1, 'import html')
            src = '\n'.join(lines)
            changes.append('import html moved to top')

        if src != original:
            with open(p, 'w', encoding='utf-8') as fp:
                fp.write(src)
            fixed_files += 1
            print(f'FIXED [{", ".join(changes)}]: {p}')

print()
print(f'Summary:')
print(f'  Files fixed: {fixed_files}')
print(f'  Markdown->HTML fixes: {total_md_fixes}')
print(f'  Import order fixes: {total_import_fixes}')
print('Done!')
