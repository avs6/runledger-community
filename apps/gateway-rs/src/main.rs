use std::env;
use std::sync::Arc;
use std::time::Instant;

use axum::body::Body;
use axum::extract::State;
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

type HmacSha256 = Hmac<Sha256>;

#[derive(Clone)]
struct AppState {
    http: Client,
    control_plane_url: String,
    admin_secret: String,
    event_signing_secret: String,
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
}

#[derive(Debug, Serialize)]
struct RuntimeFinalizeRequest {
    workspace_id: String,
    route_id: String,
    model_requested: String,
    prepared_messages: Vec<Value>,
    response_json: Value,
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
}

enum ProviderSuccess {
    Json { response_json: Value, latency_ms: i64 },
    Stream { response: Response, latency_ms: i64 },
}

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
    let event_signing_secret = env::var("RUNLEDGER_GATEWAY_EVENT_SIGNING_SECRET")
        .unwrap_or_else(|_| admin_secret.clone());
    let bind = env::var("RUNLEDGER_GATEWAY_BIND").unwrap_or_else(|_| "0.0.0.0:8210".to_string());

    let state = Arc::new(AppState {
        http: Client::new(),
        control_plane_url,
        admin_secret,
        event_signing_secret,
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
    axum::serve(listener, app).await.unwrap();
}

async fn health_live() -> impl IntoResponse {
    Json(json!({"ok": true, "service": "runledger-gateway-rs"}))
}

async fn health_ready(State(state): State<Arc<AppState>>) -> Response {
    let url = format!("{}/health/live", state.control_plane_url);
    match state.http.get(url).send().await {
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
    headers: HeaderMap,
    Json(body): Json<Value>,
) -> Response {
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
    let timeout_ms = header_value(&headers, "x-runledger-timeout-ms").and_then(|v| v.parse::<i64>().ok());
    let completion_timeout_ms = header_value(&headers, "x-runledger-completion-timeout-ms")
        .and_then(|v| v.parse::<i64>().ok());
    let stream_timeout_ms = header_value(&headers, "x-runledger-stream-timeout-ms")
        .and_then(|v| v.parse::<i64>().ok());
    let client_ip = header_value(&headers, "x-forwarded-for")
        .and_then(|value| value.split(',').next().map(|part| part.trim().to_string()));

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
        return (StatusCode::OK, Json(cached)).into_response();
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
    let started_at = Utc::now().to_rfc3339();

    for step in &preflight.execution_steps {
        if !step.required_error_triggers.is_empty()
            && step
                .required_error_triggers
                .iter()
                .all(|trigger| !last_error_triggers.iter().any(|seen| seen == trigger))
        {
            continue;
        }
        last_route_id = Some(step.route_id.clone());
        let max_attempts = std::cmp::max(1_i64, step.retry_count + 1);
        for _ in 0..max_attempts {
            match execute_step(&state, step, stream).await {
                Ok(ProviderSuccess::Stream { response, latency_ms }) => {
                    let event = json!({
                        "event_type": "gateway.request.completed",
                        "request_id": uuid_like(),
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
                    return response;
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
                            model_requested: preflight.model_requested.clone(),
                            prepared_messages: preflight.prepared_messages.clone(),
                            response_json: response_json.clone(),
                            latency_ms: Some(latency_ms),
                            total_wall_ms: Some(latency_ms),
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
                        },
                    )
                    .await
                    {
                        Ok(()) => {
                            let _ = call_mirror(
                                &state,
                                RuntimeMirrorRequest {
                                    workspace_id: preflight.workspace_id.clone(),
                                    route_id: step.route_id.clone(),
                                    model_requested: preflight.model_requested.clone(),
                                    request_body: step.request_body.clone(),
                                    response_json: response_json.clone(),
                                    request_tags: preflight.request_tags.clone(),
                                    preferred_region: preflight.preferred_region.clone(),
                                },
                            )
                            .await;
                            return (StatusCode::OK, Json(response_json)).into_response();
                        }
                        Err(response) => return response,
                    }
                }
                Err(failure) => {
                    last_upstream_status = failure.upstream_status;
                    last_error_body = failure.body;
                    last_error_triggers = failure.classified_triggers;
                    if !failure.transient {
                        return (
                            StatusCode::BAD_GATEWAY,
                            Json(json!({
                                "detail": "provider request failed",
                                "upstream_status": last_upstream_status,
                                "upstream_body": last_error_body
                            })),
                        )
                            .into_response();
                    }
                }
            }
        }
    }

    let event = json!({
        "event_type": "gateway.request.rejected",
        "request_id": uuid_like(),
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
    (
        StatusCode::BAD_GATEWAY,
        Json(json!({
            "detail": "all gateway routes failed",
            "upstream_status": last_upstream_status,
            "upstream_body": last_error_body
        })),
    )
        .into_response()
}

async fn call_preflight(
    state: &AppState,
    payload: RuntimePreflightRequest,
) -> Result<RuntimePreflightResponse, Response> {
    let url = format!("{}/gateway/runtime/internal/preflight", state.control_plane_url);
    let resp = state
        .http
        .post(url)
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
    resp.json::<RuntimePreflightResponse>().await.map_err(|err| {
        (
            StatusCode::BAD_GATEWAY,
            Json(json!({"detail": format!("gateway preflight parse failed: {}", err)})),
        )
            .into_response()
    })
}

async fn call_finalize(state: &AppState, payload: RuntimeFinalizeRequest) -> Result<(), Response> {
    let url = format!("{}/gateway/runtime/internal/finalize", state.control_plane_url);
    let resp = state
        .http
        .post(url)
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
    let resp = state
        .http
        .post(url)
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
        let stream_body = resp.bytes_stream().map(|chunk| {
            chunk.map_err(|err| std::io::Error::new(std::io::ErrorKind::Other, err.to_string()))
        });
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
            });
    }
    let status_code = resp.status().as_u16();
    let body = resp.text().await.unwrap_or_default();
    let triggers = classify_error_triggers(Some(status_code), &body);
    let transient = matches!(status_code, 429 | 500 | 502 | 503 | 504);
    let _ = call_route_result(
        state,
        &step.route_id,
        false,
        transient,
        Some(body.clone()),
    )
    .await;
    Err(ProviderFailure {
        upstream_status: Some(status_code),
        body,
        transient,
        classified_triggers: triggers,
    })
}

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
            reqwest::Method::from_bytes(step.request_method.as_bytes()).unwrap_or(reqwest::Method::POST),
            request_url,
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
            let _ = call_route_result(state, &step.route_id, false, true, Some(err_text.clone())).await;
            return Err(ProviderFailure {
                upstream_status: None,
                body: err_text,
                transient: true,
                classified_triggers: vec!["timeout".to_string()],
            });
        }
    };
    let latency_ms = started.elapsed().as_millis() as i64;
    if stream && resp.status().is_success() {
        let _ = call_route_result(state, &step.route_id, true, false, None).await;
        let content_type = resp
            .headers()
            .get("content-type")
            .and_then(|value| value.to_str().ok())
            .unwrap_or("text/event-stream")
            .to_string();
        let stream_body = resp.bytes_stream().map(|chunk| {
            chunk.map_err(|err| std::io::Error::new(std::io::ErrorKind::Other, err.to_string()))
        });
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
            });
    }
    let status_code = resp.status().as_u16();
    let body = resp.text().await.unwrap_or_default();
    let triggers = classify_error_triggers(Some(status_code), &body);
    let transient = matches!(status_code, 429 | 500 | 502 | 503 | 504);
    let _ = call_route_result(
        state,
        &step.route_id,
        false,
        transient,
        Some(body.clone()),
    )
    .await;
    Err(ProviderFailure {
        upstream_status: Some(status_code),
        body,
        transient,
        classified_triggers: triggers,
    })
}

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
    let url = format!("{}/gateway/runtime/internal/mirror", state.control_plane_url);
    state
        .http
        .post(url)
        .header("x-admin-secret", &state.admin_secret)
        .json(&payload)
        .send()
        .await
        .map_err(|err| err.to_string())?;
    Ok(())
}

fn classify_error_triggers(status_code: Option<u16>, body: &str) -> Vec<String> {
    let mut triggers = Vec::new();
    let lowered = body.to_lowercase();
    if matches!(status_code, Some(400) | Some(403))
        && ["content policy", "content_filter", "safety", "moderation", "policy"]
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

async fn response_from_upstream(resp: reqwest::Response) -> Response {
    let status = StatusCode::from_u16(resp.status().as_u16()).unwrap_or(StatusCode::BAD_GATEWAY);
    match resp.bytes().await {
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
    }
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
    format!(
        "gw_{}",
        Utc::now()
            .timestamp_nanos_opt()
            .unwrap_or_default()
            .unsigned_abs()
    )
}
