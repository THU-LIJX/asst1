	.section	__TEXT,__text,regular,pure_instructions
	.build_version macos, 15, 1	sdk_version 15, 1
	.globl	__Z11saxpySerialifPfS_S_        ; -- Begin function _Z11saxpySerialifPfS_S_
	.p2align	2
__Z11saxpySerialifPfS_S_:               ; @_Z11saxpySerialifPfS_S_
	.cfi_startproc
; %bb.0:
                                        ; kill: def $s0 killed $s0 def $q0
	cmp	w0, #1
	b.lt	LBB0_10
; %bb.1:
	mov	w8, w0
	cmp	w0, #16
	b.hs	LBB0_3
; %bb.2:
	mov	x9, #0                          ; =0x0
	b	LBB0_8
LBB0_3:
	mov	x9, #0                          ; =0x0
	sub	x10, x3, x1
	cmp	x10, #64
	b.lo	LBB0_8
; %bb.4:
	sub	x10, x3, x2
	cmp	x10, #64
	b.lo	LBB0_8
; %bb.5:
	and	x9, x8, #0xfffffff0
	dup.4s	v1, v0[0]
	add	x10, x3, #32
	add	x11, x1, #32
	add	x12, x2, #32
	mov	x13, x9
LBB0_6:                                 ; =>This Inner Loop Header: Depth=1
	ldp	q2, q3, [x11, #-32]
	ldp	q4, q5, [x11], #64
	ldp	q6, q7, [x12, #-32]
	ldp	q16, q17, [x12], #64
	fmla.4s	v6, v2, v1
	fmla.4s	v7, v3, v1
	fmla.4s	v16, v4, v1
	fmla.4s	v17, v5, v1
	stp	q6, q7, [x10, #-32]
	stp	q16, q17, [x10], #64
	subs	x13, x13, #16
	b.ne	LBB0_6
; %bb.7:
	cmp	x9, x8
	b.eq	LBB0_10
LBB0_8:
	lsl	x12, x9, #2
	add	x10, x3, x12
	add	x11, x2, x12
	add	x12, x1, x12
	sub	x8, x8, x9
LBB0_9:                                 ; =>This Inner Loop Header: Depth=1
	ldr	s1, [x12], #4
	ldr	s2, [x11], #4
	fmadd	s1, s0, s1, s2
	str	s1, [x10], #4
	subs	x8, x8, #1
	b.ne	LBB0_9
LBB0_10:
	ret
	.cfi_endproc
                                        ; -- End function
.subsections_via_symbols
