# Contract: URL Parameter Interface

**Version**: 1 | **Date**: 2026-03-12

## Query Parameters

| Parameter | Type | Required | Description |
|-|-|-|-|
| `t` | string (base64url) | No | Encoded response token. When present, app boots in shared view mode. |

## Behavior Matrix

| URL | Behavior |
|-|-|
| `/mapper/` | Normal app — landing screen, full UI |
| `/mapper/?t={valid_token}` | Shared view — minimal chrome, read-only map |
| `/mapper/?t=` | Normal app (empty token treated as absent) |
| `/mapper/?t={invalid}` | Normal app (decode failure → silent fallback) |
| `/mapper/?t={valid}&other=param` | Shared view (extra params ignored) |

## Shared View Mode

When a valid `?t=` token is detected:

1. **Skip** landing/welcome screen
2. **Load** "All (general)" domain bundle
3. **Decode** token into SyntheticResponse array
4. **Run** GP estimator with SyntheticResponses
5. **Render** map with heatmap + response dots
6. **Show** minimal chrome: map canvas + "Map your *own* knowledge!" CTA button
7. **Hide** header toolbar, quiz panel, video panel, minimap, drawer pulls

## CTA Button

- Text: "Map your *own* knowledge!"
- Action: Navigate to `/mapper/` (no token — starts fresh normal session)
- Position: Fixed bottom-center, visually prominent
- Style: Consistent with app primary button styling

## localStorage Interaction

- Shared view MUST NOT read from or write to localStorage
- Existing localStorage data is preserved but ignored during shared view
- Navigating to the main app via CTA uses normal localStorage-based state
