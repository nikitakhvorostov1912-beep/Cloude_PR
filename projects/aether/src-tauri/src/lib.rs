use reqwest::multipart;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::time::Duration;
use tokio::time::timeout;

// ─── RAII Temp File Cleanup ─────────────────────────────────────────────────

/// Автоматически удаляет временный файл при выходе из области видимости.
/// Гарантирует очистку даже при panic или раннем return.
struct TempFile(PathBuf);

impl TempFile {
    fn new(path: PathBuf) -> Self {
        Self(path)
    }

    fn path_str(&self) -> String {
        self.0.to_string_lossy().to_string()
    }
}

impl Drop for TempFile {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

// ─── FFmpeg Runner ──────────────────────────────────────────────────────────

/// Таймаут на одну ffmpeg операцию — 5 минут.
const FFMPEG_TIMEOUT: Duration = Duration::from_secs(300);

/// Таймаут на ffprobe — 30 секунд.
const FFPROBE_TIMEOUT: Duration = Duration::from_secs(30);

/// Таймаут на HTTP запрос к Whisper API — 10 минут на большой чанк.
const WHISPER_HTTP_TIMEOUT: Duration = Duration::from_secs(600);

/// Таймаут на обычные HTTP запросы (LLM, validation).
const HTTP_TIMEOUT: Duration = Duration::from_secs(300);

/// Запускает ffmpeg с таймаутом и -nostdin.
/// Использует tokio::process::Command — не блокирует async runtime.
async fn run_ffmpeg(args: &[&str], timeout_dur: Duration) -> Result<std::process::Output, String> {
    let mut cmd = tokio::process::Command::new("ffmpeg");
    cmd.arg("-nostdin"); // CRITICAL: не ждать stdin
    for arg in args {
        cmd.arg(arg);
    }
    // Скрываем stdin чтобы ffmpeg точно не пытался читать
    cmd.stdin(std::process::Stdio::null());

    let result = timeout(timeout_dur, cmd.output())
        .await
        .map_err(|_| format!("ffmpeg таймаут ({}с)", timeout_dur.as_secs()))?
        .map_err(|e| format!("ffmpeg не найден: {e}. Установите: https://ffmpeg.org/download.html"))?;

    Ok(result)
}

/// Запускает ffprobe с таймаутом.
async fn run_ffprobe(args: &[&str]) -> Result<std::process::Output, String> {
    let mut cmd = tokio::process::Command::new("ffprobe");
    for arg in args {
        cmd.arg(arg);
    }
    cmd.stdin(std::process::Stdio::null());

    let result = timeout(FFPROBE_TIMEOUT, cmd.output())
        .await
        .map_err(|_| format!("ffprobe таймаут ({}с)", FFPROBE_TIMEOUT.as_secs()))?
        .map_err(|e| format!("ffprobe не найден: {e}"))?;

    Ok(result)
}

// ─── Whisper ─────────────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize)]
pub struct WhisperApiResponse {
    pub text: String,
    pub language: Option<String>,
    pub duration: Option<f64>,
    pub segments: Option<serde_json::Value>,
}

/// Транскрипция аудио через OpenAI Whisper API.
/// API-ключ обрабатывается в Rust — не виден в DevTools браузера.
#[tauri::command]
async fn call_whisper_api(
    audio_bytes: Vec<u8>,
    filename: String,
    api_key: String,
) -> Result<String, String> {
    let client = reqwest::Client::builder()
        .timeout(WHISPER_HTTP_TIMEOUT)
        .build()
        .map_err(|e| format!("Ошибка создания HTTP клиента: {e}"))?;

    let file_part = multipart::Part::bytes(audio_bytes)
        .file_name(filename)
        .mime_str("audio/mpeg")
        .map_err(|e| format!("Ошибка создания multipart: {e}"))?;

    let form = multipart::Form::new()
        .text("model", "whisper-1")
        .text("response_format", "verbose_json")
        .text("language", "ru")
        .text("timestamp_granularities[]", "segment")
        .part("file", file_part);

    let response = client
        .post("https://api.openai.com/v1/audio/transcriptions")
        .header("Authorization", format!("Bearer {api_key}"))
        .multipart(form)
        .send()
        .await
        .map_err(|e| format!("Ошибка сети: {e}"))?;

    let status = response.status().as_u16();
    let body = response.text().await.map_err(|e| format!("Ошибка чтения ответа: {e}"))?;

    if status == 200 {
        Ok(body)
    } else {
        Err(format!("WHISPER_API_ERROR:{status}:{}", &body[..body.len().min(300)]))
    }
}

/// Проверка валидности OpenAI API-ключа.
#[tauri::command]
async fn validate_openai_key(api_key: String) -> Result<bool, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| e.to_string())?;

    let response = client
        .get("https://api.openai.com/v1/models")
        .header("Authorization", format!("Bearer {api_key}"))
        .send()
        .await
        .map_err(|e| format!("Нет подключения к API: {e}"))?;

    Ok(response.status().is_success())
}

// ─── LLM (OpenAI Chat Completions) ───────────────────────────────────────────

/// Запрос к OpenAI Chat Completions API.
/// API-ключ обрабатывается в Rust — не виден в DevTools браузера.
#[tauri::command]
async fn call_openai_api(body: String, api_key: String) -> Result<String, String> {
    let client = reqwest::Client::builder()
        .timeout(HTTP_TIMEOUT)
        .build()
        .map_err(|e| format!("Ошибка создания HTTP клиента: {e}"))?;

    let response = client
        .post("https://api.openai.com/v1/chat/completions")
        .header("Authorization", format!("Bearer {api_key}"))
        .header("Content-Type", "application/json")
        .body(body)
        .send()
        .await
        .map_err(|e| format!("Ошибка сети: {e}"))?;

    let status = response.status().as_u16();
    let resp_body = response.text().await.map_err(|e| format!("Ошибка чтения ответа: {e}"))?;

    if status == 200 {
        Ok(resp_body)
    } else {
        Err(format!("OPENAI_API_ERROR:{status}:{}", &resp_body[..resp_body.len().min(300)]))
    }
}

// ─── LLM (Anthropic Claude) ──────────────────────────────────────────────────

/// Запрос к Anthropic Messages API.
/// API-ключ обрабатывается в Rust — не виден в DevTools браузера.
#[tauri::command]
async fn call_claude_api(body: String, api_key: String) -> Result<String, String> {
    let client = reqwest::Client::builder()
        .timeout(HTTP_TIMEOUT)
        .build()
        .map_err(|e| format!("Ошибка создания HTTP клиента: {e}"))?;

    let response = client
        .post("https://api.anthropic.com/v1/messages")
        .header("x-api-key", &api_key)
        .header("anthropic-version", "2023-06-01")
        .header("Content-Type", "application/json")
        .body(body)
        .send()
        .await
        .map_err(|e| format!("Ошибка сети: {e}"))?;

    let status = response.status().as_u16();
    let resp_body = response.text().await.map_err(|e| format!("Ошибка чтения ответа: {e}"))?;

    if status == 200 {
        Ok(resp_body)
    } else {
        Err(format!("CLAUDE_API_ERROR:{status}:{}", &resp_body[..resp_body.len().min(300)]))
    }
}

/// Проверка валидности Claude API-ключа (минимальный тестовый запрос).
#[tauri::command]
async fn validate_claude_key(api_key: String) -> Result<bool, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| e.to_string())?;

    let body = serde_json::json!({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "test"}]
    });

    let response = client
        .post("https://api.anthropic.com/v1/messages")
        .header("x-api-key", &api_key)
        .header("anthropic-version", "2023-06-01")
        .header("Content-Type", "application/json")
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("Нет подключения к API: {e}"))?;

    let status = response.status().as_u16();
    Ok(status == 200 || status == 402)
}

// ─── Generic OpenAI-Compatible API ──────────────────────────────────────────

/// Универсальный вызов к любому OpenAI-совместимому API (Gemini, Groq, DeepSeek, OpenAI, MiMo).
#[tauri::command]
async fn call_openai_compatible_api(
    endpoint_url: String,
    body: String,
    api_key: String,
    auth_header_name: Option<String>,
) -> Result<String, String> {
    let client = reqwest::Client::builder()
        .timeout(HTTP_TIMEOUT)
        .build()
        .map_err(|e| format!("Ошибка создания HTTP клиента: {e}"))?;

    let mut request = client
        .post(&endpoint_url)
        .header("Content-Type", "application/json")
        .body(body);

    if let Some(header_name) = auth_header_name {
        request = request.header(&*header_name, &api_key);
    } else {
        request = request.header("Authorization", format!("Bearer {api_key}"));
    }

    let response = request
        .send()
        .await
        .map_err(|e| format!("Ошибка сети: {e}"))?;

    let status = response.status().as_u16();
    let resp_body = response.text().await.map_err(|e| format!("Ошибка чтения ответа: {e}"))?;

    if status == 200 {
        Ok(resp_body)
    } else {
        Err(format!("OPENAI_API_ERROR:{status}:{}", &resp_body[..resp_body.len().min(300)]))
    }
}

/// Универсальный Whisper API (OpenAI и Groq — одинаковый формат multipart).
#[tauri::command]
async fn call_whisper_compatible_api(
    endpoint_url: String,
    audio_bytes: Vec<u8>,
    filename: String,
    api_key: String,
    model: String,
) -> Result<String, String> {
    let client = reqwest::Client::builder()
        .timeout(WHISPER_HTTP_TIMEOUT)
        .build()
        .map_err(|e| format!("Ошибка создания HTTP клиента: {e}"))?;

    let file_part = multipart::Part::bytes(audio_bytes)
        .file_name(filename)
        .mime_str("audio/mpeg")
        .map_err(|e| format!("Ошибка создания multipart: {e}"))?;

    let form = multipart::Form::new()
        .text("model", model)
        .text("response_format", "verbose_json")
        .text("language", "ru")
        .text("timestamp_granularities[]", "segment")
        .part("file", file_part);

    let response = client
        .post(&endpoint_url)
        .header("Authorization", format!("Bearer {api_key}"))
        .multipart(form)
        .send()
        .await
        .map_err(|e| format!("Ошибка сети: {e}"))?;

    let status = response.status().as_u16();
    let resp_body = response.text().await.map_err(|e| format!("Ошибка чтения ответа: {e}"))?;

    if status == 200 {
        Ok(resp_body)
    } else {
        Err(format!("WHISPER_API_ERROR:{status}:{}", &resp_body[..resp_body.len().min(300)]))
    }
}

/// Проверка валидности API-ключа через GET к models endpoint.
#[tauri::command]
async fn validate_api_key_generic(
    validation_url: String,
    api_key: String,
) -> Result<bool, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| e.to_string())?;

    let response = client
        .get(&validation_url)
        .header("Authorization", format!("Bearer {api_key}"))
        .send()
        .await
        .map_err(|e| format!("Нет подключения к API: {e}"))?;

    Ok(response.status().is_success())
}

// ─── FFmpeg Audio Extraction ─────────────────────────────────────────────────

/// Извлекает аудиодорожку из видео/аудио через ffmpeg.
/// Принимает байты файла, конвертирует в MP3 mono 16kHz VBR.
/// Возвращает байты MP3.
#[tauri::command]
async fn extract_audio_ffmpeg(input_bytes: Vec<u8>, filename: String) -> Result<Vec<u8>, String> {
    let temp_dir = std::env::temp_dir();
    let pid = std::process::id();
    let ts = timestamp_ms();
    let ext = filename.rsplit('.').next().unwrap_or("tmp");
    let input_file = TempFile::new(temp_dir.join(format!("aether_in_{pid}_{ts}.{ext}")));
    let output_file = TempFile::new(temp_dir.join(format!("aether_out_{pid}_{ts}.mp3")));

    std::fs::write(&input_file.0, &input_bytes)
        .map_err(|e| format!("Не удалось записать временный файл: {e}"))?;

    eprintln!("[Aether] extract_audio_ffmpeg: {} КБ, формат: {ext}", input_bytes.len() / 1024);

    let input_str = input_file.path_str();
    let output_str = output_file.path_str();
    let result = run_ffmpeg(
        &["-y", "-i", &input_str, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-q:a", "5", &output_str],
        FFMPEG_TIMEOUT,
    ).await?;

    if !result.status.success() {
        let stderr = String::from_utf8_lossy(&result.stderr);
        return Err(format!("ffmpeg ошибка: {}", &stderr[..stderr.len().min(2000)]));
    }

    let audio_bytes = std::fs::read(&output_file.0)
        .map_err(|e| format!("Не удалось прочитать результат: {e}"))?;

    eprintln!("[Aether] extract_audio_ffmpeg: результат {} КБ", audio_bytes.len() / 1024);
    Ok(audio_bytes)
}

/// Извлекает аудио из файла ПО ПУТИ на диске.
/// Не загружает файл в память — ffmpeg читает напрямую.
#[tauri::command]
async fn extract_audio_from_path(input_path: String) -> Result<Vec<u8>, String> {
    if !std::path::Path::new(&input_path).exists() {
        return Err(format!("Файл не найден: {input_path}"));
    }

    let temp_dir = std::env::temp_dir();
    let pid = std::process::id();
    let ts = timestamp_ms();
    let output_file = TempFile::new(temp_dir.join(format!("aether_out_{pid}_{ts}.mp3")));

    eprintln!("[Aether] extract_audio_from_path: {input_path}");

    let output_str = output_file.path_str();
    let result = run_ffmpeg(
        &["-y", "-i", &input_path, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-q:a", "5", &output_str],
        FFMPEG_TIMEOUT,
    ).await?;

    if !result.status.success() {
        let stderr = String::from_utf8_lossy(&result.stderr);
        return Err(format!("ffmpeg ошибка: {}", &stderr[..stderr.len().min(2000)]));
    }

    let audio_bytes = std::fs::read(&output_file.0)
        .map_err(|e| format!("Не удалось прочитать результат: {e}"))?;

    eprintln!("[Aether] extract_audio_from_path: результат {} КБ", audio_bytes.len() / 1024);
    Ok(audio_bytes)
}

/// Разбивает аудиофайл на чанки для Whisper API (≤20 МБ каждый).
/// Стратегия:
/// 1. Конвертируем в MP3 mono 16kHz VBR (уменьшает размер, нормализует формат)
/// 2. Если результат ≤ max_chunk_mb — возвращаем как есть
/// 3. Если больше — пробуем ffprobe duration → split по времени
/// 4. Если ffprobe не даёт duration — split по размеру конвертированного MP3
#[tauri::command]
async fn split_audio_chunks(audio_bytes: Vec<u8>, max_chunk_mb: Option<f64>) -> Result<Vec<Vec<u8>>, String> {
    let max_mb = max_chunk_mb.unwrap_or(20.0);
    let max_bytes = (max_mb * 1024.0 * 1024.0) as usize;

    if audio_bytes.len() <= max_bytes {
        return Ok(vec![audio_bytes]);
    }

    let temp_dir = std::env::temp_dir();
    let pid = std::process::id();
    let ts = timestamp_ms();

    let ext = detect_audio_ext(&audio_bytes);
    let input_size_kb = audio_bytes.len() / 1024;
    eprintln!("[Aether] split_audio_chunks: вход {input_size_kb} КБ, формат: {ext}");

    let input_file = TempFile::new(temp_dir.join(format!("aether_split_in_{pid}_{ts}.{ext}")));
    std::fs::write(&input_file.0, &audio_bytes)
        .map_err(|e| format!("Не удалось записать временный файл: {e}"))?;

    // Шаг 1: конвертируем в MP3 mono 16kHz VBR
    let mp3_file = TempFile::new(temp_dir.join(format!("aether_split_mp3_{pid}_{ts}.mp3")));
    let input_str = input_file.path_str();
    let mp3_str = mp3_file.path_str();

    eprintln!("[Aether] Конвертация {ext} → mp3...");
    let convert = run_ffmpeg(
        &["-y", "-i", &input_str, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-q:a", "5", &mp3_str],
        FFMPEG_TIMEOUT,
    ).await?;

    // input_file удалится автоматически через Drop, но можно удалить раньше
    drop(input_file);

    if !convert.status.success() {
        let stderr = String::from_utf8_lossy(&convert.stderr);
        eprintln!("[Aether] ffmpeg stderr: {}", &stderr[..stderr.len().min(2000)]);
        return Err(format!("ffmpeg конвертация ошибка: {}", &stderr[..stderr.len().min(2000)]));
    }

    let mp3_bytes = std::fs::read(&mp3_file.0)
        .map_err(|e| format!("Не удалось прочитать MP3: {e}"))?;

    let mp3_size_kb = mp3_bytes.len() / 1024;
    eprintln!("[Aether] MP3 после конвертации: {mp3_size_kb} КБ");

    // Если после конвертации помещается — вернуть как есть
    if mp3_bytes.len() <= max_bytes {
        return Ok(vec![mp3_bytes]);
    }

    eprintln!("[Aether] Нужно разбить ({mp3_size_kb} КБ > {} КБ)", max_bytes / 1024);

    // Шаг 2: пробуем получить duration из MP3
    let probe = run_ffprobe(
        &["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", &mp3_str],
    ).await;

    let total_duration: Option<f64> = probe.ok().and_then(|p| {
        let s = String::from_utf8_lossy(&p.stdout).trim().to_string();
        s.parse::<f64>().ok().filter(|d| *d > 0.0)
    });

    let chunks = if let Some(duration) = total_duration {
        eprintln!("[Aether] Длительность: {duration:.1}с — split по времени");
        split_by_time(&mp3_str, &mp3_bytes, max_bytes, duration, pid, ts).await?
    } else {
        eprintln!("[Aether] Длительность неизвестна — split по размеру");
        split_by_size(mp3_bytes, max_bytes)
    };

    // mp3_file удалится автоматически через Drop

    if chunks.is_empty() {
        return Err("Не удалось разбить аудио на чанки".to_string());
    }

    eprintln!("[Aether] Разбито на {} чанков", chunks.len());
    Ok(chunks)
}

/// Split MP3 по времени через ffmpeg -ss/-t
async fn split_by_time(
    mp3_path: &str,
    mp3_bytes: &[u8],
    max_bytes: usize,
    total_duration: f64,
    pid: u32,
    ts: u128,
) -> Result<Vec<Vec<u8>>, String> {
    let temp_dir = std::env::temp_dir();

    let file_size = mp3_bytes.len() as f64;
    let chunk_duration = (max_bytes as f64 / file_size) * total_duration;
    let chunk_duration = (chunk_duration.floor() as u64).max(30);
    let num_chunks = ((total_duration / chunk_duration as f64).ceil() as usize).max(1);

    eprintln!("[Aether] split_by_time: {num_chunks} чанков по {chunk_duration}с");
    let mut chunks: Vec<Vec<u8>> = Vec::new();

    for i in 0..num_chunks {
        let start = i as u64 * chunk_duration;
        let chunk_file = TempFile::new(temp_dir.join(format!("aether_chunk_{pid}_{ts}_{i}.mp3")));
        let chunk_str = chunk_file.path_str();

        let start_str = start.to_string();
        let dur_str = chunk_duration.to_string();
        let result = run_ffmpeg(
            &[
                "-y", "-i", mp3_path,
                "-ss", &start_str,
                "-t", &dur_str,
                "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-q:a", "5",
                &chunk_str,
            ],
            FFMPEG_TIMEOUT,
        ).await?;

        if !result.status.success() {
            if i == num_chunks - 1 {
                break; // последний чанк может быть пустым
            }
            let stderr = String::from_utf8_lossy(&result.stderr);
            return Err(format!("ffmpeg ошибка чанк {i}: {}", &stderr[..stderr.len().min(2000)]));
        }

        match std::fs::read(&chunk_file.0) {
            Ok(bytes) if !bytes.is_empty() => {
                eprintln!("[Aether] Чанк {}/{num_chunks}: {} КБ", i + 1, bytes.len() / 1024);
                chunks.push(bytes);
            }
            _ => {}
        }
        // chunk_file удалится автоматически через Drop
    }

    Ok(chunks)
}

/// Split по размеру — fallback для файлов без duration.
fn split_by_size(data: Vec<u8>, max_bytes: usize) -> Vec<Vec<u8>> {
    data.chunks(max_bytes).map(|c| c.to_vec()).collect()
}

/// Определяет расширение аудиофайла по magic bytes.
fn detect_audio_ext(bytes: &[u8]) -> &'static str {
    if bytes.len() < 12 {
        return "webm";
    }
    // WebM/MKV: 0x1A 0x45 0xDF 0xA3
    if bytes[0..4] == [0x1A, 0x45, 0xDF, 0xA3] { return "webm"; }
    // MP3: 0xFF 0xFB / 0xFF 0xF3 / 0xFF 0xF2 или ID3 tag
    if (bytes[0] == 0xFF && (bytes[1] & 0xE0) == 0xE0) || &bytes[0..3] == b"ID3" { return "mp3"; }
    // WAV: RIFF....WAVE
    if &bytes[0..4] == b"RIFF" && &bytes[8..12] == b"WAVE" { return "wav"; }
    // OGG: OggS
    if &bytes[0..4] == b"OggS" { return "ogg"; }
    // FLAC: fLaC
    if &bytes[0..4] == b"fLaC" { return "flac"; }
    // MP4/M4A: ....ftyp
    if &bytes[4..8] == b"ftyp" { return "mp4"; }
    "webm"
}

/// Полный цикл: split + transcribe каждого чанка через Whisper API — всё в Rust.
/// Нет лишних копирований данных между JS и Rust.
/// Возвращает Vec<String> — JSON-ответы от API для каждого чанка.
#[tauri::command]
async fn transcribe_chunked(
    audio_bytes: Vec<u8>,
    endpoint_url: String,
    api_key: String,
    model: String,
    max_chunk_mb: Option<f64>,
) -> Result<Vec<String>, String> {
    let input_size_kb = audio_bytes.len() / 1024;
    eprintln!("[Aether] transcribe_chunked: вход {input_size_kb} КБ");

    let chunks = split_audio_chunks(audio_bytes, max_chunk_mb).await?;
    let total = chunks.len();
    eprintln!("[Aether] Разбито на {total} чанков, начинаю транскрипцию...");

    let client = reqwest::Client::builder()
        .timeout(WHISPER_HTTP_TIMEOUT)
        .build()
        .map_err(|e| format!("Ошибка создания HTTP клиента: {e}"))?;

    let mut results: Vec<String> = Vec::new();

    for (i, chunk) in chunks.into_iter().enumerate() {
        let chunk_size_kb = chunk.len() / 1024;
        eprintln!("[Aether] Транскрипция чанка {}/{total} ({chunk_size_kb} КБ)...", i + 1);

        let file_part = multipart::Part::bytes(chunk)
            .file_name(format!("chunk_{}.mp3", i + 1))
            .mime_str("audio/mpeg")
            .map_err(|e| format!("Ошибка создания multipart: {e}"))?;

        let form = multipart::Form::new()
            .text("model", model.clone())
            .text("response_format", "verbose_json")
            .text("language", "ru")
            .text("timestamp_granularities[]", "segment")
            .part("file", file_part);

        let response = client
            .post(&endpoint_url)
            .header("Authorization", format!("Bearer {api_key}"))
            .multipart(form)
            .send()
            .await
            .map_err(|e| format!("Ошибка сети чанк {}: {e}", i + 1))?;

        let status = response.status().as_u16();
        let body = response.text().await
            .map_err(|e| format!("Ошибка чтения ответа чанк {}: {e}", i + 1))?;

        if status != 200 {
            return Err(format!(
                "WHISPER_API_ERROR:{status}:chunk{}:{}",
                i + 1,
                &body[..body.len().min(300)]
            ));
        }

        eprintln!("[Aether] Чанк {}/{total} — OK ({} символов)", i + 1, body.len());
        results.push(body);
    }

    eprintln!("[Aether] Готово: {} чанков транскрибировано", results.len());
    Ok(results)
}

/// Проверяет доступность ffmpeg.
#[tauri::command]
async fn check_ffmpeg() -> Result<String, String> {
    let mut cmd = tokio::process::Command::new("ffmpeg");
    cmd.arg("-version");
    cmd.stdin(std::process::Stdio::null());

    let result = timeout(Duration::from_secs(5), cmd.output())
        .await
        .map_err(|_| "ffmpeg таймаут".to_string())?
        .map_err(|_| "ffmpeg не найден".to_string())?;

    if result.status.success() {
        Ok(String::from_utf8_lossy(&result.stdout).lines().next().unwrap_or("unknown").to_string())
    } else {
        Err("ffmpeg не работает".to_string())
    }
}

// ─── Утилиты ────────────────────────────────────────────────────────────────

fn timestamp_ms() -> u128 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
}

// ─── App entry ────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_stronghold::Builder::new(|password| {
            let config = argon2::Config {
                lanes: 4,
                mem_cost: 10_000,
                secret: &[],
                time_cost: 10,
                hash_length: 32,
                ..Default::default()
            };
            let salt_input = format!("aether-salt-{}", password.len());
            let salt_bytes = salt_input.as_bytes();
            argon2::hash_raw(password.as_bytes(), salt_bytes, &config)
                .expect("Ошибка деривации ключа Stronghold")
        })
        .build())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            call_whisper_api,
            validate_openai_key,
            call_openai_api,
            call_claude_api,
            validate_claude_key,
            call_openai_compatible_api,
            call_whisper_compatible_api,
            validate_api_key_generic,
            extract_audio_ffmpeg,
            extract_audio_from_path,
            split_audio_chunks,
            transcribe_chunked,
            check_ffmpeg,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
