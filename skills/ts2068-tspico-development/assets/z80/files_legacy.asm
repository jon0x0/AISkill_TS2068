; Legacy backend: TAP CODE blocks, not raw byte-file channels.
; f_load HL=current-folder filename or &nnn, DE=buffer, BC=capacity.
; f_save HL=1..10 uppercase letters/digits (no suffix), DE=buffer, BC=len.
; Firmware adds .tap. Existing append mode is explicitly disabled first.
; All payload bytes, including $17, are supported. No BASIC/ROM calls.
LEGACY_CAP equ WORK_BASE+49
LEGACY_SOURCE equ WORK_BASE+51
LEGACY_LENGTH equ WORK_BASE+53
LEGACY_DEST equ WORK_BASE+55
LEGACY_POST_ERROR equ WORK_BASE+57

; A=7: directory text, TAP CODE load, TAP CODE save. No raw-file channels.
legacy_capabilities:
        ld a,7
        or a
        ret

str_copy:
        ld a,(hl)
        ld (de),a
        inc hl
        inc de
        or a
        jr nz,str_copy
        dec de
        ret

legacy_mount:
        push hl
        ld hl,legacy_prefix
        ld de,COMMAND_BUFFER
        call str_copy
        pop hl
        ld b,80
.copy:  ld a,(hl)
        ld (de),a
        inc hl
        inc de
        or a
        jr z,.send
        djnz .copy
        ld a,E_PATH
        scf
        ret
.send:  ld hl,COMMAND_BUFFER
        ld a,1
        jp legacy_execute

legacy_directory:
        ld hl,legacy_dir_cmd
        ld a,1
        jp legacy_execute

; HL=folder name, / for root, .. for parent. Changes Pico's global cwd.
legacy_chdir:
        push hl
        ld hl,legacy_cd_cmd
        ld de,COMMAND_BUFFER
        call str_copy
        pop hl
        ld b,76
.copy:  ld a,(hl)
        ld (de),a
        inc hl
        inc de
        or a
        jr z,.send
        djnz .copy
        ld a,E_PATH
        scf
        ret
.send:  ld hl,COMMAND_BUFFER
        xor a
        jp legacy_execute

; A=expected TAP flag, DE=destination, BC=payload length.
; Caller must know length; TAP protocol does not send a length prefix.
legacy_read_block:
        ld (LEGACY_FLAG),a
        ld (FILE_PTR),de
        ld (FILE_LEFT),bc
        ld e,1
        call legacy_make_pre
        call legacy_preheader
        ret c
        ld a,5
        ld (LEGACY_PHASE),a
        ld a,(LEGACY_FLAG)              ; original LOAD_TS consumes flag echo
        ld d,0
        call tpi_tx
        call tpi_rx
        ld d,a
        ld a,(LEGACY_FLAG)
        cp d
        ld a,0
        jr z,.flag_ok
        ld a,E_SYNC
.flag_ok:
        ld (LEGACY_POST_ERROR),a
        ld hl,(FILE_PTR)
        ld bc,(FILE_LEFT)
        ld a,b
        or c
        jr z,.crc
.read:  call tpi_rx
        ld (hl),a
        inc hl
        xor d
        ld d,a
        dec bc
        ld a,b
        or c
        jr nz,.read
.crc:   call tpi_rx
        xor d
        ld (LEGACY_CRC),a
        ld d,0
        call tpi_tx                      ; XOR residual: zero is correct
        call legacy_wait_ready
        ret c
        xor a
        ld (LEGACY_TEXT),a
        call legacy_reply
        ret c
        ld a,(LEGACY_POST_ERROR)
        or a
        jr nz,.error
        ld a,(LEGACY_CRC)
        or a
        ret z
        ld a,E_CHECKSUM
.error: scf
        ret

f_load:
        ld (LEGACY_CAP),bc
        ld (LEGACY_DEST),de
        xor a
        ld (FILE_DONE),a
        ld (FILE_DONE+1),a
        call legacy_mount
        ret c
        xor a
        ld de,NAME_BUFFER
        ld bc,17
        call legacy_read_block
        ret c
        ld a,(NAME_BUFFER)
        cp 3                            ; only CODE files; no executing BASIC
        jr z,.code
        ld a,E_FUNCTION
        scf
        ret
.code:  ld hl,(NAME_BUFFER+11)
        ld (LEGACY_LENGTH),hl
        ld de,(LEGACY_CAP)
        or a
        sbc hl,de
        jr c,.fits
        jr z,.fits
        ld a,E_CAPACITY                 ; refuse before starting data block
        scf
        ret
.fits:  ld bc,(LEGACY_LENGTH)
        ld de,(LEGACY_DEST)
        ld a,$ff
        call legacy_read_block
        ret c
        ld hl,(LEGACY_LENGTH)
        ld (FILE_DONE),hl
        xor a
        ret

f_save:
        ld (LEGACY_SOURCE),de
        ld (LEGACY_LENGTH),bc
        xor a
        ld (FILE_DONE),a
        ld (FILE_DONE+1),a
        ; Validate the entire basename before touching the Pico.
        ld de,NAME_BUFFER+3
        ld b,10
.name:  ld a,(hl)
        or a
        jr z,.pad
        cp '0'
        jr c,.bad
        cp '9'+1
        jr c,.valid
        cp 'A'
        jr c,.bad
        cp 'Z'+1
        jr nc,.bad
.valid: ld (de),a
        inc de
        inc hl
        djnz .name
        ld a,(hl)
        or a
        jr nz,.bad
        jr .header
.pad:   ld a,b
        cp 10
        jr z,.bad
        ld a,' '
.padding:
        ld (de),a
        inc de
        djnz .padding
        jr .header
.bad:   ld a,E_PATH
        scf
        ret
.header:
        ; 21-byte SLVM header: flag, session, 17 header bytes, XOR.
        xor a
        ld (NAME_BUFFER),a
        ld (NAME_BUFFER+1),a
        ld (NAME_BUFFER+2),a
        ld a,3
        ; Shift name one place: type is at offset 3, name at 4.
        ld hl,NAME_BUFFER+12
        ld de,NAME_BUFFER+13
        ld bc,10
        lddr
        ld (NAME_BUFFER+3),a
        ld hl,(LEGACY_LENGTH)
        ld (NAME_BUFFER+14),hl
        ld hl,(LEGACY_SOURCE)
        ld (NAME_BUFFER+16),hl
        ld hl,$8000
        ld (NAME_BUFFER+18),hl
        ld hl,NAME_BUFFER
        ld b,20
        xor a
.header_xor:
        xor (hl)
        inc hl
        djnz .header_xor
        ld (hl),a
        ; CLOSE clears append mode, so saves never append to an old mount.
        ld hl,legacy_close_cmd
        xor a
        call legacy_execute
        ret c
        xor a
        ld e,a
        ld bc,17
        call legacy_make_pre
        call legacy_preheader
        ret c
        ld a,6
        ld (LEGACY_PHASE),a
        ld hl,NAME_BUFFER
        ld b,21
        ld d,0
.tx_header:
        ld a,(hl)
        inc hl
        call tpi_tx
        djnz .tx_header
        call legacy_wait_ready
        ret c
        call tpi_rx
        cp 1
        jr nz,.refused
        ld a,7
        ld (LEGACY_PHASE),a
        ld d,0
        ld a,$ff
        call tpi_tx
        xor a                           ; two session bytes excluded by firmware
        call tpi_tx                      ; zero makes both checksum rules agree
        xor a
        call tpi_tx
        ld bc,(LEGACY_LENGTH)
        ld hl,(LEGACY_SOURCE)
        ld a,b
        or c
        jr z,.tx_crc
.tx_data:
        ld a,(hl)
        inc hl
        call tpi_tx
        dec bc
        ld a,b
        or c
        jr nz,.tx_data
.tx_crc:
        ld a,d
        call tpi_tx
        call legacy_wait_ready
        ret c
        xor a
        ld (LEGACY_TEXT),a
        call legacy_reply
        ret c
        ld hl,(LEGACY_LENGTH)
        ld (FILE_DONE),hl
        xor a
        ret
.refused:
        scf
        ret

; Raw-file channels are deliberately unavailable on legacy firmware.
f_open:
f_close:
f_read:
f_write:
        ld a,E_FUNCTION
        scf
        ret
legacy_prefix: db 'tpi:',0
legacy_dir_cmd: db 'tpi:dir',0
legacy_cd_cmd: db 'tpi:cd ',0
legacy_close_cmd: db 'tpi:close',0
