import os, re, ast

fixes_applied = 0

for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if not f.endswith('.py'):
            continue
        p = os.path.join(root, f)
        with open(p, 'r', encoding='utf-8') as fp:
            src = fp.read()
        new_src = src
        # if name == "main": -> if __name__ == "__main__":
        new_src = new_src.replace('if name == "main":', 'if __name__ == "__main__":')
        new_src = new_src.replace("if name == 'main':", "if __name__ == '__main__':")
        new_src = new_src.replace("if name == '__main__':", "if __name__ == '__main__':")
        # logging.getLogger(name) -> logging.getLogger(__name__)
        new_src = new_src.replace('logging.getLogger(name)', 'logging.getLogger(__name__)')
        # super().init( -> super().__init__(
        new_src = new_src.replace('super().init(', 'super().__init__(')
        # __tablename__ = already fixed, skip
        
        if new_src != src:
            with open(p, 'w', encoding='utf-8') as fp:
                fp.write(new_src)
            fixes_applied += 1
            print(f'Fixed: {p}')

print(f'Fixes applied: {fixes_applied}')

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
            errors.append(f'{p}:{e.lineno}: {e.msg}')

if errors:
    for e in errors:
        print(e)
else:
    print('ALL SYNTAX OK!')
