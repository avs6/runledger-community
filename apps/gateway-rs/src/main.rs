use std::env;
use std::net::{IpAddr, SocketAddr};
use std::sync::Arc;
use std::time::Instant;

use axum::body::Body;
use axum::extract::{ConnectInfo, State};
use axum::http::{HeaderMap, HeaderValue, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use chrono::Utc;
use futures_util::StreamExt;
use hmac::{Hmac, Mac};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::Sha256;
use tracing::{error, info};
use uuid::Uuid;

type HmacSha256 = Hmac<Sha256>;

#[derive(Clone)]
struct AppState {
    http: Client,
    control_plane_url: String,
    admin_secret: String,
    event_signing_secret: String,
    /// Proxies whose X-Forwarded-For is believed (RUNLEDGER_GATEWAY_TRUSTED_PROXIES).
    trusted_proxies: Vec<IpNet>,
    /// Ceiling for control-plane calls (preflight, finalize, events…), so a stuck API
    /// can't hang requests forever (RUNLEDGER_CONTROL_PLANE_TIMEOUT_MS; review G-22).
    control_plane_timeout: std::time::Duration,
}

#[derive(Debug, Serialize)]
struct RuntimePreflightRequest {
    raw_key: String,
    body: Value,
    end_user_id: Option<String>,
    tags_header: Option<String>,
    region_header: Option<String>,
    timeout_ms: Option<i64>,
    completion_timeout_ms: Option<i64>,
    stream_timeout_ms: Option<i64>,
    client_ip: Option<String>,
}

#[derive(Debug, Deserialize)]
struct RuntimeExecutionStep {
    route_id: String,
    alias: String,
    provider: String,
    target_model: String,
    execution_mode: String,
    base_url: Option<String>,
    api_key_env_var: Option<String>,
    priority: i64,
    timeout_ms: Option<i64>,
    retry_count: i64,
    region: Option<String>,
    deployment_status: String,
    trigger: String,
    required_error_triggers: Vec<String>,
    decision_reason: Option<String>,
    request_method: String,
    request_url: Option<String>,
    request_headers: std::collections::HashMap<String, String>,
    request_body: Value,
    #[serde(default)]
    response_format: Option<String>,
    #[serde(default)]
    provider_stream_format: Option<String>,
    #[serde(default)]
    mirror_sample_pct: f64,
}

#[derive(Debug, Deserialize)]
struct RuntimePreflightResponse {
    api_key_id: Option<String>,
    workspace_id: String,
    tenant_id: String,
    auth_mode: String,
    model_requested: String,
    route_alias: String,
    preferred_region: Option<String>,
    request_tags: Vec<String>,
    missing_metadata: Vec<String>,
    cache_hit_kind: Option<String>,
    cached_response: Option<Value>,
    // Echoed on finalize so cache lookup and store use the same key and scope.
    #[serde(default)]
    cache_key: Option<String>,
    #[serde(default)]
    semantic_scope: Option<String>,
    prepared_messages: Vec<Value>,
    effective_tools: Option<Vec<Value>>,
    effective_reasoning_effort: Option<String>,
    compiler_enabled: bool,
    compiler_config: Option<Value>,
    semantic_cache_enabled: bool,
    guardrails_enabled: bool,
    ir_decision: Option<Value>,
    decision_reason: Option<String>,
    execution_steps: Vec<RuntimeExecutionStep>,
    /// Minted by preflight; echoed on finalize, mirror and runtime events so the
    /// request row, its guardrail events and its run share one id (review G-19).
    #[serde(default)]
    request_id: Option<String>,
    /// Structured "why" record, echoed on finalize and stored on the run.
    #[serde(default)]
    decision: Option<Value>,
    /// `cache=…; budget=…; guardrail=…`, completed with the served route below.
    #[serde(default)]
    decision_header: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
struct RuntimeFinalizeRequest {
    workspace_id: String,
    route_id: String,
    api_key_id: Option<String>,
    model_requested: String,
    prepared_messages: Vec<Value>,
    response_json: Value,
    request_metadata: Value,
    request_tags: Vec<String>,
    latency_ms: Option<i64>,
    total_wall_ms: Option<i64>,
    decision_reason: Option<String>,
    end_user_id: Option<String>,
    cache: bool,
    semantic_cache_enabled: bool,
    guardrails_enabled: bool,
    compiler_enabled: bool,
    compiler_config: Option<Value>,
    ir_decision: Option<Value>,
    cache_key: Option<String>,
    semantic_scope: Option<String>,
    request_id: Option<String>,
    decision: Option<Value>,
}

#[derive(Debug, Serialize)]
struct RuntimeProviderExecuteRequest {
    route_id: String,
    request_body: Value,
    stream: bool,
    timeout_ms: Option<i64>,
}

#[derive(Debug, Serialize)]
struct RuntimeRouteResultRequest {
    route_id: String,
    success: bool,
    transient: bool,
    error_detail: Option<String>,
}

#[derive(Debug, Serialize)]
struct RuntimeMirrorRequest {
    workspace_id: String,
    route_id: String,
    model_requested: String,
    request_body: Value,
    response_json: Value,
    request_tags: Vec<String>,
    preferred_region: Option<String>,
    sampled: bool,
    api_key_id: Option<String>,
    end_user_id: Option<String>,
    request_metadata: Value,
    request_id: Option<String>,
}

#[derive(Serialize)]
struct RuntimeEventBatch {
    workspace_id: String,
    source_service: String,
    events: Vec<Value>,
}

struct ProviderFailure {
    upstream_status: Option<u16>,
    body: String,
    transient: bool,
    classified_triggers: Vec<String>,
    /// Provider's Retry-After, in milliseconds, when it sent one.
    retry_after_ms: Option<u64>,
}

enum ProviderSuccess {
    Json {
        response_json: Value,
        latency_ms: i64,
    },
    Stream {
        response: Response,
        latency_ms: i64,
    },
}

// ── Response normalizers ────────────────────────────────────────────────────────

fn normalize_bedrock_converse(raw: &Value, model: &str) -> Value {
    let output = raw.get("output").unwrap_or(&Value::Null);
    let message = output.get("message").unwrap_or(&Value::Null);
    let content_blocks = message.get("content").and_then(|c| c.as_array());
    let text = content_blocks
        .map(|blocks| {
            blocks
                .iter()
                .filter_map(|b| b.get("text").and_then(|t| t.as_str()))
                .collect::<Vec<_>>()
                .join(" ")
        })
        .unwrap_or_default();
    let usage = raw.get("usage").unwrap_or(&Value::Null);
    let input_tokens = usage
        .get("inputTokens")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);
    let output_tokens = usage
        .get("outputTokens")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);
    let stop_reason = raw
        .get("stopReason")
        .and_then(|v| v.as_str())
        .unwrap_or("end_turn");
    let finish_reason = match stop_reason {
        "end_turn" | "stop_sequence" => "stop",
        "max_tokens" => "length",
        other => other,
    };
    openai_response(model, &text, input_tokens, output_tokens, finish_reason)
}

fn normalize_gemini(raw: &Value, model: &str) -> Value {
    let candidates = raw.get("candidates").and_then(|c| c.as_array());
    let first = candidates.and_then(|c| c.first()).unwrap_or(&Value::Null);
    let parts = first
        .get("content")
        .and_then(|c| c.get("parts"))
        .and_then(|p| p.as_array());
    let text = parts
        .map(|ps| {
            ps.iter()
                .filter_map(|p| p.get("text").and_then(|t| t.as_str()))
                .collect::<Vec<_>>()
                .join("")
        })
        .unwrap_or_default();
    let finish_raw = first
        .get("finishReason")
        .and_then(|v| v.as_str())
        .unwrap_or("STOP");
    let finish_reason = match finish_raw {
        "STOP" => "stop",
        "MAX_TOKENS" => "length",
        "SAFETY" => "content_filter",
        other => other,
    };
    let meta = raw.get("usageMetadata").unwrap_or(&Value::Null);
    let input_tokens = meta
        .get("promptTokenCount")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);
    let output_tokens = meta
        .get("candidatesTokenCount")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);
    openai_response(model, &text, input_tokens, output_tokens, finish_reason)
}

fn openai_response(
    model: &str,
    content: &str,
    input_tokens: u64,
    output_tokens: u64,
    finish_reason: &str,
) -> Value {
    json!({
        "id": format!("rl-gw-{}", Uuid::new_v4().simple()),
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": finish_reason,
        }],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
    })
}

fn maybe_normalize_response(raw: Value, step: &RuntimeExecutionStep) -> Value {
    match step.response_format.as_deref() {
        Some("bedrock_converse") => normalize_bedrock_converse(&raw, &step.target_model),
        Some("gemini") => normalize_gemini(&raw, &step.target_model),
        _ => raw,
    }
}

// ── Streaming format converters ─────────────────────────────────────────────────

fn sse_chunk(content: &str, model: &str, finish: bool) -> Vec<u8> {
    let chunk = json!({
        "id": "rl-gw-chunk",
        "object": "chat.completion.chunk",
        "model": model,
        "choices": [{
            "index": 0,
            "delta": if finish { json!({}) } else { json!({"content": content}) },
            "finish_reason": if finish { Value::String("stop".into()) } else { Value::Null },
        }]
    });
    format!("data: {}\n\n", chunk).into_bytes()
}

fn convert_gemini_sse_to_openai(line: &str, model: &str) -> Option<Vec<u8>> {
    if !line.starts_with("data: ") {
        return None;
    }
    let raw_str = line[6..].trim();
    if raw_str.is_empty() || raw_str == "[DONE]" {
        return None;
    }
    let raw: Value = serde_json::from_str(raw_str).ok()?;
    let candidates = raw.get("candidates")?.as_array()?;
    let first = candidates.first()?;
    let parts = first.get("content")?.get("parts")?.as_array()?;
    let text: String = parts
        .iter()
        .filter_map(|p| p.get("text").and_then(|t| t.as_str()))
        .collect();
    if text.is_empty() {
        return None;
    }
    Some(sse_chunk(&text, model, false))
}

fn parse_bedrock_event_stream_chunk(data: &[u8]) -> Vec<(String, Vec<u8>)> {
    let mut events = Vec::new();
    let mut offset = 0;
    while offset + 12 <= data.len() {
        let total_len = u32::from_be_bytes([
            data[offset],
            data[offset + 1],
            data[offset + 2],
            data[offset + 3],
        ]) as usize;
        if total_len < 16 || offset + total_len > data.len() {
            break;
        }
        let headers_len = u32::from_be_bytes([
            data[offset + 4],
            data[offset + 5],
            data[offset + 6],
            data[offset + 7],
        ]) as usize;
        let headers_start = offset + 12;
        let headers_end = headers_start + headers_len;
        if headers_end > offset + total_len {
            break;
        }
        let mut event_type = String::new();
        let mut hdr_offset = headers_start;
        while hdr_offset < headers_end {
            if hdr_offset >= data.len() {
                break;
            }
            let name_len = data[hdr_offset] as usize;
            hdr_offset += 1;
            if hdr_offset + name_len > headers_end {
                break;
            }
            let name =
                String::from_utf8_lossy(&data[hdr_offset..hdr_offset + name_len]).to_string();
            hdr_offset += name_len;
            if hdr_offset + 3 > headers_end {
                break;
            }
            let _header_type = data[hdr_offset];
            hdr_offset += 1;
            let value_len = u16::from_be_bytes([data[hdr_offset], data[hdr_offset + 1]]) as usize;
            hdr_offset += 2;
            if hdr_offset + value_len > headers_end {
                break;
            }
            let value =
                String::from_utf8_lossy(&data[hdr_offset..hdr_offset + value_len]).to_string();
            hdr_offset += value_len;
            if name == ":event-type" {
                event_type = value;
            }
        }
        let payload_start = headers_end;
        let payload_end = offset + total_len - 4;
        let payload = if payload_end > payload_start {
            data[payload_start..payload_end].to_vec()
        } else {
            Vec::new()
        };
        events.push((event_type, payload));
        offset += total_len;
    }
    events
}

fn bedrock_event_to_openai_sse(event_type: &str, payload: &[u8], model: &str) -> Option<Vec<u8>> {
    match event_type {
        "contentBlockDelta" => {
            let v: Value = serde_json::from_slice(payload).ok()?;
            let text = v.get("delta")?.get("text")?.as_str()?;
            if text.is_empty() {
                return None;
            }
            Some(sse_chunk(text, model, false))
        }
        "messageStop" => Some(sse_chunk("", model, true)),
        _ => None,
    }
}

// ── Main ────────────────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            env::var("RUST_LOG")
                .unwrap_or_else(|_| "runledger_gateway_rs=info,tower_http=info".to_string()),
        )
        .init();

    let control_plane_url = env::var("RUNLEDGER_CONTROL_PLANE_URL")
        .unwrap_or_else(|_| "http://runledger-api:8000".to_string())
        .trim_end_matches('/')
        .to_string();
    let admin_secret = env::var("RUNLEDGER_CONTROL_PLANE_ADMIN_SECRET")
        .or_else(|_| env::var("ADMIN_SECRET"))
        .expect("RUNLEDGER_CONTROL_PLANE_ADMIN_SECRET or ADMIN_SECRET must be set");
    let event_signing_secret =
        env::var("RUNLEDGER_GATEWAY_EVENT_SIGNING_SECRET").unwrap_or_else(|_| admin_secret.clone());
    let bind = env::var("RUNLEDGER_GATEWAY_BIND").unwrap_or_else(|_| "0.0.0.0:8210".to_string());
    let trusted_proxies =
        parse_trusted_proxies(&env::var("RUNLEDGER_GATEWAY_TRUSTED_PROXIES").unwrap_or_default());
    info!(
        "trusted proxies for X-Forwarded-For: {}",
        trusted_proxies.len()
    );

    let control_plane_timeout = std::time::Duration::from_millis(
        env::var("RUNLEDGER_CONTROL_PLANE_TIMEOUT_MS")
            .ok()
            .and_then(|v| v.parse::<u64>().ok())
            .filter(|ms| *ms > 0)
            .unwrap_or(30_000),
    );
    let http = Client::builder()
        .connect_timeout(std::time::Duration::from_secs(5))
        .pool_idle_timeout(std::time::Duration::from_secs(90))
        .build()
        .expect("http client");

    let state = Arc::new(AppState {
        http,
        control_plane_url,
        admin_secret,
        event_signing_secret,
        trusted_proxies,
        control_plane_timeout,
    });

    let app = Router::new()
        .route("/health/live", get(health_live))
        .route("/health/ready", get(health_ready))
        .route("/gateway/chat/completions", post(gateway_chat_completions))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(&bind)
        .await
        .unwrap_or_else(|err| panic!("failed to bind {}: {}", bind, err));
    info!("runledger-gateway-rs listening on {}", bind);
    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .await
    .unwrap();
}

async fn health_live() -> impl IntoResponse {
    Json(json!({"ok": true, "service": "runledger-gateway-rs"}))
}

async fn health_ready(State(state): State<Arc<AppState>>) -> Response {
    let url = format!("{}/health/live", state.control_plane_url);
    match state
        .http
        .get(url)
        .timeout(state.control_plane_timeout)
        .send()
        .await
    {
        Ok(resp) if resp.status().is_success() => {
            Json(json!({"ok": true, "ready": true})).into_response()
        }
        Ok(resp) => (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(json!({"ok": false, "detail": format!("control plane unhealthy: {}", resp.status())})),
        )
            .into_response(),
        Err(err) => (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(json!({"ok": false, "detail": format!("control plane unreachable: {}", err)})),
        )
            .into_response(),
    }
}

async fn gateway_chat_completions(
    State(state): State<Arc<AppState>>,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    headers: HeaderMap,
    Json(body): Json<Value>,
) -> Response {
    // Whole-request clock: total_wall_ms minus provider latency is the gateway's own
    // overhead (preflight, routing, control-plane hops) (review G-15).
    let request_started = Instant::now();
    let auth_header = match headers
        .get("authorization")
        .and_then(|value| value.to_str().ok())
    {
        Some(value) if value.starts_with("Bearer ") => value.to_string(),
        _ => {
            return (
                StatusCode::UNAUTHORIZED,
                Json(json!({"detail": "Missing bearer token"})),
            )
                .into_response()
        }
    };
    let raw_key = auth_header.trim_start_matches("Bearer ").trim().to_string();
    let stream = body
        .get("stream")
        .and_then(|value| value.as_bool())
        .unwrap_or(false);
    let end_user_id = header_value(&headers, "x-runledger-end-user-id");
    let tags_header = header_value(&headers, "x-runledger-tags");
    let region_header = header_value(&headers, "x-runledger-region");
    let timeout_ms =
        header_value(&headers, "x-runledger-timeout-ms").and_then(|v| v.parse::<i64>().ok());
    let completion_timeout_ms = header_value(&headers, "x-runledger-completion-timeout-ms")
        .and_then(|v| v.parse::<i64>().ok());
    let stream_timeout_ms =
        header_value(&headers, "x-runledger-stream-timeout-ms").and_then(|v| v.parse::<i64>().ok());
    // The socket peer, or — only when the peer is a trusted proxy — the right-most
    // untrusted X-Forwarded-For hop, so clients can't claim an allow-listed IP (G-18).
    let client_ip = Some(
        client_ip_from(
            peer.ip(),
            header_value(&headers, "x-forwarded-for").as_deref(),
            &state.trusted_proxies,
        )
        .to_string(),
    );

    let preflight = match call_preflight(
        &state,
        RuntimePreflightRequest {
            raw_key,
            body: body.clone(),
            end_user_id: end_user_id.clone(),
            tags_header,
            region_header,
            timeout_ms,
            completion_timeout_ms,
            stream_timeout_ms,
            client_ip,
        },
    )
    .await
    {
        Ok(preflight) => preflight,
        Err(response) => return response,
    };

    if let Some(cached) = preflight.cached_response {
        let mut response = (StatusCode::OK, Json(cached)).into_response();
        let kind = preflight.cache_hit_kind.as_deref().unwrap_or("exact");
        if let Ok(value) = HeaderValue::from_str(kind) {
            response.headers_mut().insert("x-runledger-cache", value);
        }
        set_decision_header(&mut response, preflight.decision_header.as_deref(), None);
        return response;
    }
    if preflight.execution_steps.is_empty() {
        return (
            StatusCode::BAD_GATEWAY,
            Json(json!({"detail": "gateway preflight returned no execution steps"})),
        )
            .into_response();
    }

    let mut last_error_body = String::new();
    let mut last_upstream_status = None;
    let mut last_route_id = None;
    let mut last_error_triggers: Vec<String> = Vec::new();
    // After a non-transient failure (400/403/413…) only steps whose error triggers match
    // it can help; plain fallbacks are skipped and, if none matches, the provider's
    // status is returned instead of 502 (review G-11).
    let mut last_failure_transient = true;
    let started_at = Utc::now().to_rfc3339();
    let request_id = preflight.request_id.clone().unwrap_or_else(uuid_like);

    for step in &preflight.execution_steps {
        if !step_runs_after(
            &step.required_error_triggers,
            &last_error_triggers,
            last_failure_transient,
        ) {
            continue;
        }
        last_route_id = Some(step.route_id.clone());
        let max_attempts = std::cmp::max(1_i64, step.retry_count + 1);
        for attempt in 0..max_attempts {
            match execute_step(&state, step, stream).await {
                Ok(ProviderSuccess::Stream {
                    response,
                    latency_ms,
                }) => {
                    let event = json!({
                        "event_type": "gateway.request.completed",
                        "request_id": request_id.clone(),
                        "workspace_id": preflight.workspace_id,
                        "route_id": step.route_id,
                        "model_requested": preflight.model_requested,
                        "model_used": step.target_model,
                        "provider": step.provider,
                        "status": "success",
                        "decision_reason": step.decision_reason.clone().or(preflight.decision_reason.clone()),
                        "cache_hit": false,
                        "semantic_cache_hit": false,
                        "stream": true,
                        "latency_ms": latency_ms,
                        "started_at": started_at,
                        "completed_at": Utc::now().to_rfc3339()
                    });
                    if let Err(err) =
                        emit_runtime_events(&state, &preflight.workspace_id, vec![event]).await
                    {
                        error!("runtime event emit failed: {}", err);
                    }
                    // Meter streamed calls (review G-03): tee the stream and, once it ends
                    // (or the client disconnects), finalize with the reassembled completion.
                    let finalize_template = RuntimeFinalizeRequest {
                        workspace_id: preflight.workspace_id.clone(),
                        route_id: step.route_id.clone(),
                        api_key_id: preflight.api_key_id.clone(),
                        model_requested: preflight.model_requested.clone(),
                        prepared_messages: preflight.prepared_messages.clone(),
                        response_json: Value::Null,
                        request_metadata: body
                            .get("metadata")
                            .cloned()
                            .unwrap_or_else(|| json!({})),
                        request_tags: preflight.request_tags.clone(),
                        latency_ms: Some(latency_ms),
                        total_wall_ms: Some(request_started.elapsed().as_millis() as i64),
                        decision_reason: step
                            .decision_reason
                            .clone()
                            .or(preflight.decision_reason.clone()),
                        end_user_id: end_user_id.clone(),
                        // Streamed answers aren't written to the response cache, and the
                        // answer is already delivered, so post-call guardrails can't block
                        // it — finalize only records the call.
                        cache: false,
                        semantic_cache_enabled: false,
                        guardrails_enabled: false,
                        compiler_enabled: preflight.compiler_enabled,
                        compiler_config: preflight.compiler_config.clone(),
                        ir_decision: preflight.ir_decision.clone(),
                        cache_key: preflight.cache_key.clone(),
                        semantic_scope: preflight.semantic_scope.clone(),
                        request_id: Some(request_id.clone()),
                        decision: preflight.decision.clone(),
                    };
                    let mut streamed = tee_stream_for_finalize(
                        response,
                        state.clone(),
                        finalize_template,
                        step.target_model.clone(),
                    );
                    set_decision_header(
                        &mut streamed,
                        preflight.decision_header.as_deref(),
                        Some(step),
                    );
                    return streamed;
                }
                Ok(ProviderSuccess::Json {
                    response_json,
                    latency_ms,
                }) => {
                    match call_finalize(
                        &state,
                        RuntimeFinalizeRequest {
                            workspace_id: preflight.workspace_id.clone(),
                            route_id: step.route_id.clone(),
                            api_key_id: preflight.api_key_id.clone(),
                            model_requested: preflight.model_requested.clone(),
                            prepared_messages: preflight.prepared_messages.clone(),
                            response_json: response_json.clone(),
                            request_metadata: body
                                .get("metadata")
                                .cloned()
                                .unwrap_or_else(|| json!({})),
                            request_tags: preflight.request_tags.clone(),
                            latency_ms: Some(latency_ms),
                            total_wall_ms: Some(request_started.elapsed().as_millis() as i64),
                            decision_reason: step
                                .decision_reason
                                .clone()
                                .or(preflight.decision_reason.clone()),
                            end_user_id: end_user_id.clone(),
                            cache: body
                                .get("cache")
                                .and_then(|value| value.as_bool())
                                .unwrap_or(true),
                            semantic_cache_enabled: preflight.semantic_cache_enabled,
                            guardrails_enabled: preflight.guardrails_enabled,
                            compiler_enabled: preflight.compiler_enabled,
                            compiler_config: preflight.compiler_config.clone(),
                            ir_decision: preflight.ir_decision.clone(),
                            cache_key: preflight.cache_key.clone(),
                            semantic_scope: preflight.semantic_scope.clone(),
                            request_id: Some(request_id.clone()),
                            decision: preflight.decision.clone(),
                        },
                    )
                    .await
                    {
                        Ok(()) => {
                            // Shadow traffic: sample here and fire it in the background,
                            // so the user never waits for the mirror model (review G-12).
                            if mirror_sampled(step.mirror_sample_pct) {
                                let mirror_state = state.clone();
                                let payload = RuntimeMirrorRequest {
                                    workspace_id: preflight.workspace_id.clone(),
                                    route_id: step.route_id.clone(),
                                    model_requested: preflight.model_requested.clone(),
                                    request_body: step.request_body.clone(),
                                    response_json: response_json.clone(),
                                    request_tags: preflight.request_tags.clone(),
                                    preferred_region: preflight.preferred_region.clone(),
                                    sampled: true,
                                    api_key_id: preflight.api_key_id.clone(),
                                    end_user_id: end_user_id.clone(),
                                    request_metadata: body
                                        .get("metadata")
                                        .cloned()
                                        .unwrap_or_else(|| json!({})),
                                    request_id: Some(request_id.clone()),
                                };
                                tokio::spawn(async move {
                                    if let Err(err) = call_mirror(&mirror_state, payload).await {
                                        error!("mirror call failed: {}", err);
                                    }
                                });
                            }
                            let mut ok = (StatusCode::OK, Json(response_json)).into_response();
                            set_decision_header(
                                &mut ok,
                                preflight.decision_header.as_deref(),
                                Some(step),
                            );
                            return ok;
                        }
                        Err(response) => return response,
                    }
                }
                Err(failure) => {
                    last_upstream_status = failure.upstream_status;
                    last_error_body = failure.body;
                    last_error_triggers = failure.classified_triggers;
                    last_failure_transient = failure.transient;
                    if !failure.transient {
                        // Retrying the same route won't change a non-transient answer.
                        break;
                    }
                    if attempt + 1 < max_attempts {
                        tokio::time::sleep(retry_delay(attempt as u32, failure.retry_after_ms))
                            .await;
                    }
                }
            }
        }
    }

    let event = json!({
        "event_type": "gateway.request.rejected",
        "request_id": request_id.clone(),
        "workspace_id": preflight.workspace_id,
        "route_id": last_route_id,
        "model_requested": preflight.model_requested,
        "model_used": Value::Null,
        "provider": Value::Null,
        "status": "error",
        "decision_reason": preflight.decision_reason,
        "cache_hit": false,
        "semantic_cache_hit": false,
        "stream": stream,
        "started_at": started_at,
        "completed_at": Utc::now().to_rfc3339()
    });
    if let Err(err) = emit_runtime_events(&state, &preflight.workspace_id, vec![event]).await {
        error!("runtime error event emit failed: {}", err);
    }
    let mut failed = (
        failure_status(last_upstream_status, last_failure_transient),
        Json(json!({
            "detail": if last_failure_transient {
                "all gateway routes failed"
            } else {
                "provider request failed"
            },
            "upstream_status": last_upstream_status,
            "upstream_body": last_error_body,
            "error_triggers": last_error_triggers
        })),
    )
        .into_response();
    set_decision_header(&mut failed, preflight.decision_header.as_deref(), None);
    failed
}

/// `X-RunLedger-Decision`: the route that served (alias/provider:model and the step's
/// trigger — primary, configured, policy, …) followed by preflight's cache, budget and
/// guardrail summary. Without a served route it is preflight's summary alone.
fn decision_header(base: Option<&str>, step: Option<&RuntimeExecutionStep>) -> Option<String> {
    let mut parts: Vec<String> = Vec::new();
    if let Some(step) = step {
        parts.push(format!(
            "route={}/{}:{}",
            step.alias, step.provider, step.target_model
        ));
        parts.push(format!("trigger={}", step.trigger));
    }
    if let Some(base) = base.filter(|b| !b.is_empty()) {
        parts.push(base.to_string());
    }
    if parts.is_empty() {
        return None;
    }
    // Header values must be visible ASCII; anything else becomes '_'.
    Some(
        parts
            .join("; ")
            .chars()
            .map(|c| {
                if c.is_ascii_graphic() || c == ' ' {
                    c
                } else {
                    '_'
                }
            })
            .collect(),
    )
}

fn set_decision_header(
    response: &mut Response,
    base: Option<&str>,
    step: Option<&RuntimeExecutionStep>,
) {
    if let Some(value) = decision_header(base, step) {
        if let Ok(header) = HeaderValue::from_str(&value) {
            response
                .headers_mut()
                .insert("x-runledger-decision", header);
        }
    }
}

/// Delay before retrying the same route: the provider's Retry-After when given,
/// otherwise exponential backoff from 250 ms; capped at 5 s so a request never stalls
/// long on one route when fallbacks exist (review G-11).
fn retry_delay(attempt: u32, retry_after_ms: Option<u64>) -> std::time::Duration {
    let backoff = 250_u64.saturating_mul(1_u64 << attempt.min(10));
    std::time::Duration::from_millis(retry_after_ms.unwrap_or(backoff).min(5_000))
}

/// Retry-After in seconds (the HTTP-date form is ignored), as milliseconds.
fn parse_retry_after(headers: &reqwest::header::HeaderMap) -> Option<u64> {
    headers
        .get(reqwest::header::RETRY_AFTER)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.trim().parse::<f64>().ok())
        .filter(|secs| secs.is_finite() && *secs >= 0.0)
        .map(|secs| (secs * 1000.0) as u64)
}

/// A CIDR block (IPv4 or IPv6) for the trusted-proxy list.
#[derive(Debug, Clone, Copy, PartialEq)]
struct IpNet {
    addr: IpAddr,
    prefix: u8,
}

impl IpNet {
    fn parse(text: &str) -> Option<IpNet> {
        let text = text.trim();
        let (addr_text, prefix_text) = match text.split_once('/') {
            Some((a, p)) => (a, Some(p)),
            None => (text, None),
        };
        let addr: IpAddr = addr_text.trim().parse().ok()?;
        let max = if addr.is_ipv4() { 32 } else { 128 };
        let prefix = match prefix_text {
            Some(p) => p.trim().parse::<u8>().ok().filter(|p| *p <= max)?,
            None => max,
        };
        Some(IpNet { addr, prefix })
    }

    fn contains(&self, ip: IpAddr) -> bool {
        match (self.addr, ip) {
            (IpAddr::V4(net), IpAddr::V4(ip)) => {
                let mask = if self.prefix == 0 {
                    0
                } else {
                    u32::MAX << (32 - self.prefix)
                };
                u32::from(net) & mask == u32::from(ip) & mask
            }
            (IpAddr::V6(net), IpAddr::V6(ip)) => {
                let mask = if self.prefix == 0 {
                    0
                } else {
                    u128::MAX << (128 - self.prefix)
                };
                u128::from(net) & mask == u128::from(ip) & mask
            }
            (IpAddr::V4(_), IpAddr::V6(ip)) => match ip.to_ipv4_mapped() {
                Some(v4) => self.contains(IpAddr::V4(v4)),
                None => false,
            },
            _ => false,
        }
    }
}

fn parse_trusted_proxies(value: &str) -> Vec<IpNet> {
    value
        .split(',')
        .filter(|part| !part.trim().is_empty())
        .filter_map(|part| {
            let parsed = IpNet::parse(part);
            if parsed.is_none() {
                error!("ignoring invalid trusted proxy entry: {}", part.trim());
            }
            parsed
        })
        .collect()
}

/// The client address for IP ACLs: the socket peer unless it is a trusted proxy, in
/// which case X-Forwarded-For is walked from the right, skipping trusted hops, and the
/// first untrusted address wins. Spoofed left-most entries are never used (G-18).
fn client_ip_from(peer: IpAddr, forwarded_for: Option<&str>, trusted: &[IpNet]) -> IpAddr {
    let is_trusted = |ip: IpAddr| trusted.iter().any(|net| net.contains(ip));
    if !is_trusted(peer) {
        return peer;
    }
    let mut client = peer;
    for hop in forwarded_for.unwrap_or("").split(',').rev() {
        match hop.trim().parse::<IpAddr>() {
            Ok(ip) => {
                client = ip;
                if !is_trusted(ip) {
                    break;
                }
            }
            Err(_) => break,
        }
    }
    client
}

/// Whether to mirror this request: `pct` is the route's sample rate (0–1).
fn mirror_sampled(pct: f64) -> bool {
    if pct.is_nan() || pct <= 0.0 {
        return false;
    }
    if pct >= 1.0 {
        return true;
    }
    let draw = (uuid::Uuid::new_v4().as_u128() % 1_000_000) as f64 / 1_000_000.0;
    draw < pct
}

/// Whether an execution step runs given the previous failure. Trigger-gated steps run
/// only when the previous failure produced one of their triggers; plain steps run unless
/// the previous failure was non-transient (another route won't fix a bad request).
fn step_runs_after(
    required_triggers: &[String],
    last_triggers: &[String],
    last_failure_transient: bool,
) -> bool {
    if required_triggers.is_empty() {
        return last_failure_transient;
    }
    required_triggers
        .iter()
        .any(|trigger| last_triggers.iter().any(|seen| seen == trigger))
}

/// Status returned when no step succeeded: the provider's own 4xx for a non-transient
/// failure (so clients see 400/413, not 502), 429 when rate limited, otherwise 502.
fn failure_status(upstream: Option<u16>, transient: bool) -> StatusCode {
    match upstream {
        Some(429) => StatusCode::TOO_MANY_REQUESTS,
        Some(code) if !transient && (400..500).contains(&code) => {
            StatusCode::from_u16(code).unwrap_or(StatusCode::BAD_GATEWAY)
        }
        _ => StatusCode::BAD_GATEWAY,
    }
}

// ── Control-plane calls ─────────────────────────────────────────────────────────

async fn call_preflight(
    state: &AppState,
    payload: RuntimePreflightRequest,
) -> Result<RuntimePreflightResponse, Response> {
    let url = format!(
        "{}/gateway/runtime/internal/preflight",
        state.control_plane_url
    );
    let resp = state
        .http
        .post(url)
        .timeout(state.control_plane_timeout)
        .header("x-admin-secret", &state.admin_secret)
        .json(&payload)
        .send()
        .await
        .map_err(|err| {
            (
                StatusCode::BAD_GATEWAY,
                Json(json!({"detail": format!("gateway preflight failed: {}", err)})),
            )
                .into_response()
        })?;
    if !resp.status().is_success() {
        return Err(response_from_upstream(resp).await);
    }
    resp.json::<RuntimePreflightResponse>()
        .await
        .map_err(|err| {
            (
                StatusCode::BAD_GATEWAY,
                Json(json!({"detail": format!("gateway preflight parse failed: {}", err)})),
            )
                .into_response()
        })
}

async fn call_finalize(state: &AppState, payload: RuntimeFinalizeRequest) -> Result<(), Response> {
    let url = format!(
        "{}/gateway/runtime/internal/finalize",
        state.control_plane_url
    );
    let resp = state
        .http
        .post(url)
        .timeout(state.control_plane_timeout)
        .header("x-admin-secret", &state.admin_secret)
        .json(&payload)
        .send()
        .await
        .map_err(|err| {
            (
                StatusCode::BAD_GATEWAY,
                Json(json!({"detail": format!("gateway finalize failed: {}", err)})),
            )
                .into_response()
        })?;
    if !resp.status().is_success() {
        return Err(response_from_upstream(resp).await);
    }
    Ok(())
}

async fn call_provider_execute(
    state: &AppState,
    step: &RuntimeExecutionStep,
    stream: bool,
) -> Result<ProviderSuccess, ProviderFailure> {
    let url = format!(
        "{}/gateway/runtime/internal/provider-execute",
        state.control_plane_url
    );
    let started = Instant::now();
    let mut builder = state.http.post(url);
    if !stream {
        // The control plane makes the provider call with the step's timeout; allow a
        // little more for the hop itself (review G-22).
        builder = builder.timeout(std::time::Duration::from_millis(
            step.timeout_ms.unwrap_or(120_000).max(1) as u64 + 5_000,
        ));
    }
    let resp = builder
        .header("x-admin-secret", &state.admin_secret)
        .json(&RuntimeProviderExecuteRequest {
            route_id: step.route_id.clone(),
            request_body: step.request_body.clone(),
            stream,
            timeout_ms: step.timeout_ms,
        })
        .send()
        .await
        .map_err(|err| ProviderFailure {
            upstream_status: None,
            body: err.to_string(),
            transient: true,
            classified_triggers: vec!["timeout".to_string()],
            retry_after_ms: None,
        })?;
    let latency_ms = started.elapsed().as_millis() as i64;
    if stream && resp.status().is_success() {
        let _ = call_route_result(state, &step.route_id, true, false, None).await;
        let content_type = resp
            .headers()
            .get("content-type")
            .and_then(|value| value.to_str().ok())
            .unwrap_or("text/event-stream")
            .to_string();
        let stream_body = resp
            .bytes_stream()
            .map(|chunk| chunk.map_err(|err| std::io::Error::other(err.to_string())));
        let body = Body::from_stream(stream_body);
        let response = Response::builder()
            .status(StatusCode::OK)
            .header("content-type", content_type)
            .body(body)
            .unwrap_or_else(|_| {
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    Json(json!({"detail": "failed to build streaming response"})),
                )
                    .into_response()
            });
        return Ok(ProviderSuccess::Stream {
            response,
            latency_ms,
        });
    }
    if resp.status().is_success() {
        let _ = call_route_result(state, &step.route_id, true, false, None).await;
        return resp
            .json::<Value>()
            .await
            .map(|response_json| ProviderSuccess::Json {
                response_json,
                latency_ms,
            })
            .map_err(|err| ProviderFailure {
                upstream_status: Some(StatusCode::BAD_GATEWAY.as_u16()),
                body: format!("provider response parse failed: {}", err),
                transient: false,
                classified_triggers: Vec::new(),
                retry_after_ms: None,
            });
    }
    let status_code = resp.status().as_u16();
    let retry_after_ms = parse_retry_after(resp.headers());
    let body = resp.text().await.unwrap_or_default();
    let triggers = classify_error_triggers(Some(status_code), &body);
    let transient = matches!(status_code, 429 | 500 | 502 | 503 | 504);
    let _ = call_route_result(state, &step.route_id, false, transient, Some(body.clone())).await;
    Err(ProviderFailure {
        upstream_status: Some(status_code),
        body,
        transient,
        classified_triggers: triggers,
        retry_after_ms,
    })
}

// ── Provider execution ──────────────────────────────────────────────────────────

async fn execute_step(
    state: &AppState,
    step: &RuntimeExecutionStep,
    stream: bool,
) -> Result<ProviderSuccess, ProviderFailure> {
    if step.execution_mode == "python_adapter" {
        return call_provider_execute(state, step, stream).await;
    }
    let request_url = match &step.request_url {
        Some(url) => url.clone(),
        None => {
            return Err(ProviderFailure {
                upstream_status: None,
                body: "missing direct request url".to_string(),
                transient: false,
                classified_triggers: Vec::new(),
                retry_after_ms: None,
            })
        }
    };
    let started = Instant::now();
    let mut upstream_headers = HeaderMap::new();
    for (key, value) in &step.request_headers {
        if let Ok(header_name) = axum::http::header::HeaderName::from_bytes(key.as_bytes()) {
            if let Ok(header_value) = HeaderValue::from_str(value) {
                upstream_headers.insert(header_name, header_value);
            }
        }
    }
    if !upstream_headers.contains_key("content-type") {
        upstream_headers.insert("content-type", HeaderValue::from_static("application/json"));
    }
    let request_builder = state
        .http
        .request(
            reqwest::Method::from_bytes(step.request_method.as_bytes())
                .unwrap_or(reqwest::Method::POST),
            &request_url,
        )
        .headers(upstream_headers)
        .timeout(std::time::Duration::from_millis(
            step.timeout_ms.unwrap_or(120_000).max(1) as u64,
        ))
        .json(&step.request_body);
    let resp = match request_builder.send().await {
        Ok(resp) => resp,
        Err(err) => {
            let err_text = err.to_string();
            let _ =
                call_route_result(state, &step.route_id, false, true, Some(err_text.clone())).await;
            return Err(ProviderFailure {
                upstream_status: None,
                body: err_text,
                transient: true,
                classified_triggers: vec!["timeout".to_string()],
                retry_after_ms: None,
            });
        }
    };
    let latency_ms = started.elapsed().as_millis() as i64;

    if stream && resp.status().is_success() {
        let _ = call_route_result(state, &step.route_id, true, false, None).await;
        return execute_streaming_response(resp, step, latency_ms).await;
    }

    if resp.status().is_success() {
        let _ = call_route_result(state, &step.route_id, true, false, None).await;
        return resp
            .json::<Value>()
            .await
            .map(|raw| {
                let response_json = maybe_normalize_response(raw, step);
                ProviderSuccess::Json {
                    response_json,
                    latency_ms,
                }
            })
            .map_err(|err| ProviderFailure {
                upstream_status: Some(StatusCode::BAD_GATEWAY.as_u16()),
                body: format!("provider response parse failed: {}", err),
                transient: false,
                classified_triggers: Vec::new(),
                retry_after_ms: None,
            });
    }
    let status_code = resp.status().as_u16();
    let retry_after_ms = parse_retry_after(resp.headers());
    let body = resp.text().await.unwrap_or_default();
    let triggers = classify_error_triggers(Some(status_code), &body);
    let transient = matches!(status_code, 429 | 500 | 502 | 503 | 504);
    let _ = call_route_result(state, &step.route_id, false, transient, Some(body.clone())).await;
    Err(ProviderFailure {
        upstream_status: Some(status_code),
        body,
        transient,
        classified_triggers: triggers,
        retry_after_ms,
    })
}

async fn execute_streaming_response(
    resp: reqwest::Response,
    step: &RuntimeExecutionStep,
    latency_ms: i64,
) -> Result<ProviderSuccess, ProviderFailure> {
    let stream_format = step.provider_stream_format.as_deref();
    match stream_format {
        Some("bedrock_eventstream") => {
            let model = step.target_model.clone();
            let all_bytes = resp.bytes().await.map_err(|err| ProviderFailure {
                upstream_status: None,
                body: format!("bedrock stream read failed: {}", err),
                transient: true,
                classified_triggers: vec!["timeout".to_string()],
                retry_after_ms: None,
            })?;
            let events = parse_bedrock_event_stream_chunk(&all_bytes);
            let mut chunks: Vec<Vec<u8>> = Vec::new();
            for (event_type, payload) in &events {
                if let Some(sse_bytes) = bedrock_event_to_openai_sse(event_type, payload, &model) {
                    chunks.push(sse_bytes);
                }
            }
            chunks.push(sse_chunk("", &model, true));
            chunks.push(b"data: [DONE]\n\n".to_vec());
            let body_bytes: Vec<u8> = chunks.into_iter().flatten().collect();
            let body = Body::from(body_bytes);
            let response = Response::builder()
                .status(StatusCode::OK)
                .header("content-type", "text/event-stream")
                .body(body)
                .unwrap_or_else(|_| {
                    (
                        StatusCode::INTERNAL_SERVER_ERROR,
                        Json(json!({"detail": "failed to build streaming response"})),
                    )
                        .into_response()
                });
            Ok(ProviderSuccess::Stream {
                response,
                latency_ms,
            })
        }
        Some("gemini_sse") => {
            let model = step.target_model.clone();
            let stream_body = resp.bytes_stream().map(move |chunk| match chunk {
                Ok(bytes) => {
                    let text = String::from_utf8_lossy(&bytes);
                    let mut output = Vec::new();
                    for line in text.lines() {
                        if let Some(sse_bytes) = convert_gemini_sse_to_openai(line, &model) {
                            output.extend_from_slice(&sse_bytes);
                        }
                    }
                    if output.is_empty() {
                        Ok(bytes::Bytes::new())
                    } else {
                        Ok(bytes::Bytes::from(output))
                    }
                }
                Err(err) => Err(std::io::Error::other(err.to_string())),
            });
            let body = Body::from_stream(stream_body);
            let response = Response::builder()
                .status(StatusCode::OK)
                .header("content-type", "text/event-stream")
                .body(body)
                .unwrap_or_else(|_| {
                    (
                        StatusCode::INTERNAL_SERVER_ERROR,
                        Json(json!({"detail": "failed to build streaming response"})),
                    )
                        .into_response()
                });
            Ok(ProviderSuccess::Stream {
                response,
                latency_ms,
            })
        }
        _ => {
            let content_type = resp
                .headers()
                .get("content-type")
                .and_then(|value| value.to_str().ok())
                .unwrap_or("text/event-stream")
                .to_string();
            let stream_body = resp
                .bytes_stream()
                .map(|chunk| chunk.map_err(|err| std::io::Error::other(err.to_string())));
            let body = Body::from_stream(stream_body);
            let response = Response::builder()
                .status(StatusCode::OK)
                .header("content-type", content_type)
                .body(body)
                .unwrap_or_else(|_| {
                    (
                        StatusCode::INTERNAL_SERVER_ERROR,
                        Json(json!({"detail": "failed to build streaming response"})),
                    )
                        .into_response()
                });
            Ok(ProviderSuccess::Stream {
                response,
                latency_ms,
            })
        }
    }
}

// ── Route health ────────────────────────────────────────────────────────────────

async fn call_route_result(
    state: &AppState,
    route_id: &str,
    success: bool,
    transient: bool,
    error_detail: Option<String>,
) -> Result<(), String> {
    let url = format!(
        "{}/gateway/runtime/internal/route-result",
        state.control_plane_url
    );
    state
        .http
        .post(url)
        .timeout(state.control_plane_timeout)
        .header("x-admin-secret", &state.admin_secret)
        .json(&RuntimeRouteResultRequest {
            route_id: route_id.to_string(),
            success,
            transient,
            error_detail,
        })
        .send()
        .await
        .map_err(|err| err.to_string())?;
    Ok(())
}

async fn call_mirror(state: &AppState, payload: RuntimeMirrorRequest) -> Result<(), String> {
    let url = format!(
        "{}/gateway/runtime/internal/mirror",
        state.control_plane_url
    );
    state
        .http
        .post(url)
        .timeout(std::time::Duration::from_secs(300))
        .header("x-admin-secret", &state.admin_secret)
        .json(&payload)
        .send()
        .await
        .map_err(|err| err.to_string())?;
    Ok(())
}

// ── Error classification ────────────────────────────────────────────────────────

fn classify_error_triggers(status_code: Option<u16>, body: &str) -> Vec<String> {
    let mut triggers = Vec::new();
    let lowered = body.to_lowercase();
    if matches!(status_code, Some(400) | Some(403))
        && [
            "content policy",
            "content_filter",
            "safety",
            "moderation",
            "policy",
        ]
        .iter()
        .any(|token| lowered.contains(token))
    {
        triggers.push("content_policy".to_string());
    }
    if matches!(status_code, Some(400) | Some(413))
        && [
            "context",
            "maximum context",
            "context length",
            "too many tokens",
            "prompt too long",
        ]
        .iter()
        .any(|token| lowered.contains(token))
    {
        triggers.push("context_window".to_string());
    }
    triggers
}

// ── Utilities ───────────────────────────────────────────────────────────────────

/// Control-plane response headers that tell a client why it was refused and when to
/// retry; forwarded with the status and body (review G-13).
const FORWARDED_REFUSAL_HEADERS: [&str; 4] = [
    "retry-after",
    "x-cost-cap-reason",
    "x-budget-id",
    "x-agent-policy-reason",
];

async fn response_from_upstream(resp: reqwest::Response) -> Response {
    let status = StatusCode::from_u16(resp.status().as_u16()).unwrap_or(StatusCode::BAD_GATEWAY);
    let forwarded: Vec<(axum::http::HeaderName, axum::http::HeaderValue)> =
        FORWARDED_REFUSAL_HEADERS
            .iter()
            .filter_map(|name| {
                let value = resp.headers().get(*name)?.to_str().ok()?;
                Some((
                    axum::http::HeaderName::from_static(name),
                    axum::http::HeaderValue::from_str(value).ok()?,
                ))
            })
            .collect();
    let mut response = match resp.bytes().await {
        Ok(bytes) => match serde_json::from_slice::<Value>(&bytes) {
            Ok(body) => (status, Json(body)).into_response(),
            Err(_) => (
                status,
                Json(json!({"detail": String::from_utf8_lossy(&bytes).to_string()})),
            )
                .into_response(),
        },
        Err(err) => (
            StatusCode::BAD_GATEWAY,
            Json(json!({"detail": format!("upstream response read failed: {}", err)})),
        )
            .into_response(),
    };
    for (name, value) in forwarded {
        response.headers_mut().insert(name, value);
    }
    response
}

fn header_value(headers: &HeaderMap, name: &str) -> Option<String> {
    headers
        .get(name)
        .and_then(|value| value.to_str().ok())
        .map(|value| value.to_string())
}

async fn emit_runtime_events(
    state: &AppState,
    workspace_id: &str,
    events: Vec<Value>,
) -> Result<(), String> {
    let payload = RuntimeEventBatch {
        workspace_id: workspace_id.to_string(),
        source_service: "runledger-gateway-rs".to_string(),
        events,
    };
    let body = serde_json::to_vec(&payload).map_err(|err| err.to_string())?;
    let timestamp = Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true);
    let mut mac = HmacSha256::new_from_slice(state.event_signing_secret.as_bytes())
        .map_err(|err| err.to_string())?;
    mac.update(workspace_id.as_bytes());
    mac.update(b".");
    mac.update(timestamp.as_bytes());
    mac.update(b".");
    mac.update(&body);
    let signature = hex::encode(mac.finalize().into_bytes());

    let url = format!("{}/gateway/runtime/events/signed", state.control_plane_url);
    let resp = state
        .http
        .post(url)
        .timeout(state.control_plane_timeout)
        .header("x-runledger-timestamp", timestamp)
        .header("x-runledger-signature", signature)
        .header("content-type", "application/json")
        .body(body)
        .send()
        .await
        .map_err(|err| err.to_string())?;
    if resp.status().is_success() {
        Ok(())
    } else {
        Err(format!("event ingest failed with status {}", resp.status()))
    }
}

fn uuid_like() -> String {
    // A real UUID: the control plane validates event request ids as UUIDs, and the
    // old "gw_<hex>" form made every runtime event fail with 400 (review G-03).
    Uuid::new_v4().to_string()
}

const STREAM_CAPTURE_LIMIT: usize = 2 * 1024 * 1024;

/// Calls finalize with whatever was captured when dropped — at the normal end of the
/// stream and when the client disconnects early.
struct StreamFinalizer {
    captured: Vec<u8>,
    state: Option<Arc<AppState>>,
    template: Option<RuntimeFinalizeRequest>,
    model: String,
    started: Instant,
}

impl Drop for StreamFinalizer {
    fn drop(&mut self) {
        let (Some(state), Some(mut request)) = (self.state.take(), self.template.take()) else {
            return;
        };
        let response_json = sse_to_completion(&self.captured, &self.model);
        // The provider is busy until the last chunk, so the stream's duration counts
        // toward both provider latency and total wall time; their difference stays the
        // gateway's own overhead (review G-15).
        let stream_ms = self.started.elapsed().as_millis() as i64;
        request.response_json = response_json;
        let provider_ms = request.latency_ms.unwrap_or(0) + stream_ms;
        request.latency_ms = Some(provider_ms);
        request.total_wall_ms =
            Some((request.total_wall_ms.unwrap_or(0) + stream_ms).max(provider_ms));
        if let Ok(handle) = tokio::runtime::Handle::try_current() {
            handle.spawn(async move {
                if let Err(resp) = call_finalize(&state, request).await {
                    error!("stream finalize failed: status {}", resp.status());
                }
            });
        }
    }
}

/// Forward the streamed body unchanged while keeping a bounded copy for metering.
fn tee_stream_for_finalize(
    response: Response,
    state: Arc<AppState>,
    template: RuntimeFinalizeRequest,
    model: String,
) -> Response {
    let (parts, body) = response.into_parts();
    let upstream = body.into_data_stream();
    let finalizer = StreamFinalizer {
        captured: Vec::new(),
        state: Some(state),
        template: Some(template),
        model,
        started: Instant::now(),
    };
    let teed = futures_util::stream::unfold(
        (upstream, finalizer),
        |(mut upstream, mut finalizer)| async move {
            match upstream.next().await {
                Some(Ok(chunk)) => {
                    let room = STREAM_CAPTURE_LIMIT.saturating_sub(finalizer.captured.len());
                    if room > 0 {
                        let take = room.min(chunk.len());
                        finalizer.captured.extend_from_slice(&chunk[..take]);
                    }
                    Some((
                        Ok::<bytes::Bytes, axum::Error>(chunk),
                        (upstream, finalizer),
                    ))
                }
                Some(Err(err)) => Some((Err(err), (upstream, finalizer))),
                None => None, // dropping the state runs the finalizer
            }
        },
    );
    Response::from_parts(parts, Body::from_stream(teed))
}

/// Rebuild an OpenAI-style chat completion from captured server-sent events.
/// Understands OpenAI chunks (choices[].delta, usage in the last chunk) and
/// Anthropic events (message_start / content_block_delta / message_delta).
fn sse_to_completion(raw: &[u8], fallback_model: &str) -> Value {
    let text = String::from_utf8_lossy(raw);
    let mut content = String::new();
    let mut id: Option<String> = None;
    let mut model: Option<String> = None;
    let mut finish_reason: Option<String> = None;
    let mut prompt_tokens: Option<i64> = None;
    let mut completion_tokens: Option<i64> = None;
    let mut cached_tokens: Option<i64> = None;
    for line in text.lines() {
        let line = line.trim();
        let Some(data) = line.strip_prefix("data:") else {
            continue;
        };
        let data = data.trim();
        if data.is_empty() || data == "[DONE]" {
            continue;
        }
        let Ok(event) = serde_json::from_str::<Value>(data) else {
            continue;
        };
        if id.is_none() {
            id = event.get("id").and_then(Value::as_str).map(str::to_string);
        }
        if model.is_none() {
            model = event
                .get("model")
                .and_then(Value::as_str)
                .map(str::to_string);
        }
        // OpenAI-compatible chunk
        if let Some(choices) = event.get("choices").and_then(Value::as_array) {
            for choice in choices {
                if let Some(piece) = choice.pointer("/delta/content").and_then(Value::as_str) {
                    content.push_str(piece);
                }
                if let Some(reason) = choice.get("finish_reason").and_then(Value::as_str) {
                    finish_reason = Some(reason.to_string());
                }
            }
        }
        if let Some(usage) = event.get("usage").filter(|u| u.is_object()) {
            if let Some(v) = usage.get("prompt_tokens").and_then(Value::as_i64) {
                prompt_tokens = Some(v);
            }
            if let Some(v) = usage.get("completion_tokens").and_then(Value::as_i64) {
                completion_tokens = Some(v);
            }
            if let Some(v) = usage
                .pointer("/prompt_tokens_details/cached_tokens")
                .and_then(Value::as_i64)
            {
                cached_tokens = Some(v);
            }
            // Anthropic message_delta usage
            if let Some(v) = usage.get("output_tokens").and_then(Value::as_i64) {
                completion_tokens = Some(v);
            }
        }
        // Anthropic events
        match event.get("type").and_then(Value::as_str) {
            Some("message_start") => {
                if let Some(msg) = event.get("message") {
                    id = id.or_else(|| msg.get("id").and_then(Value::as_str).map(str::to_string));
                    model = model
                        .or_else(|| msg.get("model").and_then(Value::as_str).map(str::to_string));
                    if let Some(v) = msg.pointer("/usage/input_tokens").and_then(Value::as_i64) {
                        prompt_tokens = Some(v);
                    }
                    if let Some(v) = msg
                        .pointer("/usage/cache_read_input_tokens")
                        .and_then(Value::as_i64)
                    {
                        cached_tokens = Some(v);
                    }
                }
            }
            Some("content_block_delta") => {
                if let Some(piece) = event.pointer("/delta/text").and_then(Value::as_str) {
                    content.push_str(piece);
                }
            }
            Some("message_delta") => {
                if let Some(reason) = event.pointer("/delta/stop_reason").and_then(Value::as_str) {
                    finish_reason = Some(reason.to_string());
                }
            }
            _ => {}
        }
    }
    let mut completion = json!({
        "id": id.unwrap_or_else(uuid_like),
        "object": "chat.completion",
        "model": model.unwrap_or_else(|| fallback_model.to_string()),
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": finish_reason.unwrap_or_else(|| "stop".to_string()),
        }],
        "x_runledger_streamed": true,
    });
    if prompt_tokens.is_some() || completion_tokens.is_some() {
        let p = prompt_tokens.unwrap_or(0);
        let c = completion_tokens.unwrap_or(0);
        let mut usage = json!({"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c});
        if let Some(cached) = cached_tokens {
            usage["prompt_tokens_details"] = json!({"cached_tokens": cached});
        }
        completion["usage"] = usage;
    }
    completion
}

#[cfg(test)]
mod stream_tests {
    use super::*;

    #[test]
    fn openai_chunks_reassemble_with_usage() {
        let raw = b"data: {\"id\":\"c1\",\"model\":\"gpt-4o-mini\",\"choices\":[{\"delta\":{\"content\":\"Hel\"}}]}\n\n\
data: {\"choices\":[{\"delta\":{\"content\":\"lo\"},\"finish_reason\":\"stop\"}]}\n\n\
data: {\"choices\":[],\"usage\":{\"prompt_tokens\":12,\"completion_tokens\":3,\"prompt_tokens_details\":{\"cached_tokens\":4}}}\n\n\
data: [DONE]\n\n";
        let out = sse_to_completion(raw, "fallback");
        assert_eq!(out["choices"][0]["message"]["content"], "Hello");
        assert_eq!(out["model"], "gpt-4o-mini");
        assert_eq!(out["usage"]["prompt_tokens"], 12);
        assert_eq!(out["usage"]["completion_tokens"], 3);
        assert_eq!(out["usage"]["total_tokens"], 15);
        assert_eq!(out["usage"]["prompt_tokens_details"]["cached_tokens"], 4);
    }

    #[test]
    fn anthropic_events_reassemble_with_usage() {
        let raw = b"event: message_start\ndata: {\"type\":\"message_start\",\"message\":{\"id\":\"m1\",\"model\":\"claude-x\",\"usage\":{\"input_tokens\":20}}}\n\n\
data: {\"type\":\"content_block_delta\",\"delta\":{\"type\":\"text_delta\",\"text\":\"Hi\"}}\n\n\
data: {\"type\":\"message_delta\",\"delta\":{\"stop_reason\":\"end_turn\"},\"usage\":{\"output_tokens\":5}}\n\n";
        let out = sse_to_completion(raw, "fallback");
        assert_eq!(out["choices"][0]["message"]["content"], "Hi");
        assert_eq!(out["usage"]["prompt_tokens"], 20);
        assert_eq!(out["usage"]["completion_tokens"], 5);
        assert_eq!(out["choices"][0]["finish_reason"], "end_turn");
    }

    #[test]
    fn no_usage_means_no_usage_block() {
        let out = sse_to_completion(
            b"data: {\"choices\":[{\"delta\":{\"content\":\"x\"}}]}\n",
            "m",
        );
        assert!(out.get("usage").is_none());
        assert_eq!(out["model"], "m");
    }

    #[test]
    fn decision_header_names_the_served_route() {
        let step: RuntimeExecutionStep = serde_json::from_value(json!({
            "route_id": "r1", "alias": "chat", "provider": "openai", "target_model": "gpt-4o-mini",
            "execution_mode": "direct_http", "base_url": null, "api_key_env_var": null,
            "priority": 1, "timeout_ms": null, "retry_count": 0, "region": null,
            "deployment_status": "healthy", "trigger": "policy", "required_error_triggers": [],
            "decision_reason": null, "request_method": "POST", "request_url": null,
            "request_headers": {}, "request_body": {}
        }))
        .unwrap();
        let value =
            decision_header(Some("cache=miss; budget=ok; guardrail=pass"), Some(&step)).unwrap();
        assert_eq!(
            value,
            "route=chat/openai:gpt-4o-mini; trigger=policy; cache=miss; budget=ok; guardrail=pass"
        );
        assert_eq!(
            decision_header(Some("route=cache; cache=exact"), None).as_deref(),
            Some("route=cache; cache=exact")
        );
        assert!(decision_header(None, None).is_none());
        assert_eq!(
            decision_header(Some("prompt=caf\u{e9}@1"), None).as_deref(),
            Some("prompt=caf_@1")
        );
    }

    #[test]
    fn uuid_like_is_a_uuid() {
        assert!(Uuid::parse_str(&uuid_like()).is_ok());
    }
}

#[cfg(test)]
mod fallback_tests {
    use super::*;

    fn v(items: &[&str]) -> Vec<String> {
        items.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn trigger_steps_run_only_after_a_matching_failure() {
        let ctx = v(&["context_window"]);
        assert!(!step_runs_after(&ctx, &[], true), "no failure yet");
        assert!(step_runs_after(&ctx, &v(&["context_window"]), false));
        assert!(!step_runs_after(&ctx, &v(&["content_policy"]), false));
    }

    #[test]
    fn plain_steps_skip_after_non_transient_failure() {
        assert!(step_runs_after(&[], &[], true));
        assert!(!step_runs_after(&[], &v(&["content_policy"]), false));
    }

    #[test]
    fn non_transient_failures_keep_the_provider_status() {
        assert_eq!(failure_status(Some(400), false), StatusCode::BAD_REQUEST);
        assert_eq!(
            failure_status(Some(413), false),
            StatusCode::PAYLOAD_TOO_LARGE
        );
        assert_eq!(
            failure_status(Some(429), true),
            StatusCode::TOO_MANY_REQUESTS
        );
        assert_eq!(failure_status(Some(503), true), StatusCode::BAD_GATEWAY);
        assert_eq!(failure_status(None, true), StatusCode::BAD_GATEWAY);
    }

    #[test]
    fn retry_delay_backs_off_and_respects_retry_after() {
        use std::time::Duration;
        assert_eq!(retry_delay(0, None), Duration::from_millis(250));
        assert_eq!(retry_delay(2, None), Duration::from_millis(1000));
        assert_eq!(retry_delay(9, None), Duration::from_millis(5000));
        assert_eq!(retry_delay(0, Some(1500)), Duration::from_millis(1500));
        assert_eq!(retry_delay(0, Some(60_000)), Duration::from_millis(5000));
        let mut headers = reqwest::header::HeaderMap::new();
        headers.insert(reqwest::header::RETRY_AFTER, "2".parse().unwrap());
        assert_eq!(parse_retry_after(&headers), Some(2000));
        headers.insert(
            reqwest::header::RETRY_AFTER,
            "Wed, 21 Oct 2015 07:28:00 GMT".parse().unwrap(),
        );
        assert_eq!(parse_retry_after(&headers), None);
    }

    #[test]
    fn mirror_sampling_respects_the_rate() {
        assert!(!mirror_sampled(0.0));
        assert!(!mirror_sampled(f64::NAN));
        assert!(mirror_sampled(1.0));
        let hits = (0..10_000).filter(|_| mirror_sampled(0.25)).count();
        assert!((2_000..3_000).contains(&hits), "{hits}");
    }

    #[test]
    fn client_ip_ignores_spoofed_forwarded_for() {
        let ip = |s: &str| s.parse::<IpAddr>().unwrap();
        let trusted = parse_trusted_proxies("172.16.0.0/12, 10.0.0.1");
        // Untrusted peer: X-Forwarded-For is ignored entirely.
        assert_eq!(
            client_ip_from(ip("203.0.113.9"), Some("10.9.9.9"), &trusted),
            ip("203.0.113.9")
        );
        // Trusted proxy: the right-most untrusted hop, not the client-supplied left one.
        assert_eq!(
            client_ip_from(ip("172.18.0.5"), Some("1.2.3.4, 198.51.100.7"), &trusted),
            ip("198.51.100.7")
        );
        // Chain of trusted proxies is skipped.
        assert_eq!(
            client_ip_from(ip("172.18.0.5"), Some("198.51.100.7, 10.0.0.1"), &trusted),
            ip("198.51.100.7")
        );
        // Trusted proxy without the header: the proxy itself.
        assert_eq!(
            client_ip_from(ip("172.18.0.5"), None, &trusted),
            ip("172.18.0.5")
        );
        assert!(parse_trusted_proxies("nope, 10.0.0.0/40").is_empty());
        assert!(IpNet::parse("::ffff:0:0/96").is_some());
    }

    #[test]
    fn classifies_context_window_and_content_policy() {
        assert_eq!(
            classify_error_triggers(Some(400), "maximum context length exceeded"),
            v(&["context_window"])
        );
        assert_eq!(
            classify_error_triggers(Some(400), "blocked by content_filter"),
            v(&["content_policy"])
        );
        assert!(classify_error_triggers(Some(500), "context").is_empty());
    }
}
