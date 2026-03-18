import pathlib

out = pathlib.Path(r"C:CLOUDE_PRprojectsmoex-trading-systemesearch-moex-strategies.md")
content = pathlib.Path(r"C:CLOUDE_PRprojectsmoex-trading-systemesearch_content.txt").read_text(encoding="utf-8")
out.write_text(content, encoding="utf-8")
print(f"Written {out.stat().st_size} bytes")