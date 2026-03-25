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
Database URL — from existing secret or direct value.
*/}}
{{- define "runledger.databaseUrl" -}}
{{- if .Values.secrets.existingSecret -}}
valueFrom:
  secretKeyRef:
    name: {{ .Values.secrets.existingSecret }}
    key: DATABASE_URL
{{- else -}}
value: {{ required "externalDatabase.url is required" .Values.externalDatabase.url | quote }}
{{- end }}
{{- end }}

{{/*
Redis URL — from existing secret or direct value.
*/}}
{{- define "runledger.redisUrl" -}}
{{- if .Values.secrets.existingSecret -}}
valueFrom:
  secretKeyRef:
    name: {{ .Values.secrets.existingSecret }}
    key: REDIS_URL
{{- else -}}
value: {{ required "externalRedis.url is required" .Values.externalRedis.url | quote }}
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
{{- end }}
