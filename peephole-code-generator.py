from __future__ import print_function


class Insn(object):
    def is_small_const(self):
        return self.opc == "ori" and self.dest != 0 and self.src1 == 0


class ADD(Insn):
    def __init__(self, dest, src1, src2):
        self.opc = "add"
        self.dest = dest
        self.src1 = src1
        self.src2 = src2

    def __repr__(self):
        return "\t{}\tX{}, X{}, X{}".format(self.opc, self.dest, self.src1, self.src2)


class ImmInsn(Insn):
    def reset(self, dest, src, imm):
        self.dest = dest
        self.src1 = src
        self.imm12 = imm

    def __repr__(self):
        return "\t{}\tX{}, X{}, {}".format(self.opc, self.dest, self.src1, self.imm12)

class ORI(ImmInsn):
    def __init__(self, dest, src, imm):
        self.opc = "ori"
        self.reset(dest, src, imm)


class ADDI(ImmInsn):
    def __init__(self, dest, src, imm):
        self.opc = "addi"
        self.reset(dest, src, imm)


class AUIPC(Insn):
    def __init__(self, dest, imm20):
        self.opc = "auipc"
        self.dest = dest
        self.imm20 = imm20

    def __repr__(self):
        return "\t{}\tX{}, {}".format(self.opc, self.dest, self.imm20)


class LD(Insn):
    def __init__(self, dest, offset, index):
        self.opc = "ld"
        self.dest = dest
        self.offset = offset
        self.index = index

    def __repr__(self):
        return "\t{}\tX{}, {}(X{})".format(self.opc, self.dest, self.offset, self.index)

class SD(Insn):
    def __init__(self, src, offset, index):
        self.opc = "sd"
        self.src = src
        self.offset = offset
        self.index = index

    def __repr__(self):
        return "\t{}\tX{}, {}(X{})".format(self.opc, self.src, self.offset, self.index)


class Optimizer(object):
    RA = 1
    RSP = 2
    DC = 3
    DSP = 4
    D0 = 5
    D1 = 6
    D2 = 7
    D3 = 8
    D4 = 9
    D5 = 10
    D6 = 11
    D7 = 12
    GP = 31

    def __init__(self):
        self.reset()

    def reset(self):
        self.C = []
        self.I = []
        self.regs_dstack = [self.DC]
        self.regs_rstack = []
        self.dsp_offset = 0
        self.rsp_offset = 0
        self.regs_avail = [self.D0, self.D1, self.D2, self.D3, self.D4, self.D5, self.D6, self.D7]
        self.gp_base = None

    def refill_register(self):
        if len(self.regs_avail) > 0:
            r = self.regs_avail[0]
            self.regs_dstack.append(r)
            self.regs_avail = self.regs_avail[1:]
            return r
        raise Exception("Out of registers")

    def next_register(self):
        if len(self.regs_avail) > 0:
            r = self.regs_avail[0]
            self.regs_dstack.insert(0, r)
            self.regs_avail = self.regs_avail[1:]
            return r
        raise Exception("Out of registers")

    def free_register(self, r):
        self.regs_avail.insert(0, r)

    def pop_register(self):
        r = self.regs_dstack[0]
        self.free_register(r)
        self.regs_dstack = self.regs_dstack[1:]
        return r

    def bind_s(self):
        r = self.refill_register()
        self.I.append(LD(r, self.dsp_offset, self.DSP))
        self.dsp_offset = self.dsp_offset + 8

    def literal(self, n):
        if -2048 <= n < 2048:
            r = self.next_register()
            self.I.append(ORI(r, 0, n))
        else:
            self.C.insert(0, n)
            if not self.gp_base:
                self.I.append(AUIPC(self.GP, 0))
                self.gp_base = -4 * (len(self.I) + 2)
            offset = -8 * (len(self.C) - 1)
            self.I.append(LD(self.next_register(), self.gp_base + offset, self.GP))

    def add(self):
        if len(self.regs_dstack) >= 2:
            rd = self.regs_dstack[1]
            rs = self.pop_register()
            self.I.append(ADD(rd, rd, rs))
        else:
            self.bind_s()
            self.add()

    def fetch(self):
        if len(self.regs_dstack) >= 1:
            rd = self.regs_dstack[0]
            self.I.append(LD(rd, 0, rd))
        else:
            self.bind_s()
            self.fetch()

    def store(self):
        if len(self.regs_dstack) >= 2:
            rs = self.regs_dstack[1]
            rd = self.regs_dstack[0]
            self.I.append(SD(rs, 0, rd))
            self.pop_register()
            self.pop_register()
        else:
            self.bind_s()
            self.store()

    def push(self):
        if len(self.regs_dstack) >= 1:
            r = self.regs_dstack[0]
            self.regs_dstack = self.regs_dstack[1:]
            self.regs_rstack.insert(0, r)
        else:
            self.bind_s()
            self.push()

    def pop(self):
        if len(self.regs_rstack) >= 1:
            r = self.regs_rstack[0]
            self.regs_rstack = self.regs_rstack[1:]
            self.regs_dstack.insert(0, r)
        else:
            r = self.refill_register()
            self.I.append(LD(r, self.rsp_offset, self.RSP))
            self.rsp_offset = self.rsp_offset + 8
            
    def dup(self):
        if len(self.regs_dstack) >= 1:
            r = self.regs_dstack[0]
            self.I.append(ORI(self.next_register(), r, 0))
        else:
            self.bind_s()
            self.dup()

    def swap(self):
        if len(self.regs_dstack) >= 2:
            t = self.regs_dstack[0]
            self.regs_dstack[0] = self.regs_dstack[1]
            self.regs_dstack[1] = t
        else:
            self.bind_s()
            self.swap()

    def over(self):
        if len(self.regs_dstack) >= 2:
            rs = self.regs_dstack[1]
            rd = self.next_register()
            self.I.append(ORI(rd, rs, 0))
        else:
            self.bind_s()
            self.over()

    def drop(self):
        self.pop_register()

    def add_imm(self, imm):
        rd = self.regs_dstack[0]
        self.I.append(ADDI(rd, rd, imm))

    def optimize(self):
        while self.optimize_step():
            pass

    def optimize_step(self):
        if len(self.I) >= 3:
            i0 = self.I[-1]
            i1 = self.I[-2]
            i2 = self.I[-3]
            if i0.opc == "add" and i1.is_small_const() and i2.is_small_const():
                n1 = i1.imm12
                n2 = i2.imm12
                self.pop_register()
                self.I = self.I[:-3]
                self.literal(n1+n2)
                return True

        if len(self.I) >= 2:
            i0 = self.I[-1]
            i1 = self.I[-2]
            if i0.opc == "add" and i1.is_small_const():
                n1 = i1.imm12
                self.I = self.I[:-2]
                self.add_imm(n1)
                return True
            elif i0.opc in ["ld", "sd"] and i1.opc == "ori" and i1.imm12 == 0 and i0.index == i1.dest:
                if i0.opc == "ld":
                    i = LD(i0.dest, i0.offset, i1.src1)
                else:
                    i = SD(i0.src, i0.offset, i1.src1)
                self.I = self.I[:-2]
                self.I.append(i)
                return True

        return False

    def dump(self):
        for c in self.C:
            print("\tDD\t{}".format(c))
        print("Entry:")
        for i in self.I:
            print(i)
        print("-----")

o = Optimizer()

o.literal(4000)
o.literal(5000)
o.over()
o.fetch()
o.over()
o.fetch()
o.over()
o.fetch()
o.over()
o.store()
o.literal(80)
o.add()
o.swap()
o.literal(256)
o.add()
o.push()
o.swap()
o.store()
o.pop()
o.swap()
o.store()

o.literal(3); o.optimize(); o.add(); o.optimize()
o.dump()

o.reset()

# o.literal(4000); o.optimize()
# o.literal(5000); o.optimize()
o.over(); o.optimize()
o.fetch(); o.optimize()
o.over(); o.optimize()
o.fetch(); o.optimize()
o.over(); o.optimize()
o.fetch(); o.optimize()
o.over(); o.optimize()
o.store(); o.optimize()
o.literal(80); o.optimize()
o.add(); o.optimize()
o.swap(); o.optimize()
o.literal(256); o.optimize()
o.add(); o.optimize()
o.push(); o.optimize()
o.swap(); o.optimize()
o.store(); o.optimize()
o.pop(); o.optimize()
o.swap(); o.optimize()
o.store(); o.optimize()

o.literal(3); o.optimize(); o.add(); o.optimize()
o.dump()

