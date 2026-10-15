	.build_version macos, 11, 0	sdk_version 27, 0
	.section	__TEXT,__literal16,16byte_literals
	.p2align	4, 0x0                          ; -- Begin function saxpy_ispc___uniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_
lCPI0_0:
	.long	4                               ; 0x4
	.long	5                               ; 0x5
	.long	6                               ; 0x6
	.long	7                               ; 0x7
lCPI0_1:
	.long	0                               ; 0x0
	.long	1                               ; 0x1
	.long	2                               ; 0x2
	.long	3                               ; 0x3
lCPI0_2:
	.long	16                              ; 0x10
	.long	32                              ; 0x20
	.long	64                              ; 0x40
	.long	128                             ; 0x80
lCPI0_3:
	.long	1                               ; 0x1
	.long	2                               ; 0x2
	.long	4                               ; 0x4
	.long	8                               ; 0x8
lCPI0_4:
	.short	1                               ; 0x1
	.short	2                               ; 0x2
	.short	4                               ; 0x4
	.short	8                               ; 0x8
	.short	16                              ; 0x10
	.short	32                              ; 0x20
	.short	64                              ; 0x40
	.short	128                             ; 0x80
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_saxpy_ispc___uniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_
	.p2align	2
_saxpy_ispc___uniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_: ; @saxpy_ispc___uniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_
; %bb.0:
                                        ; kill: def $s0 killed $s0 def $q0
	negs	w8, w0
	and	w8, w8, #0x7
	and	w9, w0, #0x7
	csneg	w8, w9, w8, mi
	sub	w9, w0, w8
	cmp	w9, #1
	b.lt	LBB0_5
; %bb.1:
	sub	sp, sp, #16
	mov	x8, #0                          ; =0x0
	mov	x10, x3
	mov	x11, x2
	mov	x12, x1
LBB0_2:                                 ; =>This Inner Loop Header: Depth=1
	ldp	q1, q2, [x12], #32
	ldp	q4, q3, [x11], #32
	fmla.4s	v4, v1, v0[0]
	fmla.4s	v3, v2, v0[0]
	add	x8, x8, #8
	stp	q4, q3, [x10], #32
	cmp	x8, x9
	b.lo	LBB0_2
; %bb.3:
	add	sp, sp, #16
	cmp	w8, w0
	b.lt	LBB0_6
LBB0_4:
	ret
LBB0_5:
	mov	w8, #0                          ; =0x0
	cmp	w8, w0
	b.ge	LBB0_4
LBB0_6:
	dup.4s	v1, w8
Lloh0:
	adrp	x9, lCPI0_0@PAGE
Lloh1:
	ldr	q2, [x9, lCPI0_0@PAGEOFF]
	orr.16b	v2, v1, v2
Lloh2:
	adrp	x9, lCPI0_1@PAGE
Lloh3:
	ldr	q3, [x9, lCPI0_1@PAGEOFF]
	orr.16b	v1, v1, v3
	dup.4s	v3, w0
	cmgt.4s	v1, v3, v1
	cmgt.4s	v2, v3, v2
	lsl	w8, w8, #2
	add	x11, x1, x8
Lloh4:
	adrp	x9, lCPI0_2@PAGE
Lloh5:
	ldr	q3, [x9, lCPI0_2@PAGEOFF]
	and.16b	v3, v2, v3
Lloh6:
	adrp	x9, lCPI0_3@PAGE
Lloh7:
	ldr	q4, [x9, lCPI0_3@PAGEOFF]
	and.16b	v4, v1, v4
	orr.16b	v3, v4, v3
	addv.4s	s3, v3
	fmov	w9, s3
	and	w12, w9, w9, lsr #7
	add	x10, x2, x8
	adrp	x9, lCPI0_4@PAGE
	tbz	w12, #0, LBB0_8
; %bb.7:
	ldp	q3, q4, [x11]
	ldp	q5, q6, [x10]
	b	LBB0_39
LBB0_8:
	uzp1.8h	v3, v1, v2
	ldr	q4, [x9, lCPI0_4@PAGEOFF]
	and.16b	v3, v3, v4
	addv.8h	h5, v3
	fmov	w13, s5
	and	w12, w13, #0xff
	tbz	w13, #0, LBB0_10
; %bb.9:
	ldr	s3, [x11]
	tbnz	w12, #1, LBB0_11
	b	LBB0_12
LBB0_10:
                                        ; implicit-def: $q3
	tbz	w12, #1, LBB0_12
LBB0_11:
	add	x13, x11, #4
	ld1.s	{ v3 }[1], [x13]
LBB0_12:
	tbnz	w12, #2, LBB0_16
; %bb.13:
	tbnz	w12, #3, LBB0_17
LBB0_14:
	tbz	w12, #4, LBB0_18
LBB0_15:
	add	x13, x11, #16
	ld1.s	{ v4 }[0], [x13]
	tbnz	w12, #5, LBB0_19
	b	LBB0_20
LBB0_16:
	add	x13, x11, #8
	ld1.s	{ v3 }[2], [x13]
	tbz	w12, #3, LBB0_14
LBB0_17:
	add	x13, x11, #12
	ld1.s	{ v3 }[3], [x13]
	tbnz	w12, #4, LBB0_15
LBB0_18:
                                        ; implicit-def: $q4
	tbz	w12, #5, LBB0_20
LBB0_19:
	add	x13, x11, #20
	ld1.s	{ v4 }[1], [x13]
LBB0_20:
	tbnz	w12, #6, LBB0_24
; %bb.21:
	tbnz	w12, #7, LBB0_25
LBB0_22:
	fmov	w12, s5
	and	w11, w12, #0xff
	tbz	w12, #0, LBB0_26
LBB0_23:
	ldr	s5, [x10]
	tbnz	w11, #1, LBB0_27
	b	LBB0_28
LBB0_24:
	add	x13, x11, #24
	ld1.s	{ v4 }[2], [x13]
	tbz	w12, #7, LBB0_22
LBB0_25:
	add	x11, x11, #28
	ld1.s	{ v4 }[3], [x11]
	fmov	w12, s5
	and	w11, w12, #0xff
	tbnz	w12, #0, LBB0_23
LBB0_26:
                                        ; implicit-def: $q5
	tbz	w11, #1, LBB0_28
LBB0_27:
	add	x12, x10, #4
	ld1.s	{ v5 }[1], [x12]
LBB0_28:
	tbnz	w11, #2, LBB0_32
; %bb.29:
	tbnz	w11, #3, LBB0_33
LBB0_30:
	tbz	w11, #4, LBB0_34
LBB0_31:
	add	x12, x10, #16
	ld1.s	{ v6 }[0], [x12]
	tbnz	w11, #5, LBB0_35
	b	LBB0_36
LBB0_32:
	add	x12, x10, #8
	ld1.s	{ v5 }[2], [x12]
	tbz	w11, #3, LBB0_30
LBB0_33:
	add	x12, x10, #12
	ld1.s	{ v5 }[3], [x12]
	tbnz	w11, #4, LBB0_31
LBB0_34:
                                        ; implicit-def: $q6
	tbz	w11, #5, LBB0_36
LBB0_35:
	add	x12, x10, #20
	ld1.s	{ v6 }[1], [x12]
LBB0_36:
	tbnz	w11, #6, LBB0_55
; %bb.37:
	tbz	w11, #7, LBB0_39
LBB0_38:
	add	x10, x10, #28
	ld1.s	{ v6 }[3], [x10]
LBB0_39:
	uzp1.8h	v1, v1, v2
	ldr	q2, [x9, lCPI0_4@PAGEOFF]
	and.16b	v1, v1, v2
	addv.8h	h1, v1
	fmov	w10, s1
	and	w9, w10, #0xff
	fmla.4s	v5, v3, v0[0]
	add	x8, x3, x8
	tbnz	w10, #0, LBB0_47
; %bb.40:
	tbnz	w9, #1, LBB0_48
LBB0_41:
	tbnz	w9, #2, LBB0_49
LBB0_42:
	tbnz	w9, #3, LBB0_50
LBB0_43:
	fmla.4s	v6, v4, v0[0]
	tbnz	w9, #4, LBB0_51
LBB0_44:
	tbnz	w9, #5, LBB0_52
LBB0_45:
	tbnz	w9, #6, LBB0_53
LBB0_46:
	tbz	w9, #7, LBB0_4
	b	LBB0_54
LBB0_47:
	str	s5, [x8]
	tbz	w9, #1, LBB0_41
LBB0_48:
	add	x10, x8, #4
	st1.s	{ v5 }[1], [x10]
	tbz	w9, #2, LBB0_42
LBB0_49:
	add	x10, x8, #8
	st1.s	{ v5 }[2], [x10]
	tbz	w9, #3, LBB0_43
LBB0_50:
	add	x10, x8, #12
	st1.s	{ v5 }[3], [x10]
	fmla.4s	v6, v4, v0[0]
	tbz	w9, #4, LBB0_44
LBB0_51:
	str	s6, [x8, #16]
	tbz	w9, #5, LBB0_45
LBB0_52:
	add	x10, x8, #20
	st1.s	{ v6 }[1], [x10]
	tbz	w9, #6, LBB0_46
LBB0_53:
	add	x10, x8, #24
	st1.s	{ v6 }[2], [x10]
	tbz	w9, #7, LBB0_4
LBB0_54:
	add	x8, x8, #28
	st1.s	{ v6 }[3], [x8]
	ret
LBB0_55:
	add	x12, x10, #24
	ld1.s	{ v6 }[2], [x12]
	tbnz	w11, #7, LBB0_38
	b	LBB0_39
	.loh AdrpLdr	Lloh6, Lloh7
	.loh AdrpAdrp	Lloh4, Lloh6
	.loh AdrpLdr	Lloh4, Lloh5
	.loh AdrpAdrp	Lloh2, Lloh4
	.loh AdrpLdr	Lloh2, Lloh3
	.loh AdrpAdrp	Lloh0, Lloh2
	.loh AdrpLdr	Lloh0, Lloh1
                                        ; -- End function
	.section	__TEXT,__literal16,16byte_literals
	.p2align	4, 0x0                          ; -- Begin function saxpy_ispc_task___uniuniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_
lCPI1_0:
	.long	4                               ; 0x4
	.long	5                               ; 0x5
	.long	6                               ; 0x6
	.long	7                               ; 0x7
lCPI1_1:
	.long	0                               ; 0x0
	.long	1                               ; 0x1
	.long	2                               ; 0x2
	.long	3                               ; 0x3
lCPI1_2:
	.long	16                              ; 0x10
	.long	32                              ; 0x20
	.long	64                              ; 0x40
	.long	128                             ; 0x80
lCPI1_3:
	.long	1                               ; 0x1
	.long	2                               ; 0x2
	.long	4                               ; 0x4
	.long	8                               ; 0x8
lCPI1_4:
	.short	1                               ; 0x1
	.short	2                               ; 0x2
	.short	4                               ; 0x4
	.short	8                               ; 0x8
	.short	16                              ; 0x10
	.short	32                              ; 0x20
	.short	64                              ; 0x40
	.short	128                             ; 0x80
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_saxpy_ispc_task___uniuniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_
	.p2align	6
_saxpy_ispc_task___uniuniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_: ; @saxpy_ispc_task___uniuniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_
; %bb.0:
	sub	sp, sp, #16
	add	x8, x0, #8
	ldr	d0, [x0]
	mov.s	w9, v0[1]
	fmov	w12, s0
	ld1.s	{ v0 }[2], [x8]
	ldp	x11, x10, [x0, #16]
	ldr	x8, [x0, #32]
	mul	w14, w9, w3
	add	w9, w14, w9
	.p2align	6, , 4
; %bb.1:
	cmp	w12, w9
	csel	w9, w12, w9, lt
	sub	w12, w9, w14
	negs	w13, w12
	and	w12, w12, #0x7
	and	w13, w13, #0x7
	csneg	w12, w12, w13, mi
	sub	w13, w9, w12
	cmp	w14, w13
	b.ge	LBB1_5
; %bb.2:
	sxtw	x12, w14
	sxtw	x13, w13
	sbfiz	x16, x14, #2, #32
	add	x14, x11, x16
	add	x15, x10, x16
	add	x16, x8, x16
LBB1_3:                                 ; =>This Inner Loop Header: Depth=1
	ldp	q1, q2, [x14], #32
	ldp	q4, q3, [x15], #32
	fmla.4s	v4, v1, v0[2]
	fmla.4s	v3, v2, v0[2]
	add	x12, x12, #8
	stp	q4, q3, [x16], #32
	cmp	x12, x13
	b.lt	LBB1_3
; %bb.4:
	mov	x14, x12
LBB1_5:
	cmp	w14, w9
	b.ge	LBB1_48
; %bb.6:
	dup.4s	v1, w14
Lloh8:
	adrp	x12, lCPI1_0@PAGE
Lloh9:
	ldr	q2, [x12, lCPI1_0@PAGEOFF]
	add.4s	v2, v1, v2
Lloh10:
	adrp	x12, lCPI1_1@PAGE
Lloh11:
	ldr	q3, [x12, lCPI1_1@PAGEOFF]
	dup.4s	v4, w9
	add.4s	v1, v1, v3
	cmgt.4s	v1, v4, v1
	cmgt.4s	v2, v4, v2
	lsl	w9, w14, #2
	sxtw	x9, w9
	add	x12, x11, x9
Lloh12:
	adrp	x11, lCPI1_2@PAGE
Lloh13:
	ldr	q3, [x11, lCPI1_2@PAGEOFF]
	and.16b	v3, v2, v3
Lloh14:
	adrp	x11, lCPI1_3@PAGE
Lloh15:
	ldr	q4, [x11, lCPI1_3@PAGEOFF]
	and.16b	v4, v1, v4
	orr.16b	v3, v4, v3
	addv.4s	s3, v3
	fmov	w11, s3
	and	w13, w11, w11, lsr #7
	add	x11, x10, x9
	adrp	x10, lCPI1_4@PAGE
	tbz	w13, #0, LBB1_8
; %bb.7:
	ldp	q3, q4, [x12]
	ldp	q5, q6, [x11]
	b	LBB1_39
LBB1_8:
	uzp1.8h	v3, v1, v2
	ldr	q4, [x10, lCPI1_4@PAGEOFF]
	and.16b	v3, v3, v4
	addv.8h	h5, v3
	fmov	w14, s5
	and	w13, w14, #0xff
	tbz	w14, #0, LBB1_10
; %bb.9:
	ldr	s3, [x12]
	tbnz	w13, #1, LBB1_11
	b	LBB1_12
LBB1_10:
                                        ; implicit-def: $q3
	tbz	w13, #1, LBB1_12
LBB1_11:
	add	x14, x12, #4
	ld1.s	{ v3 }[1], [x14]
LBB1_12:
	tbnz	w13, #2, LBB1_16
; %bb.13:
	tbnz	w13, #3, LBB1_17
LBB1_14:
	tbz	w13, #4, LBB1_18
LBB1_15:
	add	x14, x12, #16
	ld1.s	{ v4 }[0], [x14]
	tbnz	w13, #5, LBB1_19
	b	LBB1_20
LBB1_16:
	add	x14, x12, #8
	ld1.s	{ v3 }[2], [x14]
	tbz	w13, #3, LBB1_14
LBB1_17:
	add	x14, x12, #12
	ld1.s	{ v3 }[3], [x14]
	tbnz	w13, #4, LBB1_15
LBB1_18:
                                        ; implicit-def: $q4
	tbz	w13, #5, LBB1_20
LBB1_19:
	add	x14, x12, #20
	ld1.s	{ v4 }[1], [x14]
LBB1_20:
	tbnz	w13, #6, LBB1_24
; %bb.21:
	tbnz	w13, #7, LBB1_25
LBB1_22:
	fmov	w13, s5
	and	w12, w13, #0xff
	tbz	w13, #0, LBB1_26
LBB1_23:
	ldr	s5, [x11]
	tbnz	w12, #1, LBB1_27
	b	LBB1_28
LBB1_24:
	add	x14, x12, #24
	ld1.s	{ v4 }[2], [x14]
	tbz	w13, #7, LBB1_22
LBB1_25:
	add	x12, x12, #28
	ld1.s	{ v4 }[3], [x12]
	fmov	w13, s5
	and	w12, w13, #0xff
	tbnz	w13, #0, LBB1_23
LBB1_26:
                                        ; implicit-def: $q5
	tbz	w12, #1, LBB1_28
LBB1_27:
	add	x13, x11, #4
	ld1.s	{ v5 }[1], [x13]
LBB1_28:
	tbnz	w12, #2, LBB1_32
; %bb.29:
	tbnz	w12, #3, LBB1_33
LBB1_30:
	tbz	w12, #4, LBB1_34
LBB1_31:
	add	x13, x11, #16
	ld1.s	{ v6 }[0], [x13]
	tbnz	w12, #5, LBB1_35
	b	LBB1_36
LBB1_32:
	add	x13, x11, #8
	ld1.s	{ v5 }[2], [x13]
	tbz	w12, #3, LBB1_30
LBB1_33:
	add	x13, x11, #12
	ld1.s	{ v5 }[3], [x13]
	tbnz	w12, #4, LBB1_31
LBB1_34:
                                        ; implicit-def: $q6
	tbz	w12, #5, LBB1_36
LBB1_35:
	add	x13, x11, #20
	ld1.s	{ v6 }[1], [x13]
LBB1_36:
	tbnz	w12, #6, LBB1_56
; %bb.37:
	tbz	w12, #7, LBB1_39
LBB1_38:
	add	x11, x11, #28
	ld1.s	{ v6 }[3], [x11]
LBB1_39:
	uzp1.8h	v1, v1, v2
	ldr	q2, [x10, lCPI1_4@PAGEOFF]
	and.16b	v1, v1, v2
	addv.8h	h1, v1
	fmov	w11, s1
	and	w10, w11, #0xff
	fmla.4s	v5, v3, v0[2]
	add	x8, x8, x9
	tbnz	w11, #0, LBB1_49
; %bb.40:
	tbnz	w10, #1, LBB1_50
LBB1_41:
	tbnz	w10, #2, LBB1_51
LBB1_42:
	tbnz	w10, #3, LBB1_52
LBB1_43:
	fmla.4s	v6, v4, v0[2]
	tbnz	w10, #4, LBB1_53
LBB1_44:
	tbnz	w10, #5, LBB1_54
LBB1_45:
	tbnz	w10, #6, LBB1_55
LBB1_46:
	tbz	w10, #7, LBB1_48
LBB1_47:
	add	x8, x8, #28
	st1.s	{ v6 }[3], [x8]
LBB1_48:
	add	sp, sp, #16
	ret
LBB1_49:
	str	s5, [x8]
	tbz	w10, #1, LBB1_41
LBB1_50:
	add	x9, x8, #4
	st1.s	{ v5 }[1], [x9]
	tbz	w10, #2, LBB1_42
LBB1_51:
	add	x9, x8, #8
	st1.s	{ v5 }[2], [x9]
	tbz	w10, #3, LBB1_43
LBB1_52:
	add	x9, x8, #12
	st1.s	{ v5 }[3], [x9]
	fmla.4s	v6, v4, v0[2]
	tbz	w10, #4, LBB1_44
LBB1_53:
	str	s6, [x8, #16]
	tbz	w10, #5, LBB1_45
LBB1_54:
	add	x9, x8, #20
	st1.s	{ v6 }[1], [x9]
	tbz	w10, #6, LBB1_46
LBB1_55:
	add	x9, x8, #24
	st1.s	{ v6 }[2], [x9]
	tbnz	w10, #7, LBB1_47
	b	LBB1_48
LBB1_56:
	add	x13, x11, #24
	ld1.s	{ v6 }[2], [x13]
	tbnz	w12, #7, LBB1_38
	b	LBB1_39
	.loh AdrpLdr	Lloh14, Lloh15
	.loh AdrpAdrp	Lloh12, Lloh14
	.loh AdrpLdr	Lloh12, Lloh13
	.loh AdrpLdr	Lloh10, Lloh11
	.loh AdrpAdrp	Lloh8, Lloh10
	.loh AdrpLdr	Lloh8, Lloh9
                                        ; -- End function
	.globl	_saxpy_ispc_withtasks___uniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_ ; -- Begin function saxpy_ispc_withtasks___uniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_
	.p2align	6
_saxpy_ispc_withtasks___uniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_: ; @saxpy_ispc_withtasks___uniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_
; %bb.0:
	sub	sp, sp, #144
	stp	d9, d8, [sp, #80]               ; 16-byte Folded Spill
	stp	x22, x21, [sp, #96]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #112]            ; 16-byte Folded Spill
	stp	x29, x30, [sp, #128]            ; 16-byte Folded Spill
	stp	q2, q1, [sp, #32]               ; 32-byte Folded Spill
	mov	x19, x3
	mov	x20, x2
	mov.16b	v8, v0
	fmov	d0, x1
	str	q0, [sp, #16]                   ; 16-byte Spill
	add	w8, w0, #63
	.p2align	6, , 4
; %bb.1:
	cmp	w0, #0
	csel	w8, w8, w0, mi
	asr	w22, w8, #6
	sdiv	w21, w0, w22
	fmov	s0, w0
	str	q0, [sp]                        ; 16-byte Spill
	str	xzr, [sp, #72]
	add	x0, sp, #72
	mov	w1, #96                         ; =0x60
	mov	w2, #16                         ; =0x10
	bl	_ISPCAlloc
	mov	x2, x0
	ldr	q0, [sp]                        ; 16-byte Reload
	mov.s	v0[1], w22
	str	s8, [x0, #8]
	str	d0, [x0]
	ldr	q0, [sp, #16]                   ; 16-byte Reload
	mov.d	v0[1], x20
	str	q0, [x0, #16]
	str	x19, [x0, #32]
	ldp	q3, q0, [sp, #32]               ; 32-byte Folded Reload
	stp	q0, q3, [x0, #64]
Lloh16:
	adrp	x1, _saxpy_ispc_task___uniuniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_@PAGE
Lloh17:
	add	x1, x1, _saxpy_ispc_task___uniuniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_@PAGEOFF
	add	x0, sp, #72
	mov	x3, x21
	mov	w4, #1                          ; =0x1
	mov	w5, #1                          ; =0x1
	bl	_ISPCLaunch
	ldr	x0, [sp, #72]
	cbz	x0, LBB2_3
; %bb.2:
	bl	_ISPCSync
LBB2_3:
	ldp	x29, x30, [sp, #128]            ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #112]            ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #96]             ; 16-byte Folded Reload
	ldp	d9, d8, [sp, #80]               ; 16-byte Folded Reload
	add	sp, sp, #144
	ret
	.loh AdrpAdd	Lloh16, Lloh17
                                        ; -- End function
	.section	__TEXT,__literal16,16byte_literals
	.p2align	4, 0x0                          ; -- Begin function saxpy_ispc
lCPI3_0:
	.long	4                               ; 0x4
	.long	5                               ; 0x5
	.long	6                               ; 0x6
	.long	7                               ; 0x7
lCPI3_1:
	.long	0                               ; 0x0
	.long	1                               ; 0x1
	.long	2                               ; 0x2
	.long	3                               ; 0x3
lCPI3_2:
	.long	16                              ; 0x10
	.long	32                              ; 0x20
	.long	64                              ; 0x40
	.long	128                             ; 0x80
lCPI3_3:
	.long	1                               ; 0x1
	.long	2                               ; 0x2
	.long	4                               ; 0x4
	.long	8                               ; 0x8
lCPI3_4:
	.short	1                               ; 0x1
	.short	2                               ; 0x2
	.short	4                               ; 0x4
	.short	8                               ; 0x8
	.short	16                              ; 0x10
	.short	32                              ; 0x20
	.short	64                              ; 0x40
	.short	128                             ; 0x80
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_saxpy_ispc
	.p2align	2
_saxpy_ispc:                            ; @saxpy_ispc
; %bb.0:
                                        ; kill: def $s0 killed $s0 def $q0
	negs	w8, w0
	and	w8, w8, #0x7
	and	w9, w0, #0x7
	csneg	w8, w9, w8, mi
	sub	w9, w0, w8
	cmp	w9, #1
	b.lt	LBB3_5
; %bb.1:
	sub	sp, sp, #16
	mov	x8, #0                          ; =0x0
	mov	x10, x3
	mov	x11, x2
	mov	x12, x1
LBB3_2:                                 ; =>This Inner Loop Header: Depth=1
	ldp	q1, q2, [x12], #32
	ldp	q4, q3, [x11], #32
	fmla.4s	v4, v1, v0[0]
	fmla.4s	v3, v2, v0[0]
	add	x8, x8, #8
	stp	q4, q3, [x10], #32
	cmp	x8, x9
	b.lo	LBB3_2
; %bb.3:
	add	sp, sp, #16
	cmp	w8, w0
	b.lt	LBB3_6
LBB3_4:
	ret
LBB3_5:
	mov	w8, #0                          ; =0x0
	cmp	w8, w0
	b.ge	LBB3_4
LBB3_6:
	dup.4s	v1, w8
Lloh18:
	adrp	x9, lCPI3_0@PAGE
Lloh19:
	ldr	q2, [x9, lCPI3_0@PAGEOFF]
	orr.16b	v2, v1, v2
Lloh20:
	adrp	x9, lCPI3_1@PAGE
Lloh21:
	ldr	q3, [x9, lCPI3_1@PAGEOFF]
	orr.16b	v1, v1, v3
	dup.4s	v3, w0
	cmgt.4s	v1, v3, v1
	cmgt.4s	v2, v3, v2
	lsl	w8, w8, #2
	add	x11, x1, x8
Lloh22:
	adrp	x9, lCPI3_2@PAGE
Lloh23:
	ldr	q3, [x9, lCPI3_2@PAGEOFF]
	and.16b	v3, v2, v3
Lloh24:
	adrp	x9, lCPI3_3@PAGE
Lloh25:
	ldr	q4, [x9, lCPI3_3@PAGEOFF]
	and.16b	v4, v1, v4
	orr.16b	v3, v4, v3
	addv.4s	s3, v3
	fmov	w9, s3
	and	w12, w9, w9, lsr #7
	add	x10, x2, x8
	adrp	x9, lCPI3_4@PAGE
	tbz	w12, #0, LBB3_8
; %bb.7:
	ldp	q3, q4, [x11]
	ldp	q5, q6, [x10]
	b	LBB3_39
LBB3_8:
	uzp1.8h	v3, v1, v2
	ldr	q4, [x9, lCPI3_4@PAGEOFF]
	and.16b	v3, v3, v4
	addv.8h	h5, v3
	fmov	w13, s5
	and	w12, w13, #0xff
	tbz	w13, #0, LBB3_10
; %bb.9:
	ldr	s3, [x11]
	tbnz	w12, #1, LBB3_11
	b	LBB3_12
LBB3_10:
                                        ; implicit-def: $q3
	tbz	w12, #1, LBB3_12
LBB3_11:
	add	x13, x11, #4
	ld1.s	{ v3 }[1], [x13]
LBB3_12:
	tbnz	w12, #2, LBB3_16
; %bb.13:
	tbnz	w12, #3, LBB3_17
LBB3_14:
	tbz	w12, #4, LBB3_18
LBB3_15:
	add	x13, x11, #16
	ld1.s	{ v4 }[0], [x13]
	tbnz	w12, #5, LBB3_19
	b	LBB3_20
LBB3_16:
	add	x13, x11, #8
	ld1.s	{ v3 }[2], [x13]
	tbz	w12, #3, LBB3_14
LBB3_17:
	add	x13, x11, #12
	ld1.s	{ v3 }[3], [x13]
	tbnz	w12, #4, LBB3_15
LBB3_18:
                                        ; implicit-def: $q4
	tbz	w12, #5, LBB3_20
LBB3_19:
	add	x13, x11, #20
	ld1.s	{ v4 }[1], [x13]
LBB3_20:
	tbnz	w12, #6, LBB3_24
; %bb.21:
	tbnz	w12, #7, LBB3_25
LBB3_22:
	fmov	w12, s5
	and	w11, w12, #0xff
	tbz	w12, #0, LBB3_26
LBB3_23:
	ldr	s5, [x10]
	tbnz	w11, #1, LBB3_27
	b	LBB3_28
LBB3_24:
	add	x13, x11, #24
	ld1.s	{ v4 }[2], [x13]
	tbz	w12, #7, LBB3_22
LBB3_25:
	add	x11, x11, #28
	ld1.s	{ v4 }[3], [x11]
	fmov	w12, s5
	and	w11, w12, #0xff
	tbnz	w12, #0, LBB3_23
LBB3_26:
                                        ; implicit-def: $q5
	tbz	w11, #1, LBB3_28
LBB3_27:
	add	x12, x10, #4
	ld1.s	{ v5 }[1], [x12]
LBB3_28:
	tbnz	w11, #2, LBB3_32
; %bb.29:
	tbnz	w11, #3, LBB3_33
LBB3_30:
	tbz	w11, #4, LBB3_34
LBB3_31:
	add	x12, x10, #16
	ld1.s	{ v6 }[0], [x12]
	tbnz	w11, #5, LBB3_35
	b	LBB3_36
LBB3_32:
	add	x12, x10, #8
	ld1.s	{ v5 }[2], [x12]
	tbz	w11, #3, LBB3_30
LBB3_33:
	add	x12, x10, #12
	ld1.s	{ v5 }[3], [x12]
	tbnz	w11, #4, LBB3_31
LBB3_34:
                                        ; implicit-def: $q6
	tbz	w11, #5, LBB3_36
LBB3_35:
	add	x12, x10, #20
	ld1.s	{ v6 }[1], [x12]
LBB3_36:
	tbnz	w11, #6, LBB3_55
; %bb.37:
	tbz	w11, #7, LBB3_39
LBB3_38:
	add	x10, x10, #28
	ld1.s	{ v6 }[3], [x10]
LBB3_39:
	uzp1.8h	v1, v1, v2
	ldr	q2, [x9, lCPI3_4@PAGEOFF]
	and.16b	v1, v1, v2
	addv.8h	h1, v1
	fmov	w10, s1
	and	w9, w10, #0xff
	fmla.4s	v5, v3, v0[0]
	add	x8, x3, x8
	tbnz	w10, #0, LBB3_47
; %bb.40:
	tbnz	w9, #1, LBB3_48
LBB3_41:
	tbnz	w9, #2, LBB3_49
LBB3_42:
	tbnz	w9, #3, LBB3_50
LBB3_43:
	fmla.4s	v6, v4, v0[0]
	tbnz	w9, #4, LBB3_51
LBB3_44:
	tbnz	w9, #5, LBB3_52
LBB3_45:
	tbnz	w9, #6, LBB3_53
LBB3_46:
	tbz	w9, #7, LBB3_4
	b	LBB3_54
LBB3_47:
	str	s5, [x8]
	tbz	w9, #1, LBB3_41
LBB3_48:
	add	x10, x8, #4
	st1.s	{ v5 }[1], [x10]
	tbz	w9, #2, LBB3_42
LBB3_49:
	add	x10, x8, #8
	st1.s	{ v5 }[2], [x10]
	tbz	w9, #3, LBB3_43
LBB3_50:
	add	x10, x8, #12
	st1.s	{ v5 }[3], [x10]
	fmla.4s	v6, v4, v0[0]
	tbz	w9, #4, LBB3_44
LBB3_51:
	str	s6, [x8, #16]
	tbz	w9, #5, LBB3_45
LBB3_52:
	add	x10, x8, #20
	st1.s	{ v6 }[1], [x10]
	tbz	w9, #6, LBB3_46
LBB3_53:
	add	x10, x8, #24
	st1.s	{ v6 }[2], [x10]
	tbz	w9, #7, LBB3_4
LBB3_54:
	add	x8, x8, #28
	st1.s	{ v6 }[3], [x8]
	ret
LBB3_55:
	add	x12, x10, #24
	ld1.s	{ v6 }[2], [x12]
	tbnz	w11, #7, LBB3_38
	b	LBB3_39
	.loh AdrpLdr	Lloh24, Lloh25
	.loh AdrpAdrp	Lloh22, Lloh24
	.loh AdrpLdr	Lloh22, Lloh23
	.loh AdrpAdrp	Lloh20, Lloh22
	.loh AdrpLdr	Lloh20, Lloh21
	.loh AdrpAdrp	Lloh18, Lloh20
	.loh AdrpLdr	Lloh18, Lloh19
                                        ; -- End function
	.globl	_saxpy_ispc_withtasks           ; -- Begin function saxpy_ispc_withtasks
	.p2align	6
_saxpy_ispc_withtasks:                  ; @saxpy_ispc_withtasks
; %bb.0:
	sub	sp, sp, #112
	stp	d9, d8, [sp, #48]               ; 16-byte Folded Spill
	stp	x22, x21, [sp, #64]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #80]             ; 16-byte Folded Spill
	stp	x29, x30, [sp, #96]             ; 16-byte Folded Spill
	mov	x19, x3
	mov	x20, x2
	mov.16b	v8, v0
	fmov	d0, x1
	str	q0, [sp, #16]                   ; 16-byte Spill
	add	w8, w0, #63
	.p2align	6, , 4
; %bb.1:
	cmp	w0, #0
	csel	w8, w8, w0, mi
	asr	w22, w8, #6
	sdiv	w21, w0, w22
	fmov	s0, w0
	str	q0, [sp]                        ; 16-byte Spill
	str	xzr, [sp, #40]
	add	x0, sp, #40
	mov	w1, #96                         ; =0x60
	mov	w2, #16                         ; =0x10
	bl	_ISPCAlloc
	mov	x2, x0
	ldp	q1, q0, [sp]                    ; 32-byte Folded Reload
	mov.s	v1[1], w22
	str	s8, [x0, #8]
	mov.d	v0[1], x20
	str	d1, [x0]
	str	q0, [x0, #16]
	str	x19, [x0, #32]
	movi.2d	v0, #0xffffffffffffffff
	stp	q0, q0, [x0, #64]
Lloh26:
	adrp	x1, _saxpy_ispc_task___uniuniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_@PAGE
Lloh27:
	add	x1, x1, _saxpy_ispc_task___uniuniunfun_3C_unf_3E_un_3C_unf_3E_un_3C_unf_3E_@PAGEOFF
	add	x0, sp, #40
	mov	x3, x21
	mov	w4, #1                          ; =0x1
	mov	w5, #1                          ; =0x1
	bl	_ISPCLaunch
	ldr	x0, [sp, #40]
	cbz	x0, LBB4_3
; %bb.2:
	bl	_ISPCSync
LBB4_3:
	ldp	x29, x30, [sp, #96]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #80]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #64]             ; 16-byte Folded Reload
	ldp	d9, d8, [sp, #48]               ; 16-byte Folded Reload
	add	sp, sp, #112
	ret
	.loh AdrpAdd	Lloh26, Lloh27
                                        ; -- End function
.subsections_via_symbols
