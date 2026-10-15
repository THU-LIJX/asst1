	.section	__TEXT,__text,regular,pure_instructions
	.build_version macos, 15, 1	sdk_version 15, 1
	.globl	__Z11saxpySerialifPfS_S_        ; -- Begin function _Z11saxpySerialifPfS_S_
	.p2align	2
__Z11saxpySerialifPfS_S_:               ; @_Z11saxpySerialifPfS_S_
	.cfi_startproc
; %bb.0:
	cmp	w0, #1
	b.lt	LBB0_3
; %bb.1:
	mov	w8, w0
LBB0_2:                                 ; =>This Inner Loop Header: Depth=1
	ldr	s1, [x1], #4
	ldr	s2, [x2], #4
	fmadd	s1, s0, s1, s2
	str	s1, [x3], #4
	subs	x8, x8, #1
	b.ne	LBB0_2
LBB0_3:
	ret
	.cfi_endproc
                                        ; -- End function
.subsections_via_symbols
