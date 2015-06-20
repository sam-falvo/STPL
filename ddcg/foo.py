from compiler import Compiler
from ast import *

c = Compiler()

#c.compile(
#	Procedure("delay", ["n"], [],
#	Begin([
#		If(Var("n"), Begin([
#			Set(Var("n"), Add(Var("n"), IntLit(-1))),
#			Call("delay", [Var("n")])
#		]), None)
#	]))
#)

c.compile(
	Procedure("strlen", ["a", "u"], [],
	Begin([
		Call("strlen0", [Var("a"), Var("u"), IntLit(0)])
	]))
)

c.compile(
	Procedure("strlen0", ["a", "u", "len"], [],
	Begin([
		If(PeekByte(Var("a")),
			Call("strlen0", [Add(Var("a"), IntLit(1)), Add(Var("u"), IntLit(-1)), Add(Var("len"), IntLit(1))]),
			ReturnIs(Var("len"))
		)
	]))
)


print c.source()
