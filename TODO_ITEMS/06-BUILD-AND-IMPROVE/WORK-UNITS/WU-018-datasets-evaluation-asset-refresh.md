# WU-018: Datasets Evaluation Asset Refresh

- **Status**: COMPLETED
- **Bundle**: 06-Build - C (Evaluation and Replay Studio)
- **Target**: 06-BUILD-AND-IMPROVE/datasets
- **Created**: 2026-08-16
- **Completed**: 2026-09-02

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Datasets | Org: Workspaces | 06x01 | PARTIAL | STRONG |
| Build: Datasets | Observe: Request explorer | 06x03 | PARTIAL | STRONG |
| Build: Datasets | FinOps: Chargeback | 06x05 | PARTIAL | STRONG |
| Build: Datasets | Build: Evaluation studio | 06x06 | PARTIAL | STRONG |
| Build: Datasets | Build: Experiments | 06x06 | PARTIAL | STRONG |
| Build: Datasets | Build: Replay lab | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Datasets row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Datasets cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Datasets as evaluation assets under the studio umbrella, not a detached side surface.
- **UI**: Tighten dataset edit/update expectations and links into experiments and replay.
- **Docs**: Position datasets as first-class evaluation inputs with runtime and cost implications.
- **Postman**: Keep dataset lifecycle and studio-linked flows aligned.
- **Scripts/Examples**: Add a dataset-driven evaluation scenario with cost and evidence overlays.

## Acceptance Criteria

1. Datasets are re-audited as evaluation-owned assets
2. Studio, experiment, replay, and attribution relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
