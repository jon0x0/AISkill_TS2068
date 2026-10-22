; Single FIFO protocol: both IN $0E and IN $0F consume a byte.
; Never OUT $0F and never wait for modern IDLE/status-register bits.
; All calls require exclusive ownership of the link. No firmware reset exists.
LEGACY_PHASE equ WORK_BASE+40
LEGACY_BYTE equ WORK_BASE+41
LEGACY_TADDR equ WORK_BASE+42
LEGACY_FLAG equ WORK_BASE+43
LEGACY_CRC equ WORK_BASE+44
LEGACY_TEXT equ WORK_BASE+45
LEGACY_FUNCTION equ WORK_BASE+46
LEGACY_USED equ WORK_BASE+47
LEGACY_REPLY_BUFFER equ $e000
LEGACY_REPLY_CAPACITY equ $1800
LEGACY_BUDGET equ WORK_BASE+$3c0

legacy_wait_ready:
        push bc
        push de
        ld de,20
        ld bc,0
.poll:  call tpi_rx
        ld (LEGACY_BYTE),a
        cp $40                          ; a literal FIFO token, not a bitmask
        jr z,.ok
        dec bc
        ld a,b
        or c
        jr nz,.poll
        dec de
        ld a,d
        or e
        jr nz,.poll
        pop de
        pop bc
        ld a,E_TIMEOUT
        scf
        ret
.ok:    pop de
        pop bc
        xor a
        ret

; Pace FIFO traffic for the original MicroPython handlers.
tpi_tx:
        out ($0e),a
        xor d
        ld d,a
        push bc
        ld b,24
.delay: djnz .delay
        pop bc
        ret
tpi_rx:
        push bc
        ld b,18
.delay: djnz .delay
        pop bc
        in a,($0e)
        ret

; HL = complete ten-byte preheader, including XOR. Initial 01 precedes 40.
legacy_preheader:
        ld a,1
        ld (LEGACY_PHASE),a
        ld b,10
        ld d,0
.send:  ld a,(hl)
        inc hl
        call tpi_tx
        djnz .send
        push bc
        ld bc,0
.ack:   call tpi_rx
        ld (LEGACY_BYTE),a
        cp 1
        jr z,.initial
        dec bc
        ld a,b
        or c
        jr nz,.ack
        pop bc
        ld a,E_TIMEOUT
        scf
        ret
.initial:
        pop bc
        ld a,2
        ld (LEGACY_PHASE),a
        jp legacy_wait_ready

; Common preheader construction. A=flag, E=TADDR, BC=length.
legacy_make_pre:
        ld hl,RX_BUFFER
        ld (hl),a
        inc hl
        ld (hl),e
        inc hl
        ld (hl),$ff
        inc hl
        ld (hl),0                       ; session ID / command PMR1
        inc hl
        ld (hl),0
        inc hl
        ld (hl),0                       ; address / command PMR2
        inc hl
        ld (hl),0
        inc hl
        ld (hl),c
        inc hl
        ld (hl),b
        ld hl,RX_BUFFER
        ld b,9
        xor a
.xor:   xor (hl)
        inc hl
        djnz .xor
        ld (hl),a
        ld hl,RX_BUFFER
        ret

; HL=NUL command, A=0 SAVE or 1 LOAD. No ROM interpreter involved.
legacy_command:
        ld (LEGACY_TADDR),a
        ld (CMD_PTR),hl
        ld bc,0
.length:ld a,(hl)
        or a
        jr z,.length_ok
        inc hl
        inc bc
        ld a,c
        cp 90                           ; original handler's buffer is only 100
        jr c,.length
        ld a,E_PATH
        scf
        ret
.length_ok:
        ld a,c
        or a
        jr nz,.nonempty
        ld a,E_PATH
        scf
        ret
.nonempty:
        ld (CMD_LENGTH),bc
        ld a,(LEGACY_TADDR)
        ld e,a
        ld a,'B'
        call legacy_make_pre
        call legacy_preheader
        ret c
        ld a,3
        ld (LEGACY_PHASE),a
        ld d,0
        ld a,'D'
        call tpi_tx
        ld bc,(CMD_LENGTH)
        ld a,c
        call tpi_tx
        ld a,b
        call tpi_tx
        ld hl,(CMD_PTR)
.body:  ld a,(hl)
        inc hl
        call tpi_tx
        dec bc
        ld a,b
        or c
        jr nz,.body
        ld a,d
        call tpi_tx
        ld a,4
        ld (LEGACY_PHASE),a
        jp legacy_wait_ready

; Allow legacy handlers to finish SD housekeeping/re-enable MQ after reply.
; Also accommodates DIR's explicit two-second post-reply sleep in 1.1.
legacy_settle:
        push bc
        push de
        ld de,5
.outer: ld bc,0
.inner: dec bc
        ld a,b
        or c
        jr nz,.inner
        dec de
        ld a,d
        or e
        jr nz,.outer
        pop de
        pop bc
        ret

; Capture 81/86 text into LEGACY_REPLY_BUFFER, bounded to LEGACY_REPLY_CAPACITY-1 bytes.
; For 86, 1.00 ends each page in NUL and waits for Y/N, including final page.
; The last page is recognized by its documented end-of-list prompt; send N.
; 1.1's final ETX is accepted as well. No UI calls in this transport.
legacy_reply:
        call tpi_rx
        ld (LEGACY_FUNCTION),a
        cp $81
        jr z,.text
        cp $86
        jr z,.text
        cp $80
        jr c,.plain
        ld a,E_FUNCTION
        scf
        ret
.plain: ld (REPLY_STATUS),a
        jp .finish
.text:  call tpi_rx
        ld (REPLY_STATUS),a
        ld hl,LEGACY_REPLY_BUFFER
        ld bc,LEGACY_REPLY_CAPACITY-1
        xor a
        ld (LEGACY_TEXT),a
        ld (LEGACY_BUDGET),a
        ld (LEGACY_BUDGET+1),a
.char:  call tpi_rx
        push af
        ld de,(LEGACY_BUDGET)
        dec de
        ld (LEGACY_BUDGET),de
        ld a,d
        or e
        jr z,.text_timeout
        pop af
        cp 3
        jr z,.terminate
        or a
        jr z,.page_end
        push af
        ld a,b
        or c
        jr z,.full
        pop af
        ld (hl),a
        inc hl
        dec bc
        jr .char
.full:  pop af
        ld a,1
        ld (LEGACY_TEXT),a
        jr .char                        ; drain the response even when full
.text_timeout:
        pop af
        ld (hl),0
        ld a,E_TIMEOUT
        scf
        ret
.page_end:
        ld a,(LEGACY_FUNCTION)
        cp $86
        jr nz,.terminate
        call legacy_wait_ready
        ret c
        push hl
        push bc
        ld de,LEGACY_REPLY_BUFFER
        or a
        sbc hl,de
        ld b,h
        ld c,l
        ld hl,LEGACY_REPLY_BUFFER
        call legacy_has_end
        pop bc
        pop hl
        jr c,.stop
        ld a,(LEGACY_TEXT)
        or a
        jr nz,.stop                     ; bounded list: stop instead of overrunning
        ld a,'Y'
        ld d,0
        call tpi_tx
        jr .char
.stop:  ld a,'N'
        ld d,0
        call tpi_tx
.terminate:
        ld (hl),0
        ld de,LEGACY_REPLY_BUFFER
        or a
        sbc hl,de
        ld (LEGACY_USED),hl
.finish:
        call legacy_settle
        ld a,(REPLY_STATUS)
        cp 1
        jr nz,.error
        ld a,(LEGACY_TEXT)
        or a
        jr z,.ok
        ld a,E_CAPACITY
.error: scf
        ret
.ok:    xor a
        ret

; Carry if captured text contains the original firmware's final-page prompt.
legacy_has_end:
        ld a,b
        or c
        ret z
.scan:  ld a,(hl)
        cp '-'
        jr nz,.next
        push hl
        push bc
        ld de,legacy_end_text
.match: ld a,(de)
        or a
        jr z,.found
        ld a,b
        or c
        jr z,.miss
        ld a,(de)
        cp (hl)
        jr nz,.miss
        inc de
        inc hl
        dec bc
        jr .match
.found: pop bc
        pop hl
        scf
        ret
.miss:  pop bc
        pop hl
.next:  inc hl
        dec bc
        ld a,b
        or c
        jr nz,.scan
        or a
        ret
legacy_end_text: db '--- End of list (N to exit) ---',0

legacy_execute:
        push af
        xor a
        ld (LEGACY_TEXT),a
        ld (LEGACY_USED),a
        ld (LEGACY_USED+1),a
        pop af
        call legacy_command
        ret c
        jp legacy_reply
