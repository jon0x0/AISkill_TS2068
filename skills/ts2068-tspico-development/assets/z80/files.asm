; Core file interface, independent of display, keyboard, BASIC and ROM.
; f_open: A=stream, HL=path, DE=mode string (rb/wb/ab). Path <=191 bytes.
; f_close: A=stream. f_read: A=stream B=1..255 HL=destination.
; f_read returns BC=actual count, 0 at EOF; reads all packet bytes/checksum.
; f_write: A=stream B=count(1..96) HL=data. Rejects $17 before writing.
; f_load: HL=path DE=destination BC=capacity; FILE_DONE=bytes read.
; f_save: same inputs (BC=length). Entire input preflighted before open wb.

str_copy:                              ; HL source, DE destination, copies NUL
        ld a,(hl)
        ld (de),a
        inc hl
        inc de
        or a
        jr nz,str_copy
        dec de                         ; points at destination terminator
        ret

f_open:
        ld (PMR1),a
        xor a
        ld (PMR1+1),a
        ld (PMR2),a
        ld (PMR2+1),a
        push hl
        push de
        ld hl,cmd_open
        ld de,COMMAND_BUFFER
        call str_copy
        pop hl
        call str_copy
        ld a,' '
        ld (de),a
        inc de
        pop hl
        ld b,191
.path:  ld a,(hl)
        ld (de),a
        inc de
        inc hl
        or a
        jr z,.send
        djnz .path
        ld a,E_PATH
        scf
        ret
.send:  ld hl,COMMAND_BUFFER
        jp tpi_execute

f_close:
        ld (PMR1),a
        xor a
        ld (PMR1+1),a
        ld (PMR2),a
        ld (PMR2+1),a
        ld hl,cmd_close
        jp tpi_execute

f_read:
        ld (FILE_CHUNK),hl
        ld (PMR1),a
        xor a
        ld (PMR1+1),a
        ld (PMR2+1),a
        ld a,b
        or a
        jr nz,.count_ok
        ld a,255
.count_ok:
        ld (PMR2),a
        ld hl,cmd_read
        call tpi_command
        ret c
        call tpi_rx
        cp 7
        jr z,.eof
        cp 1
        jr nz,.error
        call tpi_rx
        or a
        jr z,.bad_count
        ld c,a
        ld a,(PMR2)
        cp c
        jr c,.bad_count
        ld a,c
        ld b,a
        ld e,0
        ld hl,(FILE_CHUNK)
.bytes: call tpi_rx
        ld (hl),a
        inc hl
        xor e
        ld e,a
        djnz .bytes
        call tpi_rx
        cp e
        jr nz,.bad_crc
        ld b,0
        xor a
        ret
.eof:  ld bc,0
        xor a
        ret
.bad_crc:
        ld a,E_CHECKSUM
        jr .error
.bad_count:
        call tpi_reset
        ld a,E_CAPACITY
.error: ld bc,0
        scf
        ret

f_write:
        ld (PMR1),a
        xor a
        ld (PMR1+1),a
        ld (PMR2),a
        ld (PMR2+1),a
        ld a,b
        or a
        ret z
        cp 97
        jr nc,.too_big
        push hl
        push bc
.check: ld a,(hl)
        cp $17
        jr z,.reserved
        inc hl
        djnz .check
        pop bc
        pop hl
        push hl
        push bc
        ld hl,cmd_write
        ld de,COMMAND_BUFFER
        call str_copy
        pop bc
        pop hl
.encode:ld a,(hl)
        inc hl
        call hex_byte
        djnz .encode
        xor a
        ld (de),a
        ld hl,COMMAND_BUFFER
        jp tpi_execute
.reserved:
        pop bc
        pop hl
        ld a,E_RESERVED_BYTE
        scf
        ret
.too_big:
        ld a,E_CAPACITY
        scf
        ret

hex_byte:                              ; A -> two uppercase hex chars at DE
        push af
        rrca
        rrca
        rrca
        rrca
        call .nibble
        pop af
.nibble:and 15
        add a,'0'
        cp '9'+1
        jr c,.store
        add a,7
.store: ld (de),a
        inc de
        ret

f_load:
        ld (FILE_PTR),de
        ld (FILE_LEFT),bc
        ld de,0
        ld (FILE_DONE),de
        ld de,mode_rb
        ld a,FILE_STREAM
        call f_open
        ret c
.loop:  ld bc,(FILE_LEFT)
        ld a,b
        or c
        jr z,.full
        ld a,b
        or a
        ld a,c
        jr z,.small
        ld a,255
.small: ld b,a
        ld hl,(FILE_PTR)
        ld a,FILE_STREAM
        call f_read
        jr c,f_cleanup_error
        ld a,b
        or c
        jr z,f_cleanup_ok
        ld hl,(FILE_PTR)
        add hl,bc
        ld (FILE_PTR),hl
        ld hl,(FILE_DONE)
        add hl,bc
        ld (FILE_DONE),hl
        ld hl,(FILE_LEFT)
        or a
        sbc hl,bc
        ld (FILE_LEFT),hl
        jr .loop
.full:  ld hl,RX_BUFFER                 ; probe EOF; never overwrite caller buffer
        ld b,1
        ld a,FILE_STREAM
        call f_read
        jr c,f_cleanup_error
        ld a,c
        or a
        jr z,f_cleanup_ok
        ld a,E_CAPACITY
        jr f_cleanup_error

f_cleanup_ok:
        ld a,FILE_STREAM
        jp f_close
f_cleanup_error:
        push af
        ld a,FILE_STREAM
        call f_close
        pop af
        scf
        ret

f_save:
        ld (FILE_PTR),de
        ld (FILE_LEFT),bc
        push hl
        ex de,hl
.preflight:
        ld a,b
        or c
        jr z,.checked
        ld a,(hl)
        cp $17
        jr z,.unsafe
        inc hl
        dec bc
        jr .preflight
.unsafe:pop hl
        ld a,E_RESERVED_BYTE
        scf
        ret
.checked:
        pop hl
        ld de,mode_wb
        ld a,FILE_STREAM
        call f_open
        ret c
.loop:  ld bc,(FILE_LEFT)
        ld a,b
        or c
        jr z,f_cleanup_ok
        ld a,b
        or a
        ld a,c
        jr nz,.max
        cp 97
        jr c,.small
.max:   ld a,96
.small: ld (FILE_WRITE_COUNT),a
        ld b,a
        ld a,FILE_STREAM
        ld hl,(FILE_PTR)
        call f_write
        jr c,f_cleanup_error
        ld a,(FILE_WRITE_COUNT)
        ld c,a
        ld b,0
        ld hl,(FILE_PTR)
        add hl,bc
        ld (FILE_PTR),hl
        ld hl,(FILE_LEFT)
        or a
        sbc hl,bc
        ld (FILE_LEFT),hl
        jr .loop

cmd_open: db 'tpi:chopen ',0
cmd_close: db 'tpi:chclose',0
cmd_read: db 'tpi:chrd',0
cmd_write: db 'tpi:chwr ',0
mode_rb: db 'rb',0
mode_wb: db 'wb',0
mode_r: db 'r',0
FILE_WRITE_COUNT equ WORK_BASE+37
