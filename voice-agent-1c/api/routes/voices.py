"""Voice Preview API — тестирование и выбор голосов TTS.

GET  /api/voices           — список доступных голосов
POST /api/voices/preview   — синтез превью (WAV)
GET  /api/calls/{id}/audio — отдача записи звонка
"""
from __future__ import annotations

import io
import math
import struct
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Voices"])

# ── Каталог голосов Yandex SpeechKit ────────────────────────
YANDEX_VOICES = [
    {
        "id": "alena",
        "name": "Алёна",
        "gender": "female",
        "description": "Основной женский голос. Нейтральный, профессиональный тон.",
        "emotions": ["neutral", "good"],
        "sample_text": "Здравствуйте! Вы позвонили в компанию 1С-Франчайзи. Чем могу помочь?",
    },
    {
        "id": "filipp",
        "name": "Филипп",
        "gender": "male",
        "description": "Мужской голос. Спокойный, деловой стиль.",
        "emotions": ["neutral"],
        "sample_text": "Добрый день. Техническая поддержка 1С, слушаю вас.",
    },
    {
        "id": "ermil",
        "name": "Ермил",
        "gender": "male",
        "description": "Мужской голос. Дружелюбный, энергичный.",
        "emotions": ["neutral", "good"],
        "sample_text": "Здравствуйте! Рад помочь. Расскажите о вашей задаче.",
    },
    {
        "id": "jane",
        "name": "Джейн",
        "gender": "female",
        "description": "Женский голос. Мягкий, приятный тембр.",
        "emotions": ["neutral", "good", "evil"],
        "sample_text": "Добрый день! Компания франчайзи 1С. Как я могу вам помочь?",
    },
    {
        "id": "madirus",
        "name": "Мадирус",
        "gender": "male",
        "description": "Мужской голос. Глубокий, уверенный.",
        "emotions": ["neutral"],
        "sample_text": "Здравствуйте. Отдел технической поддержки. Слушаю вас внимательно.",
    },
    {
        "id": "omazh",
        "name": "Омаж",
        "gender": "female",
        "description": "Женский голос. Взрослый, авторитетный.",
        "emotions": ["neutral", "evil"],
        "sample_text": "Добрый день. Вы обратились в службу поддержки 1С.",
    },
    {
        "id": "zahar",
        "name": "Захар",
        "gender": "male",
        "description": "Мужской голос. Молодой, чёткая дикция.",
        "emotions": ["neutral", "good"],
        "sample_text": "Привет! Я голосовой помощник. Давайте разберёмся с вашим вопросом.",
    },
    {
        "id": "dasha",
        "name": "Даша",
        "gender": "female",
        "description": "Женский голос нового поколения. Естественный, выразительный.",
        "emotions": ["neutral", "friendly", "strict"],
        "sample_text": "Здравствуйте! Меня зовут Даша, я ваш виртуальный помощник.",
    },
    {
        "id": "julia",
        "name": "Юлия",
        "gender": "female",
        "description": "Женский голос. Тёплый, дружелюбный.",
        "emotions": ["neutral", "strict"],
        "sample_text": "Добрый день! Спасибо за звонок. Чем могу быть полезна?",
    },
    {
        "id": "lera",
        "name": "Лера",
        "gender": "female",
        "description": "Женский голос. Молодой, современный.",
        "emotions": ["neutral", "friendly"],
        "sample_text": "Привет! Готова помочь. Расскажите, что произошло.",
    },
    {
        "id": "alexander",
        "name": "Александр",
        "gender": "male",
        "description": "Мужской голос нового поколения. Естественный, нейтральный.",
        "emotions": ["neutral", "good"],
        "sample_text": "Здравствуйте. Я Александр, виртуальный ассистент компании.",
    },
    {
        "id": "kirill",
        "name": "Кирилл",
        "gender": "male",
        "description": "Мужской голос. Профессиональный, деловой.",
        "emotions": ["neutral", "strict", "good"],
        "sample_text": "Добрый день! Техподдержка 1С. Опишите вашу проблему.",
    },
]


class VoicePreviewRequest(BaseModel):
    """Запрос на синтез превью голоса."""

    voice_id: str = Field(description="ID голоса (alena, filipp, ...)")
    text: str = Field(
        default="",
        max_length=500,
        description="Текст для озвучки. Пусто = стандартная фраза.",
    )
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Скорость речи")
    emotion: str = Field(default="neutral", description="Эмоция голоса")


# ── Генератор WAV для демо (без Yandex API) ────────────────

def _generate_demo_wav(voice_id: str, text: str, speed: float) -> bytes:
    """Генерирует демо WAV с синтезированной речью через встроенный TTS.

    Создаёт тональный сигнал разной частоты для каждого голоса,
    чтобы можно было отличить голоса в demo-режиме.
    """
    sample_rate = 22050
    duration_seconds = max(1.5, min(len(text) * 0.06 / speed, 5.0))
    num_samples = int(sample_rate * duration_seconds)

    # Уникальная частота для каждого голоса
    voice_freqs = {
        "alena": (330, 440),
        "filipp": (220, 293),
        "ermil": (247, 330),
        "jane": (349, 466),
        "madirus": (196, 262),
        "omazh": (294, 392),
        "zahar": (262, 349),
        "dasha": (370, 494),
        "julia": (311, 415),
        "lera": (392, 523),
        "alexander": (233, 311),
        "kirill": (277, 370),
    }
    freq1, freq2 = voice_freqs.get(voice_id, (330, 440))

    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        # Плавный переход между двумя нотами + вибрато
        blend = 0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * t)
        freq = freq1 * blend + freq2 * (1 - blend)
        vibrato = 1 + 0.005 * math.sin(2 * math.pi * 5.5 * t)
        sample = 0.3 * math.sin(2 * math.pi * freq * vibrato * t)
        # Envelope: fade in/out
        env = min(t * 10, 1.0) * min((duration_seconds - t) * 10, 1.0)
        sample *= env
        samples.append(int(sample * 32767))

    # WAV header
    data_size = num_samples * 2  # 16-bit mono
    buf = io.BytesIO()
    # RIFF header
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    # fmt chunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))  # chunk size
    buf.write(struct.pack("<H", 1))  # PCM
    buf.write(struct.pack("<H", 1))  # mono
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", sample_rate * 2))  # byte rate
    buf.write(struct.pack("<H", 2))  # block align
    buf.write(struct.pack("<H", 16))  # bits per sample
    # data chunk
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    for s in samples:
        buf.write(struct.pack("<h", max(-32768, min(32767, s))))

    return buf.getvalue()


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 8000) -> bytes:
    """Конвертирует raw PCM (16-bit mono) в WAV."""
    buf = io.BytesIO()
    data_size = len(pcm_data)
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))
    buf.write(struct.pack("<H", 1))
    buf.write(struct.pack("<H", 1))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", sample_rate * 2))
    buf.write(struct.pack("<H", 2))
    buf.write(struct.pack("<H", 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(pcm_data)
    return buf.getvalue()


# ── Endpoints ───────────────────────────────────────────────

@router.get("/voices")
async def list_voices(request: Request):
    """Список доступных голосов с метаданными."""
    # Проверяем наличие Yandex API
    has_yandex = hasattr(request.app.state, "dialog_orchestrator")

    return {
        "voices": YANDEX_VOICES,
        "active_voice": _get_active_voice(request),
        "tts_available": has_yandex,
        "mode": "yandex" if has_yandex else "demo",
    }


@router.post("/voices/preview")
async def preview_voice(body: VoicePreviewRequest, request: Request):
    """Синтезирует превью голоса и возвращает WAV."""
    voice = next((v for v in YANDEX_VOICES if v["id"] == body.voice_id), None)
    if not voice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Голос '{body.voice_id}' не найден",
        )

    text = body.text or voice["sample_text"]

    # Попробуем Yandex TTS
    if hasattr(request.app.state, "dialog_orchestrator"):
        try:
            from services.tts import YandexTTSService

            orchestrator = request.app.state.dialog_orchestrator
            tts: YandexTTSService = orchestrator._tts

            # Создаём временный TTS с нужным голосом
            preview_tts = YandexTTSService(
                api_key=tts._api_key,
                folder_id=tts._folder_id,
                voice=body.voice_id,
                speed=body.speed,
                emotion=body.emotion,
                sample_rate=22050,
            )
            result = await preview_tts.synthesize(text)
            wav_data = _pcm_to_wav(result.audio_data, sample_rate=22050)
            logger.info("TTS превью: %s, %d байт", body.voice_id, len(wav_data))
            return Response(
                content=wav_data,
                media_type="audio/wav",
                headers={
                    "Content-Disposition": f'inline; filename="{body.voice_id}-preview.wav"',
                },
            )
        except Exception as e:
            logger.warning("Yandex TTS недоступен, используем демо: %s", e)

    # Fallback: demo WAV
    wav_data = _generate_demo_wav(body.voice_id, text, body.speed)
    logger.info("Демо превью: %s, %d байт", body.voice_id, len(wav_data))
    return Response(
        content=wav_data,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'inline; filename="{body.voice_id}-demo.wav"',
            "X-Voice-Mode": "demo",
        },
    )


@router.get("/calls/{call_id}/audio")
async def get_call_audio(call_id: str):
    """Отдаёт записанный WAV файл звонка."""
    # Безопасная проверка пути
    if "/" in call_id or "\\" in call_id or ".." in call_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный ID звонка",
        )

    base_dir = Path(__file__).resolve().parent.parent.parent / "data" / "recordings"
    wav_path = base_dir / call_id / "combined.wav"

    if not wav_path.exists():
        # Попробуем из PCM
        pcm_path = base_dir / call_id / "output.pcm"
        if pcm_path.exists():
            pcm_data = pcm_path.read_bytes()
            wav_data = _pcm_to_wav(pcm_data, sample_rate=8000)
            return Response(
                content=wav_data,
                media_type="audio/wav",
                headers={
                    "Content-Disposition": f'inline; filename="{call_id}.wav"',
                },
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись звонка не найдена",
        )

    wav_data = wav_path.read_bytes()
    return Response(
        content=wav_data,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'inline; filename="{call_id}.wav"',
        },
    )


def _get_active_voice(request: Request) -> str:
    """Возвращает текущий активный голос из конфига."""
    try:
        from orchestrator.config import get_settings

        return get_settings().yandex.tts_voice
    except Exception:
        return "alena"
