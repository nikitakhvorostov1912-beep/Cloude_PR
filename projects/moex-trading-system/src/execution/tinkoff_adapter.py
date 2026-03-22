"""Compatibility shim — re-exports TinkoffAdapter as TinkoffExecutor."""
from src.execution.adapters.tinkoff import TinkoffAdapter

# main.py imports TinkoffExecutor
TinkoffExecutor = TinkoffAdapter

__all__ = ["TinkoffAdapter", "TinkoffExecutor"]
