use reqwest::multipart;
use serde::{Deserialize, Serialize};

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
        .timeout(std::time::Duration::from_secs(300)) // 5 минут
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
        .timeout(std::time::Duration::from_secs(10))
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
        .timeout(std::time::Duration::from_secs(120))
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
        .timeout(std::time::Duration::from_secs(120))
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
        .timeout(std::time::Duration::from_secs(10))
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
    // 200 или 402 (нет средств) = ключ валидный
    Ok(status == 200 || status == 402)
}

// ─── App entry ────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_stronghold::Builder::new(|password| {
            // Деривация ключа из пароля через argon2 (встроен в плагин)
            let config = argon2::Config {
                lanes: 4,
                mem_cost: 10_000,
                secret: &[],
                time_cost: 10,
                hash_length: 32,
                ..Default::default()
            };
            argon2::hash_raw(password.as_bytes(), b"aether-stronghold-salt-v1", &config)
                .expect("Ошибка деривации ключа Stronghold")
        })
        .build())
        .invoke_handler(tauri::generate_handler![
            call_whisper_api,
            validate_openai_key,
            call_openai_api,
            call_claude_api,
            validate_claude_key,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
