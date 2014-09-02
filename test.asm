start	lda	0,n0
	sta	1,n1
	lda	2,n0
	sta	3,n1
	jmp	0,3
n0	dcw	0
n1	dcw	1,2,3
