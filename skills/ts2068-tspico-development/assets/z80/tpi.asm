; ROM-independent TPI 2.x transport. No ROM calls, self modification or EI.
; Callers serialize access, supply a writable stack, preserve their bank map.
; Errors: carry set, A=wire status or E_*. Success carry clear.

tpi_wait_idle:
        ld bc,0
.poll:  in a,($0f)
        and $48
        cp $48
        ret z
        dec bc
        ld a,b
        or c
        jr nz,.poll
        ld a,E_TIMEOUT
        scf
        ret

tpi_wait_ready:
        push bc
        push de
        ld de,20
        ld bc,0
.poll:  in a,($0f)
        bit 6,a
        jr nz,.ready
        dec bc
        ld a,b
        or c
        jr nz,.poll
        dec de
        ld a,d
        or e
        jr nz,.poll
        ld a,E_TIMEOUT
.fail:  pop de
        pop bc
        scf
        ret
.ready: bit 2,a
        ld a,E_SYNC
        jr z,.fail
        pop de
        pop bc
        or a
        ret

; Explicit reset can recover a stalled prior exchange (2.x firmware only).
tpi_reset:
        ld a,3
        out ($0f),a
        jp tpi_wait_idle

; About 55 us between writes at 3.528 MHz. No per-byte ready poll.
tpi_tx:
        out ($0e),a
        xor d
        ld d,a
        push bc
        ld b,11
.delay: djnz .delay
        pop bc
        ret

; At least 75 us per received byte, including the call overhead.
tpi_rx:
        push bc
        ld b,18
.delay: djnz .delay
        pop bc
        in a,($0e)
        ret

; HL=NUL-terminated ASCII command; PMR1/2=parameters. Leaves answer unread.
; Length <=255 (COMMAND_BUFFER); an empty command is rejected.
tpi_command:
        ld (CMD_PTR),hl
        ld bc,0
.length:ld a,(hl)
        or a
        jr z,.have_length
        inc hl
        inc bc
        ld a,b
        or a
        jr z,.length
        ld a,E_CAPACITY
        scf
        ret
.have_length:
        ld a,c
        or a
        jr nz,.nonempty
        ld a,E_PATH
        scf
        ret
.nonempty:
        ld (CMD_LENGTH),bc
        call tpi_wait_idle
        ret c
        call tpi_reset
        ret c
        ld d,0
        ld a,'B'
        call tpi_tx
        xor a
        call tpi_tx
        ld a,$ff
        call tpi_tx
        ld a,(PMR1)
        call tpi_tx
        ld a,(PMR1+1)
        call tpi_tx
        ld a,(PMR2)
        call tpi_tx
        ld a,(PMR2+1)
        call tpi_tx
        ld bc,(CMD_LENGTH)
        ld a,c
        call tpi_tx
        ld a,b
        call tpi_tx
        ld a,d
        call tpi_tx
        in a,($0e)
        cp 1
        jr z,.preload_ok
        ld a,E_SYNC
        scf
        ret
.preload_ok:
        call tpi_wait_ready
        ret c
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
        jp tpi_wait_ready

; Ordinary reply: plain status or 81h message. Other functions are aborted.
; Text is drained, never printed, so verbose firmware cannot corrupt a UI.
tpi_reply:
        call tpi_rx
        cp $81
        jr z,.message
        cp $80
        jr nc,.unsupported
.status:cp 1
        jr nz,.error
        xor a
        ret
.error: scf
        ret
.message:
        call tpi_rx
        ld (REPLY_STATUS),a
        ld bc,0
.drain: call tpi_rx
        or a
        jr z,.end
        dec bc
        ld a,b
        or c
        jr nz,.drain
        call tpi_reset
        ld a,E_TIMEOUT
        scf
        ret
.end:   ld a,(REPLY_STATUS)
        jr .status
.unsupported:
        call tpi_reset
        ld a,E_FUNCTION
        scf
        ret

tpi_execute:
        call tpi_command
        ret c
        jp tpi_reply
