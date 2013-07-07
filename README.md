STPL
====

STPL stands for Sam's Toy Programming Language.

This is an attempt to write a compiler for some kind of language using a
completely hand-rolled LR parser.  Although not Kestrel-related, I used the
S16X4's instruction set as a starting point for the compiler's output.  The
output produced is hypothetical, though -- it will not run on real hardware
without an additional assembly step with some predefined macros.

Rationale
---------

Some time ago, I was running into seemingly intractible problems writing a
Forth interpreter to run native on the Kestrel-2.  Because different subsystems
that make up an interactive Forth environment are all so tightly coupled,
writing one using traditional TDD approaches proves quite difficult to
impossible.  So, I started asking the question, "What kind of systems
programming language can I write which is more conducive to TDD?"

I started looking at alternatives available.  Two languages _really_ stuck out
for me: Oberon and BCPL.  Just for comparison, here is some code to clear a
hypothetical text screen in each language, respectively:

```oberon
MODULE Screen;
	IMPORT SYSTEM;

	CONST	W=80;
		H=25;

	VAR	x, y: INTEGER;
		screenbase*: SYSTEM.PTR;
		ctr*: INTEGER;

	PROCEDURE	delay*;
	BEGIN		REPEAT ctr := ctr - 1 UNTIL ctr = 0;
	END delay;

	PROCEDURE	clr*;
	BEGIN		FOR i := 0 TO W*H DO
				(* Oberon is a type-safe language, unless you import SYSTEM.
				 * SYSTEM is what makes Oberon useful for systems programming.
				 *)
				SYSTEM.VAL(screenbase, ARRAY W*H OF CHAR)[i] := 32
			END
	END clr;

	PROCEDURE	home*;
	BEGIN		x := 0; y := 0;
	END home.
END Screen.
```

```bcpl
MANIFEST {
	W = 80;
	H = 25;
}

GLOBAL {
	clr; home; screenbase; ctr
}

LET x, y = ?, ?;
LET screenbase = ?;
LET ctr = ?;

LET delay() BE ctr = ctr - 1 REPEATUNTIL ctr = 0
LET clr() BE FOR i = 0 TO W*H DO screenbase%i := 32
LET home() BE x, y = 0, 0;
```

As you can see, both languages would be fairly easy to write a home-made LL
parser for (as, indeed, existing implementations of each utilize).  However,
they both had their uncertainties in other areas, and I wasn't convinced I
wanted to invest the time needed to make a fully conforming implementation of
the languages.  In particular, Oberon's compiler complexity stems mostly from
its support for strong type-safety, and in particular from a module file format
that records type information in a binary manner.  It expects the loader to
understand and similarly enforce type safety at the point a module is loaded.
The Oberon System does exactly this, of course, but the logic for it isn't
obvious to me.  I'll need to explore some more how best to implement this kind
of logic.  Moreover, Oberon is a garbage-collected environment, requiring me to
write a garbage collector.  BCPL's uncertainty concerns its "global vector,"
and how it's managed both within and between applications.  This, again,
requires runtime support, with some cooperation from the language compiler.

I then realized I had wanted a language suitable for writing the runtime itself
in.  So, I started exploring.  First, I wrote a very simple lexer.  Then I
added support for simple mathematical expressions.  Then I added support for
variable assignments.  Then for memory access.  Then for control flow.  It just
evolved organically.  Additionally, I wanted the most direct translation from
source to resulting assembly output, so I ended up making a kind of "event
driven" recognizer and translater.  The end result ended up not being LL, but
rather LR.  Moreover, since it competes more or less with the Machine Forth
translator I already have for the Kestrel-2, you can imagine it doesn't support
very high-level constructs at all.  None the less, I think you'll be impressed
with what it _can_ actually do.  Here's the same logic as above expressed in
STPL:

```
declare by80;		(* pointer to multiplication table: 80*n *)
declare ctr;
declare x,y;
declare screenbase;
declare w,h;		(* No constants yet, so make these variables *)

(* silly delay loop *)

delay:  let ctr = ctr+65535;
        return if ctr=0;
        goto delay;

(* Clear Screen capability for text console *)

home:   let x=0; let y=0; return;

clrx:   goto clrxx if (x-w)&32768; return;
clrxx:  let !(screenbase+(by80!(y+y))+x) = 32;
        let x=x+1; goto clrx;
clry:   goto clryy if (y-h)&32768; return;
clryy:  call clrx; let x=0; let y=y+1; goto clry;
clr:    call home; call clry; return;
init:	let w = 80; let h = 25; return;
```

Note that the compiler doesn't support comments (yet?).  Comments written above
are just to help the reader associate chunks of code between STPL, BCPL, and
Oberon examples.

As you can see, the resulting language has similar code density as BCPL or
Oberon, even though they're a bit higher level in notation.  Some code
explanation is in order:

* clrx jumps to clrxx if x < w.  Thinking in terms of binary, if x < w, then x-w < 0, which means bit 15 is set.  Hence the logical AND with 32768 in the IF clause.

* The moment x >= w, it will return, thus ending a loop created by the "goto clrx" statement.

* Similar arguments for clry and clryy.

* The ! operator is both a peek and a poke operation, depending on context.  When used on the left-hand side of an equals sign in a LET statement, it will serve as a poke.  Otherwise, it peeks memory.

* the ctr=ctr+65535 statement in the delay routine exists because it's more efficient than ctr=ctr-1, since the Kestrel-2's CPU lacks a subtract operator.  (This will be fixed with the Kestrel-3 of course.)

By pure accident, the resulting language happens to look a lot like compiled
BASIC, post-line-numbers, with some BCPL influences here and there.

I was surprised to get to this level of functionality after only about six
hours of hacking.  The resulting compiler output could conceivably work with an
existing S16X4-based system if I had bothered to either (1) implement a set of
assembler macros to fill in the missing gaps in the instruction set, OR, (2)
co-designed the next-generation processor to the needs of the compiler.

As you can see from looking at the code, it's definitely an LR parser.  We feed
program source to the lexer directly, character at a time.  The lexer then
recognizes when one token ends and another begins.  During this transition,
completed tokens are forwarded to the Recognizer instance to be dealt with how
it sees fit.

The recognizer, then, maintains a stack of symbols it has seen.  After each
symbol is pushed onto the stack, a set of transformation rules are invoked on
the stack.  The stack is thus manipulated until _no rules match_, and then
control returns back to the program's main loop.  Thus, you might say that this
language's parser is an event-driven parser, implementing an LR shift/reduce
algorithm.  Note that it goes directly from source code to assembly language --
no internal representations or parse trees are generated.  There's no
fundamental reason why this couldn't be done, and might even improve the
generated code quality substantially.  For example, all procedure labels are
actually variables.  This could be useful in certain limited cases.  For
example, suppose we have two character comparison routines:

```
(* case-sensitive character compare *)
cmp_char_cs:	let result = 65535;
		return if ch1=ch2;
		let result = 0; return

(* case-insensitive character compare *)
cmp_char:
cmp_char_ci:	let result = 65535;
		goto ch1_not_letter if (ch1-65)&32768;
		goto ch1_letter if (ch1-91)&32768;
		goto ch1_not_letter if (ch1-96)&32768;
		goto ch1_letter if (ch1-112)&32768;
ch1_not_letter:	let ch1_is_letter = 0; goto try_ch2;
ch1_letter:	let ch1_is_letter = 65535
try_ch2:	goto ch2_not_letter if (ch2-65)&32768;
		goto ch2_letter if (ch2-91)&32768;
		goto ch2_not_letter if (ch2-96)&32768;
		goto ch2_letter if (ch2-112)&32768;
ch2_not_letter:	let ch2_is_letter = 0; goto char_compare;
ch2_letter:	let ch2_is_letter = 65535
char_compare:	return if (ch1 & 95)=(ch2 & 95) if ch1_is_letter & ch2_is_letter;
		let result = 0; return

(* main entry point for character compare *)
cmp_char:	goto cmp_char_cs
```

We can redirect cmp_char at any time:

```
change_case_sensitivity:
	let cmp_char = cmp_char_cs;
	let cmp_char = cmp_char_ci if case_insensitive_mode;
	return;
```

However, this means that _every_ symbol reference goes through one level of
indirection, and it bloats the generated binary.  Generating an AST and
analyzing that just a little bit before generating code would eliminate that
extra level of indirection, and save a few bytes in the compiled output.  You
could still retain generality by using an actual variable, like so:

```
declare cmp_char
change_case_sensitivity:
	let cmp_char = cmp_char_cs;
	let cmp_char = cmp_char_ci if case_insensitive_mode;
	return;
```

It would still work, since GOTO and CALL take _expressions_, and are otherwise
not constrained to taking just labels.

Anyway, I hope you enjoyed this as much as I did writing it and learning from
it.  I have a better understanding now, and hopefully will be in a better
position to port the languages of my choice to the Kestrel platform.

