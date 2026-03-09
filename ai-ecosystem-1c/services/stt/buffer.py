"""Audio buffer for accumulating PCM chunks before STT recognition."""

from __future__ import annotations


class AudioBuffer:
    """Accumulates PCM audio data and emits chunks of a target size."""

    def __init__(self, *, chunk_size: int = 32000) -> None:
        self._buffer = bytearray()
        self._chunk_size = chunk_size
        self._total_bytes = 0

    def append(self, data: bytes) -> list[bytes]:
        """Append data and return complete chunks ready for recognition."""
        self._buffer.extend(data)
        self._total_bytes += len(data)
        chunks: list[bytes] = []
        while len(self._buffer) >= self._chunk_size:
            chunks.append(bytes(self._buffer[: self._chunk_size]))
            self._buffer = self._buffer[self._chunk_size :]
        return chunks

    def flush(self) -> bytes | None:
        """Return remaining data (if any) and clear the buffer."""
        if not self._buffer:
            return None
        data = bytes(self._buffer)
        self._buffer.clear()
        return data

    @property
    def pending_bytes(self) -> int:
        return len(self._buffer)

    @property
    def total_bytes(self) -> int:
        return self._total_bytes

    def reset(self) -> None:
        self._buffer.clear()
        self._total_bytes = 0
