import attr

a = attr.validators.instance_of
an = a

@attr.s
class optional(object):
	"""
	An attr validator that makes an attribute optional.
	An optional field is one which can be set to None
	in addition to its intended data type.
	"""
	v = attr.ib()

	def __call__(self, inst, attr, value):
		if value is None:
			return
		return self.v(inst, attr, value)


class _return(object):
        pass
Return = _return()


@attr.s
class Statement(object):
	pass


@attr.s
class Expression(object):
	pass


@attr.s
class IntLit(Expression):
	rval = attr.ib(validator=an(int))


@attr.s
class Var(Expression):
	name = attr.ib(validator=an(str))


@attr.s
class Nil(Expression):
	pass


@attr.s
class Procedure(object):
	name = attr.ib(validator=a(str))
	params = attr.ib(validator=a(list))
	locals = attr.ib(validator=a(list))
	statement = attr.ib(validator=a(Statement))


@attr.s
class Begin(Statement):
	statements = attr.ib(validator=a(list))


@attr.s
class Set(Statement):
	lval = attr.ib(validator=a(Expression))
	rval = attr.ib(validator=an(Expression))


@attr.s
class If(Statement):
	pred = attr.ib(validator=an(Expression))
	con = attr.ib(validator=a(Statement))
	alt = attr.ib(validator=optional(a(Statement)))

@attr.s
class Call(Statement):
	f = attr.ib(validator=a(str))
	params = attr.ib(validator=a(list))

@attr.s
class Return(Statement):
	expr = attr.ib(validator=an(Expression))

@attr.s
class Add(Expression):
	lhs = attr.ib(validator=an(Expression))
	rhs = attr.ib(validator=an(Expression))


@attr.s
class Sub(Expression):
	lhs = attr.ib(validator=an(Expression))
	rhs = attr.ib(validator=an(Expression))


@attr.s
class Shl(Expression):
	lhs = attr.ib(validator=an(Expression))
	rhs = attr.ib(validator=an(Expression))


@attr.s
class Shr(Expression):
	lhs = attr.ib(validator=an(Expression))
	rhs = attr.ib(validator=an(Expression))


@attr.s
class And(Expression):
	lhs = attr.ib(validator=an(Expression))
	rhs = attr.ib(validator=an(Expression))


@attr.s
class Or(Expression):
	lhs = attr.ib(validator=an(Expression))
	rhs = attr.ib(validator=an(Expression))


@attr.s
class Xor(Expression):
	lhs = attr.ib(validator=an(Expression))
	rhs = attr.ib(validator=an(Expression))

@attr.s
class PeekByte(Expression):
        lval = attr.ib(validator=an(Expression))


@attr.s
class ReturnIs(Statement):
        expr = attr.ib(validator=optional(an(Expression)))

