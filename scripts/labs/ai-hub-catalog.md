# AI Hub Model Catalog

Validate that **AI Hub** behaves like a real workspace model catalog.

Recommended workspace: `HomeLab / AgentTest` for a clean catalog, or
`LocalAIAgentStack / LiteLLM Gateway` alongside gateway routing work.

## What to Confirm

- Create, list, filter, edit, and delete model cards
- Deprecation controls and access request tracking
- Provider sync populates cards from upstream
- Navigation into **Provider Profiles** and **Model Usage** is coherent

## Setup

1. Log in with an org-admin or platform-admin session.
2. Open **AI Hub** from the left navigation.
3. Keep **Provider Profiles** and **Model Usage** in separate tabs for cross-checks.

## Steps

### Create a Model Card

Create a new card:

- Name: `workspace-demo-model`
- Provider: `ollama`
- Description: `Workspace-owned validation card`
- Context window: `32768`
- Input cost / 1K: `0.0001`
- Output cost / 1K: `0.0002`
- Capabilities: `chat, reasoning`
- Tags: `lab, workspace`

Verify the card appears in the inventory list.

### Filter & Search

1. Search by model name.
2. Filter by provider `ollama`.
3. Filter by tag `lab`.
4. Toggle **Show featured models only** (after marking the card featured below).

### Edit & Deprecate

Edit the card:

- Mark as `Featured` and `Deprecated`
- Add deprecation notice: `Replace with the promoted default after validation`
- Add capability `tools` and tag `featured-candidate`

Verify badges and deprecation notice render correctly.

### Access Request

Use **Request Access** on the card. Verify the count increments.

### Provider Sync

Open **Sync Provider Catalog** and run a sync for `OpenAI`.
Verify new provider cards appear and can be edited after sync.

### Cross-Check

1. Open **Provider Profiles** from the AI Hub header.
2. Open **Model Usage** from the AI Hub header.

Verify the catalog is the model-definition surface while adjacent pages handle
provider config and observed usage.

### Clean Up

Delete the `workspace-demo-model` card. Provider-synced cards can remain for
later demo work.
