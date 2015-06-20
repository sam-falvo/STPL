import attr
from ast import *


@attr.s
class Register(object):
        r = attr.ib(validator=attr.validators.instance_of(int))


@attr.s
class FrameLocal(object):
        name = attr.ib(validator=attr.validators.instance_of(str))
        offset = attr.ib(validator=attr.validators.instance_of(int))


@attr.s
class Compiler(object):
        symtab = attr.ib(default=attr.Factory(dict))
        frameOffset = attr.ib(default=0)
        nextLabel = attr.ib(default=0)
        nextRegister = attr.ib(default=0)
        _source = attr.ib(default=attr.Factory(list))

        def asm(self, line):
                self._source.append(line)

        def source(self):
                return "{}\n".format("\n".join(self._source))

        def topRegister(self):
                return self.nextRegister - 1

        def allocRegister(self):
                self.nextRegister = self.nextRegister + 1
                return self.topRegister()

        def popRegister(self, by=1):
                self.nextRegister = self.nextRegister - by
                return self.nextRegister

        def allocLabel(self):
                self.nextLabel = self.nextLabel + 1
                return self.nextLabel - 1

        def nextOffset(self):
                self.frameOffset = self.frameOffset + 8

        def assignParam(self, p):
                self.symtab[p] = FrameLocal(p, self.frameOffset)
                self.nextOffset()

        def saveReg(self, varName, reg):
                self.asm("\tsd\tx{}, {}(sp)".format(reg, self.symtab[varName].offset))

        def return_(self):
                self.asm("\tld\tx1, 0(sp)")
                self.asm("\taddi\tsp, sp, {}".format(self.frameSize))
                self.asm("\tjal\tx0, 0(x1)")

        def goto(self, ift, iff, brt, brf):
                if ift == iff:
                        if ift == Return:
                                self.return_()
                        elif ift:
                                self.asm("\tjal\tx0, L{}".format(ift))
                else:
                        reg = self.topRegister()
                        if not ift and iff != Return:
                                self.asm("\t{}\tx{}, x0, L{}".format(brf, reg, iff))
                        elif not iff and ift != Return:
                                self.asm("\t{}\tx{}, x0, L{}".format(brt, reg, ift))
                        elif not ift and iff == Return:
                                l = self.allocLabel()
                                self.asm("\t{}\tx{}, x0, L{}".format(brt, reg, l))
                                self.return_()
                                self.asm("L{}:".format(l))
                        elif not iff and ift == Return:
                                self.asm("-- not sure how to handle this (B) --")
                        else:
                                self.goto(None, iff, brt, brf)
                                self.goto(ift, ift, brt, brf)

        def cgProcedure(self, x, ift, iff):
                self.asm("{}:".format(x.name))

                self.currentProcedureName = x.name
                self.frameSize = 8*(len(x.params) + len(x.locals) + 1)
                self.asm("\taddi\tsp, sp, -{}".format(self.frameSize))

                self.assignParam("$rpc")  # our return address is always the first implicit parameter.
                self.saveReg("$rpc", 1)
                reg = 2
                for p in x.params:
                        self.assignParam(p)
                        self.saveReg(p, reg)
                        reg = reg + 1

                for l in x.locals:
                        self.assignParam(l)

                self.cg(x.statement, ift, iff, None)

        def cgBegin(self, x, ift, iff):
                if len(x.statements) > 0:
                        final = x.statements[-1]
                        for s in x.statements[:-1]:
                                self.cg(s, None, None, None)
                        self.cg(final, ift, iff, None)

        def cgIf(self, x, ift, iff):
                if x.alt:
                        labelTrue = self.allocLabel()
                        labelFalse = self.allocLabel()
                        rp = self.allocRegister()
                        self.cg(x.pred, ift=labelTrue, iff=labelFalse, dd=Register(rp))
                        self.popRegister()
                        self.asm("L{}:".format(labelTrue))
                        self.cg(x.con, ift=ift, iff=iff, dd=None)
                        self.asm("L{}:".format(labelFalse))
                        self.cg(x.alt, ift=ift, iff=iff, dd=None)
                else:
                        #labelFalse = self.allocLabel()
                        rp = self.allocRegister()
                        self.cg(x.pred, ift=None, iff=iff, dd=Register(rp))
                        self.popRegister()
                        self.cg(x.con, ift=ift, iff=iff, dd=None)
                        #self.asm("L{}:".format(labelFalse))

        def cgIntLit(self, x, ift, iff, dd):
                if isinstance(dd, Register):
                        self.asm("\taddi\tx{}, x0, {}".format(dd.r, x.rval))
                        self.goto(ift, iff, "bne", "beq")
                else:
                        self.asm("-- Don't know how to compile a literal to anything but a register --")

        def cgVar(self, x, ift, iff, dd):
                desc = self.symtab[x.name]
                if isinstance(desc, FrameLocal) and isinstance(dd, Register):
                        self.asm("\tld\tx{}, {}(sp)".format(dd.r, desc.offset))
                        self.goto(ift, iff, "bne", "beq")
                elif isinstance(desc, FrameLocal) and not isinstance(dd, Register):
                        self.asm("-- unsupported storage target for cgVar --")
                else:
                        self.asm("-- unsupported symtab object --")

        def cgSet(self, x, ift, iff):
                rvr = self.allocRegister()
                self.cg(x.rval, None, None, Register(rvr))
                if isinstance(x.lval, Var):
                        desc = self.symtab[x.lval.name]
                        if isinstance(desc, FrameLocal):
                                self.asm("\tsd\tx{}, {}(fp)".format(rvr, desc.offset))
                        else:
                                self.asm("-- unsupported symtab object --")
                else:
                        self.asm("-- unsupported set target --")
                self.popRegister()
                self.goto(ift, iff, "bne", "beq")

        def cgAdd(self, x, ift, iff, dd):
                if isinstance(dd, Register):
                        rr = self.allocRegister()
                        self.cg(x.lhs, None, None, dd)
                        self.cg(x.rhs, None, None, Register(rr))
                        self.asm("\tadd\tx{}, x{}, x{}".format(dd.r, dd.r, rr))
                        self.popRegister()
                        self.goto(ift, iff, "bne", "beq")
                else:
                        self.asm("-- Don't know how to add to non-register --")

        def cgCall(self, x, ift, iff):
                for p in x.params:
                        r = self.allocRegister()
                        self.cg(p, None, None, Register(r))
                self.asm("\tjal\tx1, {}".format(x.f))
                self.popRegister(by=len(x.params))
                self.goto(ift, iff, "bne", "beq")

        def cgPeekByte(self, x, ift, iff, dd):
                if isinstance(dd, Register):
                        self.cg(x.lval, None, None, dd)
                        self.asm("\tlb\tx{}, 0(x{})".format(dd.r, dd.r))
                else:
                        self.asm("-- don't know how to fetch byte from non-register address --")
                self.goto(ift, iff, "bne", "beq")

        def cgReturnIs(self, x, ift, iff):
                if x.expr:
                        self.cg(x.expr, None, None, Register(2))
                self.goto(Return, Return, "bne", "beq")

        def cg(self, x, ift, iff, dd):
                if isinstance(x, Procedure):
                        self.cgProcedure(x, ift, iff)
                elif isinstance(x, Begin):
                        self.cgBegin(x, ift, iff)
                elif isinstance(x, If):
                        self.cgIf(x, ift, iff)
                elif isinstance(x, Var):
                        self.cgVar(x, ift, iff, dd)
                elif isinstance(x, IntLit):
                        self.cgIntLit(x, ift, iff, dd)
                elif isinstance(x, Set):
                        self.cgSet(x, ift, iff)
                elif isinstance(x, Add):
                        self.cgAdd(x, ift, iff, dd)
                elif isinstance(x, Call):
                        self.cgCall(x, ift, iff)
                elif isinstance(x, PeekByte):
                        self.cgPeekByte(x, ift, iff, dd)
                elif isinstance(x, ReturnIs):
                        self.cgReturnIs(x, Return, Return)
                elif x is None:
                        self.goto(ift, iff, "bne", "beq")
                else:
                        self.asm("-- incomplete --")

        def compile(self, x):
                self.nextRegister = 2
                self.frameOffset = 0
                self.cg(x, Return, Return, None)
