# TSPico wire protocol for a Z80 client

These are two distinct transports. The legacy notes apply to the demonstrated
original-firmware client, supported by recovered older handlers and the user
hardware report. Modern details are pinned to firmware-build commit
`6b72847e1121112e438d6d4c2ec41835df90f940`; consult that implementation before
generalizing to another revision. Source links are in
[assets-and-validation.md](assets-and-validation.md#evidence-and-sources).

## Ports and framing

| Property | Legacy | Modern 2.3 |
| --- | --- | --- |
| OUT `$0E` | Send bytes to RX FIFO | Same |
| IN `$0E` | Consume TX byte | Same |
| IN `$0F` | Also consumes shared FIFO data | Reads separate nonconsuming status register |
| Ready | Literal `$40` in TX FIFO | Bit 6 of status register |
| OUT `$0F`, `$03` | Not a reset; may become malformed input | SYNC/abort and reset transaction |

The FIFO does not stall the Z80 until MicroPython catches up. Use paced
`IN A,(n)` / `OUT (n),A`, not unpaced INIR/OTIR. Delays are part of the driver,
not optional overhead. Do not poll READY before every payload byte: legacy
polling would consume the payload, and modern auto-busy/status transitions
are defined at phase boundaries.

Every transaction starts with a ten-byte preheader:

| Offset | BASIC command | TAP block transfer |
| --- | --- | --- |
| 0 | `$42` = B | `$00` header or `$FF` data |
| 1 | TADDR: 0 SAVE-command, 1 LOAD/mount-command | 0 SAVE, 1 LOAD |
| 2 | `$FF` compatible old bank field; modern ROMs may send ROM ID | Bank, `$FF` for HOME |
| 3–4 | PMR1, little-endian | Session ID |
| 5–6 | PMR2, little-endian | Address |
| 7–8 | ASCII command length, little-endian | Payload length |
| 9 | XOR of bytes 0–8 | XOR of bytes 0–8 |

The B command body is `44, length_lo, length_hi, ASCII text, XOR`, with the
last byte equal to XOR of everything before it in that body. Length excludes
the three framing bytes and checksum, and the text has no transmitted NUL.
Command text includes `tpi:`. TADDR selects the firmware dispatcher, not whether
the command text happens to mention reading or writing. Modern channel commands
are TADDR 0, including `chrd`. Legacy directory/mount commands are TADDR 1;
legacy `cd` and `close` are TADDR 0. The reserved A/assembler command is not a
portable disk API.

For example, legacy `LOAD "tpi:dir"` with zero parameters has preheader
`42 01 FF 00 00 00 00 07 00 BB`, followed by a D-framed seven-character body.
Send its body only after the initial ACK/ready handshake below.

## Legacy transaction

1. Send the complete preheader, at paced byte intervals.
2. Consume initial `$01` from the shared TX FIFO, then consume the literal
   `$40` ready token. Bound both waits.
3. Send the D-framed command body and checksum.
4. Consume bytes until the next `$40` ready token. The exposed older
   `PROCESS_CMD` also queues an extra `$01` before receiving its body; this
   wait consumes that byte without interpreting it as the final result.
5. Read final status or function response. Drain it completely.
6. Leave time for handler cleanup and SD/MQ reactivation before another
   preheader. The supplied driver uses ~2.4 seconds; exposed legacy DIR even
   sleeps two seconds after its reply. This is a compatibility delay, not a
   universal SD completion guarantee.

The CP/M 2.2 cold loader uses shorter ordinary-reply guards but retains long
DIR/volume-transition guards. Its physical third-volume timeout informed that
choice; do not remove these waits merely because a functional emulator passes.
See [RAMDisk discovery and saves](banked-ram-and-disk-images.md#firmware-and-capabilities)
for quiet status-05 failures, bounded directory evidence, MEMDOCK parameters,
and modern single-TAP APPEND versus original-firmware chunk saves.

Unlike modern firmware there is no established reset/IDLE transaction here.
A timeout leaves the protocol boundary uncertain. Do not try modern SYNC as
recovery; restore a clean TS/Pico state before issuing another operation.
The legacy driver uses only port `$0E`; that is valid because both read ports
share the FIFO. Do not substitute a modern nonconsuming-status wait routine.

### Legacy responses and directories

- Plain status `$01` means success; other low status values are errors.
- `$81, exit_status, text..., 00` is a text response. Consume text even when
  the application does not display it. Firmware VERBOSE may enable this on
  otherwise ordinary commands, including TAP transfers.
- `$86, exit_status, pages...` is an interactive listing. In the original-ROM
  path, NUL ends a page; consume its ready token and send Y to continue, or N
  to stop. The final page contains `--- End of list (N to exit) ---`; send N.
  Newer legacy ROM paths may end with ETX (`$03`), which needs no further key.
  Do not confuse a page boundary with command completion or apply modern
  function-$86 cleanup rules to original firmware.

`LOAD "tpi:dir"` produces fixed-width formatted directory text, not a raw
array of filenames. It includes headers, 32-character rows, CRs, and scrolling
prompts. File names can be truncated; use the displayed three-digit number
with `LOAD "tpi:&nnn"` for a reliable indexed mount. `SAVE "tpi:cd NAME"`,
`SAVE "tpi:cd .."` and `SAVE "tpi:cd /"` change the global working directory.
The library can capture text into bounded scratch instead of calling a ROM
print function. Its 6 KB capture limit and 89-character command limit are
client bounds; drain/stop a full listing rather than overrunning memory.

### Legacy TAP LOAD

First mount the desired TAP with a TADDR-1 B command `tpi:filename.tap` or
`tpi:&nnn`. A mount is not a transfer into CPU memory. Then:

1. Send a header-block preheader: flag `$00`, TADDR 1, payload length 17.
   Consume initial `$01` and literal-ready `$40`.
2. OUT expected flag `$00`. Read flag `$00`, 17 header bytes, then checksum.
   Accumulate XOR over flag, payload and checksum; the residual should be 0.
3. OUT that XOR residual. The handler consumes the expected-flag echo and
   residual as its two acknowledgments. Consume `$40` and drain final reply.
4. Interpret the 17 bytes: type (1), name (10), length (2), start/parameter (2),
   other parameter (2). Words are little-endian. This library accepts type 3,
   CODE. Reject an oversized block **before** requesting its data.
5. Send another preheader: flag `$FF`, TADDR 1, length from the header. Repeat
   the same exchange: OUT `$FF`, IN flag, exactly length bytes, IN checksum,
   OUT residual, consume ready/final reply.

There is no response length prefix in this TAP payload phase. Requesting a
guessed length can leave bytes in the FIFO or under-read the packet. The
library loads the first header/data pair; it does not implement arbitrary
TAP searching or execution. Preserve the flag/checksum error after draining
the final verbose reply. A successful receive is not permission to jump into
the data or run BASIC.

### Legacy TAP SAVE

Close the previous mount with TADDR-0 `tpi:close` to clear APPEND mode. Then:

1. Send flag `$00`, TADDR 0, header length 17 preheader; consume initial ACK
   and `$40`.
2. Send the 21-byte SLVM header:
   `00, SID_lo, SID_hi, type=3, name[10], length_LE, start_LE, param_LE, XOR`.
   Use session ID zero consistently. In the recovered SAVE handler the XOR
   excludes the two session bytes; zero session values make this agree with
   an XOR including them. Name is space-padded, not NUL-padded.
3. Consume `$40`, then status `$01`, before sending the data block.
4. Send `FF, SID_lo, SID_hi, payload[length], XOR(flag+payload)`.
5. Consume `$40` and the final plain/verbose reply, then allow cleanup/SD work.

Firmware constructs a normal TAP file with two little-endian length-prefixed
blocks, each containing flag, payload and XOR; session bytes are removed.
The bundled API restricts basename to 1–10 letters/digits and firmware appends
`.tap`. Validate before closing/mutating a destination. Application UI should
confirm overwrite first. The payload accepts all byte values, including `$17`.

The recovered handler sends its final reply before writing the file to SD.
Do not describe that reply as an atomic/durable commit. Read back when needed
and document limitations; a fixed cleanup delay cannot guarantee power-loss
durability or successful SD media writes.

## Modern 2.3 transaction

Status bits: READY bit 6, IDLE bit 3, RECOVERED bit 2 **active low**. Values
used by the pinned implementation: `$FF` idle, `$F7` ready in a transaction,
`$FB` recovered, `$00` busy. Only test RECOVERED after READY is set; busy also
has bit 2 clear.

1. Wait READY+IDLE (mask `$48` equal `$48`) before beginning another command.
2. OUT `$03` to port `$0F`; wait READY+IDLE. SYNC empties both FIFOs and leaves
   exactly one `$01` preload. Do this only after selecting a compatible backend.
3. Send ten-byte preheader. Read the `$01` preload from `$0E`, then wait READY.
4. Send D body/checksum, then wait READY and read the command's response.
5. Consume all response bytes. A channel answer may be READY but not IDLE;
   wait for the firmware's command tail to drain/reload/mark IDLE before SYNC.

Modern ready tokens are not in the data FIFO. Do not read/discard a `$40`
there: it may be real data. Every OUT makes status busy, but the firmware
signals phase readiness, not readiness after each byte of an incomplete body.
Some older dual-port firmware lacks the current SYNC/IDLE contract; a broad
"2.x" label is insufficient to establish compatibility.

### Raw files and directories

All of these commands use B/TADDR 0 and D-framed ASCII text:

| Command text | PMR1 | PMR2 | Reply |
| --- | --- | --- | --- |
| `tpi:chopen rb /path` | Stream 0–255 | 0 | Status |
| `tpi:chopen wb /path` | Stream | 0 | Status; may create/truncate |
| `tpi:chopen r d:/folder/*` | Stream | 0 | Status; directory becomes readable stream |
| `tpi:chrd` | Stream | Requested bytes 1–255; 0 means 255 | Counted data or EOF |
| `tpi:chwr HEX...` | Stream | 0 | Status |
| `tpi:chclose` | Stream | 0 | Status |

`chrd` reply is `01, n, n data bytes, XOR(data seed 0)` or status `$07` EOF.
There is no extra ordinary-reply/C_END phase. Validate `1 <= n <= requested`
before writing a caller's buffer and consume the checksum. Reads need roughly
75 microseconds between bytes for the pinned implementation; use the paced
driver. The complete-file helper probes one extra byte into private scratch
when the destination fills, distinguishing exact-capacity EOF from truncation.

Binary mode is needed for byte-exact reads. Text mode translates TS2068 CR
and tokens. Directory channel names are CR-delimited and folders have `/`.

**Binary write exception:** in the pinned firmware, decoded byte `$17` is a
TAB/position escape even in binary mode. Hex-encoding it in `chwr` does not
remove that interpretation. The bundled writer rejects any `$17` in the whole
input before opening `wb`; the per-write helper also checks. It uses at most
96 decoded bytes per hex command. Full arbitrary binary SAVE requires a
verified alternative command, an application-level encoding, or a firmware
change; do not promise a raw binary roundtrip otherwise. This restriction is
not a property of legacy TAP SAVE or of all hypothetical future firmware.

Plain `$01` succeeds. `$81` contains exit status plus NUL-terminated text and
must be drained. The bundled modern ordinary-reply helper supports `$81` and
aborts unsupported function codes with modern SYNC; a client needing interactive
`$82/$84/$86/$88` replies must implement their complete matching contracts.
Do not silently discard a prompt that is waiting for keyboard input.

## Errors, recovery and detection

Wire errors include 03 filename, 04 parameter, 05 command, 07 EOF. Bundled
client errors are E0 timeout, E1 sync/flag, E2 XOR, E3 unsupported, E4 capacity,
E5 reserved-write-byte, E6 path/name, E7 UI cancel, E8 truncated-name handling.
Keep wire codes and host UI errors distinguishable. E0 is a client timeout,
not a firmware version number or a specific file-not-found condition.

Autodetection is not included. A future detector must run at a clean boundary,
cache its selection, account for all legacy bytes consumed, reject a floating
bus, and avoid modern writes before identification. Offer explicit selection
and compile out unused backend/detector code. Failure to detect modern status
does not prove legacy compatibility. Validate detection against legacy, modern,
absent/busy devices and stale bytes before enabling it in a general library.

## Recovering an undocumented variant

Search the firmware build tree as well as the original card/filesystem repo:
low-level modules may be frozen into the UF2 and absent from the SD/Pico file
listing. Read the dispatcher plus its transport helper together; recovering
only command names does not recover phase order or checksums. Gustavo's
preliminary specification helps identify packets, but the exact deployed
firmware and ROM client resolve disagreements.

Decode UF2 using block target addresses and payload lengths. Do not concatenate
payloads while ignoring gaps or assume strings identify executable handlers.
Use version strings and qstr/constant pools to locate functions, then trace
bytecode or find matching source history. Disassemble supplied TAP machine-code
blocks and the exact client ROM when source is absent; record ACK/ready/data/key
order, packet lengths, XOR coverage and termination. ROM addresses are analysis
evidence, not runtime dependencies for a protocol-only implementation.

Exercise a recovered client against actual handlers when possible and record
which parts remain modeled. Use known TAP fixtures and byte-exact roundtrips
before trusting a file dialog. A successful hardware test narrows uncertainty
for its firmware and flow; it does not validate unrelated modern commands.
