# Data Model: Shareable Map Links

**Date**: 2026-03-12 | **Branch**: `008-shareable-map-links`

## Entities

### QuestionIndex

A deterministic mapping from every question in the question bank to a stable integer index. Used for compact binary encoding in tokens.

| Field | Type | Description |
|-|-|-|
| version | uint8 | Index version — increments when questions are added/removed |
| entries | Map\<string, number\> | question_id → integer index |
| reverseEntries | Map\<number, string\> | integer index → question_id |

**Construction rule**: Sort all questions across all domains by `(domain_ids[0], id)` alphabetically. Assign index 0, 1, 2, ... in sort order.

**Invariants**:
- Every question has exactly one index
- Index assignment is deterministic (same question bank → same indices)
- Indices are contiguous (0 to N-1 for N questions)

### ResponseToken

A versioned, compressed, URL-safe encoding of a user's quiz responses.

| Field | Type | Description |
|-|-|-|
| version | uint8 | Token format version (currently 1) |
| count | uint16 | Number of encoded responses |
| entries | Array\<{index: uint16, value: int8}\> | Sparse response pairs |

**Value encoding**:

| Response State | Value |
|-|-|
| Unanswered | 0 (not stored — sparse) |
| Skipped | 1 |
| Correct | 2 |
| Incorrect | -1 (0xFF as uint8) |

**Binary layout**: `[version:1][count:2][index:2,value:1]×count`
- Total bytes: `3 + (count × 3)`
- Big-endian for multi-byte integers

**Lifecycle**:
1. **Created** when user clicks "Copy Link" in share modal
2. **Compressed** via pako deflate
3. **Encoded** to base64url string
4. **Appended** to URL as `?t=` parameter
5. **Decoded** when recipient opens the URL
6. **Inflated** via pako inflate
7. **Mapped** back to response objects using QuestionIndex reverse lookup

### SyntheticResponse

A minimal response object reconstructed from a decoded token. Compatible with the existing `$responses` store format for rendering purposes.

| Field | Type | Description |
|-|-|-|
| question_id | string | From QuestionIndex reverse lookup |
| is_correct | boolean | true if value === 2 |
| is_skipped | boolean | true if value === 1 |
| x | number | From question data (looked up by question_id) |
| y | number | From question data (looked up by question_id) |

**Note**: SyntheticResponses are NOT written to localStorage. They exist only in memory for the shared view session.

## Relationships

```text
QuestionIndex ──builds──> ResponseToken (encoding)
ResponseToken ──decodes──> SyntheticResponse[] (decoding)
SyntheticResponse ──feeds──> GP Estimator ──renders──> Heatmap
```

## State Transitions

```text
[User answers questions]
    │
    ▼
$responses (localStorage) ──encode──> ResponseToken ──compress──> base64url ──> URL

[Recipient opens URL]
    │
    ▼
URL ──parse ?t=──> base64url ──inflate──> ResponseToken ──decode──> SyntheticResponse[]
    │
    ▼
[Shared view renders map with SyntheticResponses]
```
