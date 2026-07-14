"""Inventory all `from db import` and `import db` usage in app/."""
import ast
from pathlib import Path
from collections import defaultdict

imports = defaultdict(set)
for py in Path('app').rglob('*.py'):
    if '__pycache__' in str(py):
        continue
    src = py.read_text(encoding='utf-8')
    tree = ast.parse(src)
    for node in ast.walk(tree):
        symbols = []
        if isinstance(node, ast.ImportFrom) and node.module == 'db':
            symbols = [n.name for n in node.names]
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name == 'db':
                    symbols = ['(import db as module)']
        for s in symbols:
            imports[s].add(str(py).replace('\\', '/'))

print('SYMBOL                              |  USAGE  |  FILES')
print('-' * 100)
for sym in sorted(imports.keys()):
    files = sorted(imports[sym])
    print(f'{sym:36} | {len(files):3}      | {", ".join(files)}')

print()
print(f'Total unique symbols: {len(imports)}')
print(f'Total import sites:   {sum(len(v) for v in imports.values())}')
print(f'Total files using db.py: {len(set(f for v in imports.values() for f in v))}')