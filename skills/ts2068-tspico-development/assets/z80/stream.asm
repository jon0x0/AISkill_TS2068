; OPTIONAL sequential byte reader. Omit this file to pay zero ROM/RAM cost.
; stream_open HL=path; stream_get -> NC A=byte; C A=7 EOF or error.
; stream_close abandons buffered bytes and closes; no whole-file allocation.
; Stream number 202 is reserved while open; all code is reentrant only with
; serialized TPI access. Totals count delivered bytes, modulo 2^32.
STREAM_BASE equ $7c00
STREAM_ACTIVE equ STREAM_BASE
STREAM_PTR equ STREAM_BASE+1
STREAM_LEFT equ STREAM_BASE+3
STREAM_TOTAL equ STREAM_BASE+4
STREAM_BUFFER equ $e000
STREAM_NUMBER equ 202

stream_open:
        push hl
        call stream_close
        pop hl
        ret c
        ld de,mode_rb
        ld a,STREAM_NUMBER
        call f_open
        ret c
        ld a,1
        ld (STREAM_ACTIVE),a
        xor a
        ld (STREAM_LEFT),a
        ld hl,STREAM_TOTAL
        ld b,4
.zero:  ld (hl),a
        inc hl
        djnz .zero
        ret

stream_get:
        ld a,(STREAM_ACTIVE)
        or a
        jr z,.closed
        ld a,(STREAM_LEFT)
        or a
        jr nz,.take
        ld hl,STREAM_BUFFER
        ld b,255
        ld a,STREAM_NUMBER
        call f_read
        ret c
        ld a,c
        or a
        jr z,.eof
        ld (STREAM_LEFT),a
        ld hl,STREAM_BUFFER
        ld (STREAM_PTR),hl
.take:  ld hl,(STREAM_PTR)
        ld a,(hl)
        inc hl
        ld (STREAM_PTR),hl
        push af
        ld hl,STREAM_LEFT
        dec (hl)
        ld hl,STREAM_TOTAL
        ld b,4
.count: inc (hl)
        jr nz,.counted
        inc hl
        djnz .count
.counted:
        pop af
        or a
        ret
.eof:   call stream_close
        ret c
.closed:ld a,7
        scf
        ret

stream_close:
        ld a,(STREAM_ACTIVE)
        or a
        ret z
        ld a,STREAM_NUMBER
        call f_close
        ret c
        xor a
        ld (STREAM_ACTIVE),a
        ld (STREAM_LEFT),a
        ret
