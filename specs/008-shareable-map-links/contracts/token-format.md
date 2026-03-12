# Contract: Response Token Binary Format

**Version**: 1 | **Date**: 2026-03-12

## Wire Format

```text
Byte 0:       version (uint8) — currently 0x01
Bytes 1-2:    count (uint16 big-endian) — number of response entries
Bytes 3+:     entries, each 3 bytes:
              [0-1] index (uint16 big-endian) — question index
              [2]   value (int8) — response value
```

## Value Encoding

| Response | Encoded Value | Byte Representation |
|-|-|-|
| Correct | 2 | 0x02 |
| Skipped | 1 | 0x01 |
| Incorrect | -1 | 0xFF |
| Unanswered | 0 | (not stored) |

## Compression

1. Serialize to binary using the wire format above
2. Compress with raw DEFLATE (pako `deflate` with `raw: true`)
3. Encode compressed bytes as base64url (RFC 4648 §5): `+` → `-`, `/` → `_`, strip `=` padding

## URL Format

```text
https://context-lab.com/mapper/?t={base64url_token}
```

## Size Guarantees

| Answered Questions | Raw Bytes | Compressed (est.) | Base64url Chars | Total URL Length |
|-|-|-|-|-|
| 50 | 153 | ~100 | ~134 | ~175 |
| 100 | 303 | ~200 | ~268 | ~309 |
| 200 | 603 | ~380 | ~508 | ~549 |
| 500 | 1503 | ~800 | ~1068 | ~1109 |
| 2500 (all) | 7503 | ~3000 | ~4000 | ~4041 |

Base URL (`https://context-lab.com/mapper/?t=`) = 41 characters.

## Decoding Rules

1. Extract `t` parameter from URL query string
2. Restore base64url: `-` → `+`, `_` → `/`, re-pad with `=` to multiple of 4
3. Decode base64 to bytes
4. Inflate with pako (`inflate` with `raw: true`)
5. Parse version byte — if unsupported version, abort (fall back to normal app)
6. Parse count (bytes 1-2, big-endian)
7. For each entry: read index (uint16 BE), value (int8)
8. Look up question_id from QuestionIndex using the token's version
9. Skip entries whose index has no matching question (question was removed)

## Versioning

- Version byte `0x01`: Initial format as described above
- Future versions may change field sizes or add metadata
- Decoders MUST check the version byte and reject unknown versions gracefully
