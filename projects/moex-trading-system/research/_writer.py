# -*- coding: utf-8 -*-
import pathlib

content = open(pathlib.Path(__file__).parent / '_content.md', 'r', encoding='utf-8').read()
out = pathlib.Path(r'C:\CLOUDE_PR\projects\moex-trading-system\research\04-moex-strategies.md')
out.write_text(content, encoding='utf-8')
print(f'Written {out.stat().st_size} bytes')
