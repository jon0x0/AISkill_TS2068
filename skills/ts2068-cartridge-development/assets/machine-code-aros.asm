; Minimal TS2068 machine-code AROS (Pasmo-compatible example)
; Copy this file into a project and adapt the memory map deliberately.

                ORG     $8000

; language=machine code, type=AROS, entry=$8008, only chunk 4 declared,
; autostart=yes, no ROM-managed variable reserve.
                DB      $02,$02,$08,$80,$EF,$01,$00,$00

PORT_HSR        EQU     $F4
CODE_MASK       EQU     $10

START:          DI
                LD      SP,$7FFF             ; HOME chunk 3; keep HSR bit 3 clear
                LD      A,CODE_MASK
                LD      BC,$00F4
                OUT     (C),A                ; code chunk 4; all others HOME

                ; Initialize application RAM and interrupt policy here.

MAIN_LOOP:      JP      MAIN_LOOP

; Example: copy ROM data chunk 5 ($A000) to HOME chunk 6 ($C000).
; PC remains in chunk 4, source chunk 5 is DOCK, destination chunk 6 HOME.
COPY_CHUNK5_TO_HOME6:
                DI
                LD      A,$30                ; chunks 4+5 from DOCK
                LD      BC,$00F4
                OUT     (C),A
                LD      HL,$A000
                LD      DE,$C000
                LD      BC,$2000
                LDIR
                LD      A,CODE_MASK
                LD      BC,$00F4
                OUT     (C),A
                RET

                DEFS    $A000-$,$FF
