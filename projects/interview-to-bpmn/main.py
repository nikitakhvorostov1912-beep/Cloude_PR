"""Interview-to-BPMN: CLI entry point."""
import json
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from src.config import AppConfig, ProjectDir

app = typer.Typer(help="Interview-to-BPMN: Audio transcription to BPMN 2.0 diagrams")
console = Console()

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> AppConfig:
    """Load configuration from config.yaml."""
    return AppConfig.from_yaml(str(CONFIG_PATH))


@app.command()
def process(
    audio_path: str = typer.Argument(..., help="Path to audio file or directory"),
    project: str = typer.Option("default", help="Project name"),
    mode: str = typer.Option(None, help="Transcription mode: 'local_cpu', 'local' (GPU), or 'api'"),
    skip_transcription: bool = typer.Option(False, help="Skip transcription, use existing transcript"),
    skip_bpmn: bool = typer.Option(False, help="Skip BPMN generation"),
    skip_docs: bool = typer.Option(False, help="Skip document generation"),
):
    """Process audio interview: transcribe, analyze, generate BPMN and documents."""
    config = load_config()
    config_dict = config.to_dict()
    if mode:
        config_dict["transcription"]["mode"] = mode

    # Setup project directory
    project_dir = ProjectDir(project, config.project.data_dir)
    project_dir.ensure_dirs()

    console.print(Panel(f"[bold green]Interview-to-BPMN[/bold green]\nProject: {project}", title="Starting"))

    audio_file = Path(audio_path)
    if not audio_file.exists():
        console.print(f"[red]Error: File not found: {audio_path}[/red]")
        raise typer.Exit(1)

    # Step 1: Audio preprocessing
    if not skip_transcription:
        console.print("\n[bold cyan]Step 1/4: Audio preprocessing...[/bold cyan]")
        from src.transcription.preprocessor import preprocess_audio
        processed_path = preprocess_audio(str(audio_file), str(project_dir.audio), config_dict)
        console.print(f"  [green]Preprocessed: {processed_path}[/green]")

        # Step 2: Transcription + diarization
        console.print("\n[bold cyan]Step 2/4: Transcription + diarization...[/bold cyan]")
        from src.transcription.formatter import format_transcript
        from src.transcription.transcriber import transcribe
        raw_result = transcribe(processed_path, config_dict)
        transcript = format_transcript(raw_result)

        # Save transcript
        transcript_path = project_dir.transcripts / f"{audio_file.stem}.json"
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)
        console.print(f"  [green]Transcript saved: {transcript_path}[/green]")
    else:
        # Load existing transcript
        transcript_path = project_dir.transcripts / f"{audio_file.stem}.json"
        with open(transcript_path, encoding="utf-8") as f:
            transcript = json.load(f)
        console.print(f"  [yellow]Using existing transcript: {transcript_path}[/yellow]")

    # Step 3: AI analysis
    console.print("\n[bold cyan]Step 3/4: AI analysis (process extraction)...[/bold cyan]")
    from src.analysis.process_extractor import extract_processes, generate_bpmn_json
    processes = extract_processes(transcript, config_dict)

    # Save processes
    processes_path = project_dir.processes / f"{audio_file.stem}_processes.json"
    with open(processes_path, "w", encoding="utf-8") as f:
        json.dump(processes, f, ensure_ascii=False, indent=2)
    console.print(f"  [green]Processes saved: {processes_path}[/green]")

    # Step 4: BPMN generation
    if not skip_bpmn:
        console.print("\n[bold cyan]Step 4/4: BPMN generation...[/bold cyan]")
        from src.bpmn.json_to_bpmn import generate_bpmn_file
        from src.bpmn.renderer import render_bpmn

        generate_both = config.bpmn.generate_both_levels
        for proc in processes.get("processes", []):
            proc_id = proc.get("id", "process_1")
            levels = ["high_level", "detailed"] if generate_both else ["high_level"]
            for level in levels:
                bpmn_json = generate_bpmn_json(proc, config_dict, detail_level=level)
                bpmn_file = generate_bpmn_file(bpmn_json, str(project_dir.bpmn), proc_id, level)
                console.print(f"  [green]BPMN: {bpmn_file}[/green]")
                rendered = render_bpmn(bpmn_file, str(project_dir.output), config_dict)
                console.print(f"  [green]Image: {rendered}[/green]")

    # Step 5: Document generation
    if not skip_docs:
        console.print("\n[bold cyan]Generating documents...[/bold cyan]")
        from src.docs.doc_generator import generate_documents
        doc_files = generate_documents(processes, str(project_dir.root), config_dict)
        for doc_file in doc_files:
            console.print(f"  [green]Document: {doc_file}[/green]")

    console.print(Panel("[bold green]Processing complete![/bold green]", title="Done"))


@app.command()
def web():
    """Launch Streamlit web interface."""
    subprocess.run([sys.executable, "-m", "streamlit", "run", "src/web/app.py"])


@app.command()
def server():
    """Launch GPU transcription server (for local mode on second device)."""
    console.print("[bold cyan]Starting GPU transcription server...[/bold cyan]")
    console.print("Run this command on your GPU device:")
    console.print("[yellow]uvicorn src.transcription.gpu_server:app --host 0.0.0.0 --port 8000[/yellow]")


if __name__ == "__main__":
    app()
