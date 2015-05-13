;;; Destination Driven Code Generation (experimental)
;;;
;;; Given a simple, unsafe, imperative language expressed in s-expr notation,
;;; compile to a sequence of RISC-V instructions.  The language should at least
;;; be as comfortable to use as Forth.

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;
; Generic utilities.  I'm sure Scheme has similar functionality that I just
; do not know about.  But, I wrote my own versions in part for the practice,
; but also because I was too lazy to research the built-in set of primitives.
;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;


(define (in? needle haystack)
	(cond	((atom? haystack)		#f)	; also checks for '()
		((eq? needle (car haystack))	#t)
		(else				(in? needle (cdr haystack)))))

(define (filter needle haystack)	; NOTE: Swaps order of haystack.
	(define (filter0 needle todo filtered)
		(if (atom? todo)
			filtered
		; else
			(let	((candidate  (car todo)))

				(filter0 needle
					 (cdr todo)
					 (if (eq? needle candidate)
						filtered
					 ; else
						(cons candidate filtered))))))

	(filter0 needle haystack '()))

(define (upto needle haystack)	; return haystack up to, but not including, needle.
	(define (upto0 n h acc)
		(cond	((eq? h '()) acc)
			((eq? (car h) n) acc)
			(else (upto0 n (cdr h) (cons (car h) acc)))))
	(upto0 needle haystack '()))

(define (after needle haystack)
	(cond	((eq? haystack '())		'())
		((eq? (car haystack) needle)	(cdr haystack))
		(else		(after needle (cdr haystack)))))

(define (mapinc f xs acc inc)
	(cond	((eq? xs '())			'())
		(else	(cons (f (car xs) acc) (mapinc f (cdr xs) (+ acc inc) inc)))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;
; REGISTER ALLOCATION
;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;


(define registers-available '(s0 s1 s2 s3 s4 s5 s6 s7))
(define registers-allocated '())


(define (new-register)
	(define (allocate)
		(let* ((reg	       (car registers-available))
		       (new-available  (cdr registers-available))
		       (new-allocated  (cons reg registers-allocated)))

			(set! registers-available new-available)
			(set! registers-allocated new-allocated)
			reg))
	(if (> (length registers-available) 0) (allocate) '()))


(define (dispose-register r)
	(define (dispose r)
		(set! registers-available (cons r registers-available))
		(set! registers-allocated (filter r registers-allocated))
		'freed
	)
	(if (in? r registers-allocated)
		(dispose r)
	; else
		'no-change))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;
; CODE GENERATION (for RV64I RISC-V instruction set)
;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;


(define (goto k)
	(cond
	  ((eq? k 'next) '())
	  ((eq? k 'return) '(insn jalr x0 ra 0))
	  (else `(insn jal x0 ,k))))

(define (compile-number n d k)
	`((insn ori ,d x0 ,n) ,(goto k)))

(define (compile-char ch d k)
	`((insn ori ,d x0 ,(char->integer ch)) ,(goto k)))

; (op v1 v2 ...)
; where op in {+, -, and, or, xor}
(define (compile-bin form i d k)
	(let*	((ap (compile (car form) d 'next))
		 (r (new-register))
		 (aps (map (lambda (p) `(,(compile p r 'next) (insn ,i ,d ,d ,r))) (cdr form))))

		(dispose-register r)
		`(,ap ,aps ,(goto k))))

; ( @ addr )
; ( C@ addr )
(define (compile-fetch form i d k)
	`(,(compile-bin (cdr form) 'add d 'next) (insn ,i ,d ,d 0) ,(goto k)))

; ( ! start-addr = v1 v2 v3 ... )
; ( C! start-addr = v1 v2 v3 ... )
(define (compile-store form i d k inc)
	(let*	((r (new-register))
		 (ea (compile-bin (upto '= (cdr form)) 'add r 'next))
		 (ps (mapinc (lambda (p ofs) `(,(compile p d 'next) (insn ,i ,d ,r ,ofs))) (after '= form) 0 inc))
		 (asm `(,ea ,ps ,(goto k))))

		(dispose-register r)
		asm))

(define (compile form d k)
	(cond
	  ((eq? form '())	(goto k))
	  ((number? form)	(compile-number form d k))
	  ((char? form)		(compile-char form d k))
	  ((eq? (car form) '+)	(compile-bin (cdr form) 'add d k))
	  ((eq? (car form) '-)	(compile-bin (cdr form) 'sub d k))
	  ((eq? (car form) 'and)(compile-bin (cdr form) 'and d k))
	  ((eq? (car form) 'or)	(compile-bin (cdr form) 'or d k))
	  ((eq? (car form) 'xor)(compile-bin (cdr form) 'xor d k))
	  ((eq? (car form) '@)  (compile-fetch form 'ld d k))
	  ((eq? (car form) 'C@) (compile-fetch form 'lb d k))
	  ((eq? (car form) '!)  (compile-store form 'sd d k 8))
	  ((eq? (car form) 'C!) (compile-store form 'sb d k 1))
	  (else			(printf "~a\n" form) 'unknown-form-error)))

(new-register)
(printf "~a\n" (compile '(C! 1024 = #\H #\e #\l #\l #\o #\, #\space #\W #\o #\r #\l #\d #\.) 's0 'return))
(dispose-register 's0)

