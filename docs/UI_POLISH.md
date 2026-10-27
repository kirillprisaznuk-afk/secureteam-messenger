# Desktop UI polish

## Scope and visual audit

This pass refines the existing PyQt5 presentation. Networking, authentication,
authorization, database architecture, request contracts, and application services
are unchanged. The previous modernization report remains a historical record.

The initial UI used the same visual weight for messages and metadata, raw ISO
message timestamps, dense admin headers, an oversized Online column, and small
inconsistent dialogs. Conversation names lacked secondary context, destructive
controls looked like ordinary actions, and keyboard focus/control styling varied
between windows. These were presentation issues, not a reason to rebuild the app.

## Design system

`client/gui/styles.py` owns the dark palette, shared stylesheet, table defaults,
application palette, and text elision. Logical spacing follows an 8-pixel rhythm
with 12/16/20/24-pixel insets where appropriate. Segoe UI is preferred on Windows;
Qt uses its available font fallback on other systems. Main titles, section titles,
body text and secondary metadata have distinct weights/sizes.

Panels, borders, primary/secondary/destructive buttons, disabled/hover/pressed/
focus states, input fields, dropdowns, list selections, table headers, scrollbars,
and notifications use consistent styling. The Fusion base style plus an explicit
dark application palette keeps popup controls consistent. Two small packaged SVGs
provide legible dropdown/check indicators; no generated image assets are used.

## Login and dialogs

Sign-in has a clear heading, a grouped form, full-width primary action, persistent
transport disclosure, and a distinct inline error state. Labels have keyboard
mnemonics and buddies; fields have accessible names and an explicit tab sequence.

Create-user/role and membership dialogs share the theme, larger readable layouts,
clear action names, and properly sized controls. Existing validation, passwords,
role choices, confirmation questions, and requests retain their behaviour.

## Messenger

- A resizable, non-collapsing sidebar uses two-line conversation rows with full
  names in tooltips, selected/hover/focus states, and explicit archive labels.
- The conversation heading, history and composer have separate visual sections.
  Long usernames/titles elide without widening the entire window.
- Incoming and outgoing message rows differ in alignment and background, while
  always naming the sender. Dates/times are displayed in the local timezone at
  minute precision. Stored timestamps and message content remain unchanged.
- Message rows escape all user text before inserting presentation HTML. Literal
  markup, spaces, tabs, line breaks and long words remain readable/copyable.
  Unchanged polling results retain text selection instead of relaying out history.
- Empty, disconnected, archived, and ready-to-compose states use readable guidance.
  The single-line composer, Enter-to-send, paging, polling and reconnect flows remain.

## Administration

Users have proportioned columns, alternating rows, useful tooltips, and readable
status colours plus text. Account roles/identifiers retain their existing values.
Conversation administration separates create/refresh from edit/archive/delete
controls and presents name, membership count, owner and archive status clearly.
Audit rows use readable local times with original timestamps in tooltips, sensible
column widths, and horizontal scrolling when the window is narrow. Tables remain
read-only and existing permissions/actions are preserved.

## Visual and automated verification

Local verification used Windows, Python 3.12.14 and PyQt5 5.15.11. All **88 tests**
passed: the existing 82 tests plus six presentation checks. Ruff lint, format,
source compilation, documentation links, and the candidate-file privacy scan passed.
A wheel build verified that both SVGs are packaged and no database/key files are
included. Remote CI results are reported with the published commit in the delivery.

Focused checks cover safe literal markup, whitespace and 10,000-character word
wrapping, literal name tooltips, selection retention, minimum-size layout/long identities, password masking,
keyboard tab order, label buddies, and text contrast. The selected body/secondary/
muted text colours meet a measured 4.5:1 contrast against the tested panel/message
backgrounds. This is a colour-palette check, not a full accessibility certification.

The screenshot utility ran against synthetic accounts on a temporary real TCP
server at explicit scale factors **1.0, 1.5 and 2.0**. All runs checked control
containment at minimum window sizes. Compact messenger, login and membership
captures were opened for visual inspection, as were the seven portfolio views.
Scaling is enabled before QApplication, including high-DPI pixmaps and fractional
scale handling. The application uses logical dimensions, not pixel-scaled fonts.

## Authentic screenshots

`python -m scripts.capture_screenshots` creates these actual offscreen Qt captures
from a live local server, random ephemeral credentials, and a temporary database:

- `screenshots/login.png`
- `screenshots/conversation.png`
- `screenshots/administration.png`
- `screenshots/chat-administration.png`
- `screenshots/audit.png`
- `screenshots/user-dialog.png`
- `screenshots/members-dialog.png`

The README embeds the current views. To keep exploratory captures out of the
portfolio directory, use `--output-dir PATH --check-layouts`. `QT_SCALE_FACTOR`
can select a test scale. The helper fixes offscreen font DPI for repeatable renders;
the real desktop application follows the platform DPI configuration.

## Limits

Offscreen captures and geometry checks do not establish native Windows
per-monitor DPI transitions, actual screen-reader behaviour, or fit on every
physical display. Those remain platform checks; no owner retest is requested or
claimed. Large audit tables intentionally allow horizontal scrolling. The composer
remains single-line. This pass adds no delivery features, permissions, transport
changes, or database migrations.
