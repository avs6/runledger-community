{{/*
Expand the name of the chart.
*/}}
{{- define "runledger.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "runledger.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart label.
*/}}
{{- define "runledger.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to all resources.
*/}}
{{- define "runledger.labels" -}}
helm.sh/chart: {{ include "runledger.chart" . }}
{{ include "runledger.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels (used in matchLabels + podSelector).
*/}}
{{- define "runledger.selectorLabels" -}}
app.kubernetes.io/name: {{ include "runledger.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
ServiceAccount name.
*/}}
{{- define "runledger.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "runledger.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Database URL — existing secret, in-cluster Postgres, or external value.
*/}}
{{- define "runledger.databaseUrl" -}}
{{- if .Values.secrets.existingSecret -}}
valueFrom:
  secretKeyRef:
    name: {{ .Values.secrets.existingSecret }}
    key: DATABASE_URL
{{- else if .Values.postgres.inCluster -}}
value: {{ printf "postgresql+asyncpg://%s:%s@%s-postgres:%v/%s" .Values.postgres.user .Values.postgres.password (include "runledger.fullname" .) .Values.postgres.port .Values.postgres.database | quote }}
{{- else -}}
value: {{ required "externalDatabase.url is required (or set postgres.inCluster=true)" .Values.externalDatabase.url | quote }}
{{- end }}
{{- end }}

{{/*
Redis URL — existing secret, in-cluster Redis, or external value.
*/}}
{{- define "runledger.redisUrl" -}}
{{- if .Values.secrets.existingSecret -}}
valueFrom:
  secretKeyRef:
    name: {{ .Values.secrets.existingSecret }}
    key: REDIS_URL
{{- else if .Values.redis.inCluster -}}
value: {{ printf "redis://%s-redis:%v/0" (include "runledger.fullname" .) .Values.redis.port | quote }}
{{- else -}}
value: {{ required "externalRedis.url is required (or set redis.inCluster=true)" .Values.externalRedis.url | quote }}
{{- end }}
{{- end }}

{{/*
Store URLs — in-cluster service DNS unless the store is marked external.
*/}}
{{- define "runledger.qdrantUrl" -}}
{{- if .Values.stores.qdrant.external -}}{{ required "stores.qdrant.url required when external" .Values.stores.qdrant.url }}{{- else -}}http://{{ include "runledger.fullname" . }}-qdrant:{{ .Values.stores.qdrant.port }}{{- end -}}
{{- end }}
{{- define "runledger.lettaUrl" -}}
{{- if .Values.stores.letta.external -}}{{ required "stores.letta.url required when external" .Values.stores.letta.url }}{{- else -}}http://{{ include "runledger.fullname" . }}-letta:{{ .Values.stores.letta.port }}{{- end -}}
{{- end }}
{{- define "runledger.memoryDbUrl" -}}
{{- if .Values.stores.memoryDb.external -}}{{ required "stores.memoryDb.url required when external" .Values.stores.memoryDb.url }}{{- else -}}postgresql://{{ .Values.stores.memoryDb.user }}:{{ .Values.stores.memoryDb.password }}@{{ include "runledger.fullname" . }}-memory-db:{{ .Values.stores.memoryDb.port }}/{{ .Values.stores.memoryDb.database }}{{- end -}}
{{- end }}

{{/*
Shared optimization-layer env — all inter-service URLs + store URLs + model config.
Included on api/worker/beat and every optimization microservice pod. Over-provisioning
env a given pod doesn't read is harmless; it keeps wiring in one place.
*/}}
{{- define "runledger.optimizationEnv" -}}
{{- $full := include "runledger.fullname" . -}}
- name: EMBEDDING_SVC_URL
  value: {{ printf "http://%s-embedding:8100" $full | quote }}
- name: SEMANTIC_CACHE_SVC_URL
  value: {{ printf "http://%s-semantic-cache:8101" $full | quote }}
- name: RERANKER_SVC_URL
  value: {{ printf "http://%s-reranker:8102" $full | quote }}
- name: CONTEXT_COMPILER_SVC_URL
  value: {{ printf "http://%s-context-compiler:8103" $full | quote }}
- name: COMPRESSION_SVC_URL
  value: {{ printf "http://%s-compression:8104" $full | quote }}
- name: ROUTER_SVC_URL
  value: {{ printf "http://%s-router:8105" $full | quote }}
- name: KG_SVC_URL
  value: {{ printf "http://%s-kg:8106" $full | quote }}
- name: MEMORY_SVC_URL
  value: {{ printf "http://%s-memory:8107" $full | quote }}
- name: SKILL_REGISTRY_URL
  value: {{ printf "http://%s-skill-registry:8108" $full | quote }}
- name: FLYWHEEL_SVC_URL
  value: {{ printf "http://%s-flywheel:8109" $full | quote }}
- name: QDRANT_URL
  value: {{ include "runledger.qdrantUrl" . | quote }}
- name: LETTA_BASE_URL
  value: {{ include "runledger.lettaUrl" . | quote }}
- name: OLLAMA_BASE_URL
  value: {{ .Values.optimization.ollamaBaseUrl | quote }}
- name: VLLM_BASE_URL
  value: {{ .Values.optimization.vllmBaseUrl | quote }}
- name: LOCAL_LLM_MODEL
  value: {{ .Values.optimization.localLlmModel | quote }}
- name: LETTA_MODEL
  value: {{ .Values.optimization.localLlmModel | quote }}
- name: EMBEDDING_MODEL
  value: {{ .Values.optimization.embeddingModel | quote }}
- name: EMBEDDING_DIM
  value: {{ .Values.optimization.embeddingDim | quote }}
- name: RERANKER_MODEL
  value: {{ .Values.optimization.rerankerModel | quote }}
- name: COMPRESSION_MODEL
  value: {{ .Values.optimization.compressionModel | quote }}
{{- end }}

{{/*
Soft/hard pod anti-affinity for a component, spreading replicas across nodes.
Usage: {{ include "runledger.antiAffinity" (list . "embedding") }}
*/}}
{{- define "runledger.antiAffinity" -}}
{{- $ctx := index . 0 -}}
{{- $component := index . 1 -}}
{{- $mode := $ctx.Values.optimization.antiAffinity -}}
{{- if ne $mode "off" }}
affinity:
  podAntiAffinity:
    {{- if eq $mode "hard" }}
    requiredDuringSchedulingIgnoredDuringExecution:
      - topologyKey: kubernetes.io/hostname
        labelSelector:
          matchLabels:
            {{- include "runledger.selectorLabels" $ctx | nindent 12 }}
            app.kubernetes.io/component: {{ $component }}
    {{- else }}
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          topologyKey: kubernetes.io/hostname
          labelSelector:
            matchLabels:
              {{- include "runledger.selectorLabels" $ctx | nindent 14 }}
              app.kubernetes.io/component: {{ $component }}
    {{- end }}
{{- end }}
{{- end }}

{{/*
Secret key reference helper — returns either secretKeyRef (existing secret) or value.
Usage: {{ include "runledger.secretRef" (list . "SECRET_KEY" .Values.secrets.secretKey) }}
*/}}
{{- define "runledger.secretRef" -}}
{{- $ctx := index . 0 -}}
{{- $key := index . 1 -}}
{{- $val := index . 2 -}}
{{- if $ctx.Values.secrets.existingSecret -}}
valueFrom:
  secretKeyRef:
    name: {{ $ctx.Values.secrets.existingSecret }}
    key: {{ $key }}
    optional: true
{{- else -}}
value: {{ $val | quote }}
{{- end }}
{{- end }}

{{/*
Common environment variables shared by api, worker, and beat.
*/}}
{{- define "runledger.commonEnv" -}}
- name: DATABASE_URL
  {{ include "runledger.databaseUrl" . }}
- name: REDIS_URL
  {{ include "runledger.redisUrl" . }}
- name: SECRET_KEY
  {{ include "runledger.secretRef" (list . "SECRET_KEY" .Values.secrets.secretKey) }}
- name: ADMIN_SECRET
  {{ include "runledger.secretRef" (list . "ADMIN_SECRET" .Values.secrets.adminSecret) }}
- name: METRICS_TOKEN
  {{ include "runledger.secretRef" (list . "METRICS_TOKEN" .Values.secrets.metricsToken) }}
- name: KMS_PROVIDER
  value: {{ .Values.secrets.kmsProvider | quote }}
{{- if eq .Values.secrets.kmsProvider "aws_kms" }}
- name: AWS_KMS_KEY_ID
  {{ include "runledger.secretRef" (list . "AWS_KMS_KEY_ID" .Values.secrets.awsKmsKeyId) }}
- name: AWS_KMS_REGION
  value: {{ .Values.secrets.awsKmsRegion | quote }}
{{- end }}
{{- if eq .Values.secrets.kmsProvider "vault" }}
- name: VAULT_ADDR
  value: {{ .Values.secrets.vaultAddr | quote }}
- name: VAULT_TOKEN
  {{ include "runledger.secretRef" (list . "VAULT_TOKEN" .Values.secrets.vaultToken) }}
- name: VAULT_TRANSIT_KEY
  value: {{ .Values.secrets.vaultTransitKey | quote }}
{{- end }}
- name: CORS_ORIGINS
  value: {{ .Values.corsOrigins | quote }}
- name: SMTP_HOST
  value: {{ .Values.email.smtpHost | quote }}
- name: SMTP_PORT
  value: {{ .Values.email.smtpPort | quote }}
- name: SMTP_USER
  {{ include "runledger.secretRef" (list . "SMTP_USER" .Values.email.smtpUser) }}
- name: SMTP_PASSWORD
  {{ include "runledger.secretRef" (list . "SMTP_PASSWORD" .Values.email.smtpPassword) }}
- name: SMTP_FROM
  value: {{ .Values.email.smtpFrom | quote }}
- name: APP_BASE_URL
  value: {{ .Values.email.appBaseUrl | quote }}
{{- if .Values.optimization.enabled }}
{{ include "runledger.optimizationEnv" . }}
{{- end }}
{{- end }}
