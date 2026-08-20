# WU-007: Plugins Collapse Ownership Refresh

- **Status**: NOT_STARTED
- **Bundle**: 07-Platform - C (Utility Route Collapse and Discovery Ownership)
- **Target**: 07-PLATFORM-AND-UTILITY/plugins
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Platform: Plugins | Org: Onboarding | 07x01 | STRONG | STRONG |
| Platform: Plugins | Platform: Plugins | 07x07 | STRONG | STRONG |
| Platform: Plugins | Build: Evaluation studio | 07x06 | PARTIAL | STRONG |
| Platform: Plugins | Safety: Tool registry | 07x04 | N/A | PARTIAL |
| Platform: Plugins | Observe: Monitoring | 07x03 | N/A | PARTIAL |

## Paired Features (files to update)

- `07-PLATFORM-AND-UTILITY/GAP-MATRIX.md` - Plugins row
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - Plugins cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md`
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Plugins as a collapsed compatibility route whose backend capabilities still affect setup, governance, and runtime-adjacent workflows.
- **UI**: Keep the collapse discipline clear while improving the onboarding-owned discovery story.
- **Docs**: Remove ambiguity about whether `/plugins` is a real first-class admin surface.
- **Postman**: Review the missing plugin request coverage through the lens of collapsed ownership.
- **Scripts/Examples**: Add or defer support coverage intentionally based on the collapsed-route stance.

## Acceptance Criteria

1. Plugins is re-audited as a collapsed ownership surface, not a ghost product page
2. Onboarding, governance, evaluation, and monitoring relationships are explicitly covered
3. Current `N/A` plugin relationships are re-reviewed and updated where needed
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
