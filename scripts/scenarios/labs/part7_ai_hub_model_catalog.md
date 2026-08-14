# Part 7A - AI Hub Model Catalog

*Prerequisite: Part 1 completed.*

Use this lab after the org, workspace, user, and API-key foundation is in place.

Recommended workspace:

- `HomeLab / AgentTest` if you want a small clean catalog
- `LocalAIAgentStack / LiteLLM Gateway` if you want the catalog to sit beside gateway routing work

## Goal

Validate that **AI Hub** behaves like a real workspace model catalog rather than a static marketplace page.

You should confirm:

- create works
- list and filtering work
- edit and deprecation controls work
- access request tracking works
- provider sync works
- delete works
- adjacent navigation into **Provider Profiles** and **Model Usage** feels coherent

## Setup

1. Log in with an org-admin, org-manager, workspace-admin, or platform-admin session.
2. Open **AI Hub** from the left navigation.
3. Keep **Provider Profiles** and **Model Usage** available in separate tabs for cross-checks.

## Manual steps

### 1. Create a model card

Create a new card with values like:

- Name: `workspace-demo-model`
- Provider: `ollama`
- Description: `Workspace-owned validation card`
- Context window: `32768`
- Input cost / 1K: `0.0001`
- Output cost / 1K: `0.0002`
- Capabilities: `chat, reasoning`
- Tags: `lab, workspace`

Verify the new card appears in the inventory list.

### 2. Review filters

1. Search by the model name.
2. Filter by provider `ollama`.
3. Filter by tag `lab`.
4. Toggle **Show featured models only** after marking the card featured in the next step.

Verify the filters narrow the list correctly.

### 3. Edit and deprecate the card

Edit the created card and:

- mark it as `Featured`
- mark it as `Deprecated`
- add a deprecation notice such as `Replace with the promoted default after validation`
- append capability `tools`
- append tag `featured-candidate`

Verify the badges and deprecation notice render in the card list.

### 4. Record an access request

Use **Request Access** on the card.

Verify the access-request count increments in the inventory list.

### 5. Sync a provider baseline

Open **Sync Provider Catalog** and run a sync for `OpenAI`.

Verify:

- the sync completes successfully
- new provider cards appear in AI Hub
- those cards can be edited after sync

### 6. Cross-check adjacent surfaces

1. Open **Provider Profiles** from the AI Hub header.
2. Open **Model Usage** from the AI Hub header.

Verify the catalog feels like the model-definition surface while those adjacent pages handle provider-level configuration and observed usage.

### 7. Clean up

Delete the manually created `workspace-demo-model` card.

Provider-synced cards can remain if you want them for later demo work.

## Automated companion

Run the matching smoke test:

```bash
uv run python scripts/runledger/exercise_ai_hub_catalog.py
```
