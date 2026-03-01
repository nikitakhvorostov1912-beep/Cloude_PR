# Memory — C:\CLOUDE_PR

## User Preferences
- **Skills location**: Always create skills in `C:\CLOUDE_PR\.claude\skills\` (global, for all projects)
- **Documentation format**: User prefers Word (.docx), not Markdown
- **Language**: Russian interface and documentation
- **UX priority**: Always think about user convenience — desktop shortcuts, auto-launch, minimal friction
- **OS**: Windows 10 Enterprise, no GPU on main machine

## Project: interview-to-bpmn
- See [project-interview-to-bpmn.md](project-interview-to-bpmn.md) for details

## Patterns
- For Streamlit apps: create `start.bat` + `start_silent.vbs` + desktop shortcut
- For ruff config: use `pyproject.toml` with `select = ["E", "F", "W", "I"]`
- For tests: `pytest` with `conftest.py` fixtures, config in `pyproject.toml`
