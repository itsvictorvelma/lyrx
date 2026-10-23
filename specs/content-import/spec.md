---
cursor:
  subagentId: "bc-43f25a2f-93d8-5ec7-9282-d2774358e7bf"
---

# Developer song import specification

Parent plan: [Prototype 1 build plan](../../AGENTS.md)

Dependencies and consumers:

- [Application foundation](../app-foundation/spec.md)
- [Song Library](../song-library/spec.md)
- [Learn Song](../learn-song/spec.md)

## Goal

Let a developer import one pre-authored song bundle safely and repeatably without building public uploads, a general admin system, or an in-browser text editor.

## Availability and security boundary

- Import Song exists only in local development.
- Route: `/import`.
- Its backend mutation is registered only in local development and binds to localhost.
- Production frontend and backend omit the feature entirely.
- A hidden navigation link, environment check in React, or lack of documentation is not sufficient protection.
- No authentication is added for this tool because it is not remotely exposed.

## Input contract

### Required files

Names are exact:

```text
original.txt
pronunciation.txt
translation.txt
audio.mp3
```

Exactly one of each is accepted. ZIP archives, folders, alternate names, remote URLs, and extra files are rejected.

### Required metadata fields

- Stable song ID/slug
- Title
- Artist
- Source language, Japanese for the working bundle
- Target language, English for the working bundle

Optional metadata must be explicitly enumerated before implementation; arbitrary key/value input is out of scope.

## Text normalization and alignment

The importer:

1. Requires UTF-8 and handles/rejects a UTF-8 BOM consistently.
2. Normalizes CRLF and CR to LF.
3. Ignores one terminal newline consistently across all files.
4. Splits each file into rows without trimming meaningful internal characters.
5. Compares row counts before constructing line records.
6. Rejects the complete import if counts differ.
7. Allows a blank separator only when the same index is blank in all three files.
8. Omits all-three-blank separators from stored lyric units.
9. Rejects a row if only one or two layers are blank.
10. Constructs one ordered unit per retained row.

Layer semantics:

- `original.txt` → Japanese
- `pronunciation.txt` → Pronunciation (Romaji), reader-friendly Hepburn-style sound representation
- `translation.txt` → Direct Meaning

The importer checks that the files line up. It does not check linguistic correctness.

## Audio validation

- Require the exact filename `audio.mp3`.
- Enforce a configurable request/file-size ceiling.
- Inspect file signature/container with a media parser; do not trust extension or client MIME.
- Reject unreadable, empty, encrypted, or unsupported media.
- Measure duration.
- Calculate a cryptographic checksum.
- Generate the destination storage key; ignore client paths and sanitize metadata-derived names.
- Stage the file outside the public media directory until all validation succeeds.

No transcoding, waveform generation, loudness normalization, or alternate formats are part of Prototype 1.

## Import transaction

1. Receive files into bounded temporary storage.
2. Validate metadata, text files, alignment, and audio.
3. Build a three-layer preview model.
4. Check stable ID and content/checksum conflicts.
5. Write database records and move media as one logical transaction.
6. On failure, roll back the database and remove staged/new media.
7. Return the stored song/version identifiers and validation summary.

Idempotency:

- An identical song ID, aligned content, metadata version, and audio checksum returns the existing result without duplication.
- Different content under an existing ID is a conflict unless the developer explicitly chooses the supported replace/new-version action.
- Replacement never overwrites the only known-good version before the new transaction succeeds.

A successful import is published immediately so the song list can return it. Submitting the same files again does not create a second copy. Different files for an existing song id are rejected unless replacement is confirmed.

## UI behavior

The Import Song screen contains:

- Screen heading and development-only warning
- Metadata form
- Four clearly labeled file inputs
- Validation summary
- Submit/progress state
- Error summary with links/focus to fields
- Success summary and aligned three-layer preview
- Explicit return to Song Library

Do not provide line editing, drag reorder, lyric generation, timing, waveform, public sharing, or account controls.

## Validation and error states

Use stable codes and actionable messages for:

- Missing/extra/wrongly named file
- Request/file too large
- Invalid UTF-8 or malformed text
- Different line counts, showing all three counts
- Partial blank row, showing row number and affected files
- Empty retained lyric set
- Missing/invalid metadata
- Invalid song ID/slug
- Unsupported/unreadable MP3
- Duplicate/idempotent import
- Existing-ID content conflict
- Database or media-copy failure

Client validation is advisory. Server validation is authoritative.

## Accessibility

- Each metadata and file field has a persistent label and described requirements.
- Error summary receives focus after failed submission and links to invalid inputs.
- Field errors are associated programmatically.
- Progress/success messages use appropriate live regions.
- Preview uses a semantic ordered list; each unit identifies Japanese, Pronunciation (Romaji), and Direct Meaning.
- Keyboard-only import is complete.
- No drag/drop-only interaction.
- File inputs remain operable at narrow widths and high zoom.

## Tests

### Unit

- Newline/BOM normalization
- Equal/mismatched line counts
- Full and partial blank rows
- Layer mapping
- Metadata validation
- MP3 validation/checksum
- Idempotency key/version rules
- Safe generated storage names

### Backend integration

- Valid import writes one coherent track/version/media file
- Every validation failure writes nothing
- Media-copy/database failures clean up both sides
- Identical re-import does not duplicate
- Different-content conflict is deterministic
- Production router/OpenAPI has no import mutation

### Frontend

- Required fields/files
- Loading/progress, success, and each major error family
- Error-summary focus behavior
- Three-layer preview order and labels
- Development route presence and production route absence

### End-to-end

- Import valid “Akuma no Ko” development fixture, return to library, open Learn Song.
- Submit mismatched files and verify no new song/media exists.
- Attempt production `/import` and mutation; both are unavailable.

Use a small test fixture in automated tests.

## Sequencing

1. Foundation contracts, models, migration, and environment guard.
2. Pure normalization/alignment validators.
3. MP3 inspection and staged storage.
4. Transaction/idempotency service.
5. Development mutation.
6. Import Song form and preview.
7. Production exclusion tests.

## Acceptance criteria

- The exact four-file bundle plus required metadata imports in development.
- Every retained line maps one-to-one across the three layers.
- Count and partial-blank mismatches are rejected with row/file details.
- Invalid audio is rejected before durable writes.
- Import is atomic and idempotent.
- Success publishes the song and shows the aligned preview.
- Production contains neither route nor mutation.
- Screen passes keyboard, focus, labeling, and responsive checks.

## Risks

- Different editors create newline/BOM false mismatches.
- Audio and lyric files leak into Git, images, logs, or public media.
- Database/media operations diverge after partial failure.
- A development flag accidentally becomes a remote admin surface.
- Romaji/direct meaning appear aligned but are linguistically wrong.

Mitigate with deterministic normalization, ignore rules and storage separation, staged atomic writes, route-absence tests, and human linguistic review.

## Non-goals and deferred work

- Public/user uploads
- Authentication or remote admin
- Arbitrary filenames/archive ingestion
- In-browser lyric editing
- Automatic romaji/translation generation
- Transcoding/object storage/moderation
- Timestamps, tap timing, waveform, synchronization
- Catalog/provider API import
