; TS2068 HOME-RAM gateway patterns.
; Assemble/copy these into a HOME chunk whose HSR bit remains zero.
; Adapt register preservation, entry addresses, and interrupt policy.

PORT_HSR        EQU     $F4
PORT_DECR       EQU     $FF

; Cartridge-side caller may select another data chunk without RAM code if it
; keeps the executing chunk selected. A=additional DOCK mask, code in chunk 4.
SELECT_DOCK_WITH_CODE4:
                OR      $10
                LD      (HSR_SHADOW),A
                LD      BC,$00F4
                OUT     (C),A
                RET

RESTORE_CODE4_ONLY:
                LD      A,$10
                LD      (HSR_SHADOW),A
                LD      BC,$00F4
                OUT     (C),A
                RET

; Call a verified EXROM routine from HOME RAM.
; This assumes EXROM is needed at external chunk 0. Keep all gateway code,
; variables, stack, and return path in HOME chunks that remain selected.
CALL_EXROM_FROM_HOME:
                PUSH    AF                  ; preserve caller AF separately
                LD      A,I
                LD      A,0
                JP      PO,EXROM_IFF_SAVED
                INC     A
EXROM_IFF_SAVED:
                LD      (IFF_SHADOW),A
                DI
                PUSH    BC
                PUSH    DE
                PUSH    HL

                XOR     A
                LD      BC,$00F4
                OUT     (C),A                ; expose HOME before DECR flip

                LD      A,(DECR_SHADOW)
                OR      $80                  ; choose EXROM, preserve video bits
                LD      BC,$00FF
                OUT     (C),A

                LD      A,$01                ; EXROM chunk 0
                LD      BC,$00F4
                OUT     (C),A
                CALL    EXROM_ENTRY

                XOR     A
                LD      BC,$00F4
                OUT     (C),A                ; no external chunk during bank flip
                LD      A,(DECR_SHADOW)
                AND     $7F                  ; restore DOCK selection
                LD      BC,$00FF
                OUT     (C),A
                LD      A,(HSR_SHADOW)
                LD      BC,$00F4
                OUT     (C),A

                POP     HL
                POP     DE
                POP     BC
                LD      A,(IFF_SHADOW)
                OR      A
                JR      Z,EXROM_RETURN_DI
                EI
EXROM_RETURN_DI:
                POP     AF
                RET

EXROM_ENTRY     EQU     $0000                ; replace with verified entry
HSR_SHADOW:     DB      $10
DECR_SHADOW:    DB      $00
IFF_SHADOW:     DB      $00
