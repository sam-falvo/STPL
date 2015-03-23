from __future__ import print_function


class Insn(object):
    def is_small_const(self):
        return self.opc == "ori" and self.dest != 0 and self.src1 == 0


label_counter = 0

def new_label_name():
    global label_counter
    label_counter = label_counter + 1
    return "L{}".format(label_counter)


class BEQ(Insn):
    def __init__(self, r1, r2, label):
        self.opc = "beq"
        self.src1 = r1
        self.src2 = r2
        self.label = label

    def __repr__(self):
        return "\tbeq\tX{}, X{}, {}".format(self.src1, self.src2, self.label.name)


class Label(Insn):
    def __init__(self, name=None):
        self.opc = ":label:"

        if not name:
            self.name = new_label_name()
        else:
            self.name = name

    def __repr__(self):
        return "\n{}:".format(self.name)


class ADD(Insn):
    def __init__(self, dest, src1, src2):
        self.opc = "add"
        self.dest = dest
        self.src1 = src1
        self.src2 = src2

    def __repr__(self):
        return "\t{}\tX{}, X{}, X{}".format(self.opc, self.dest, self.src1, self.src2)


class XOR(Insn):
    def __init__(self, dest, src1, src2):
        self.opc = "xor"
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


class XORI(ImmInsn):
    def __init__(self, dest, src, imm):
        self.opc = "xori"
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

class JALR(Insn):
    def __init__(self, dest, offset, index):
        self.opc = "jalr"
        self.dest = dest
        self.offset = offset
        self.index = index

    def __repr__(self):
        return "\t{}\tX{}, {}(X{})".format(self.opc, self.dest, self.offset, self.index)


class JAL(Insn):
    def __init__(self, dest, label):
        self.opc = "jal"
        self.dest = dest
        self.label = label

    def __repr__(self):
        return "\t{}\tX{}, {}".format(self.opc, self.dest, self.label.name)



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
        self.regs_rstack = []
        self.rsp_offset = 0
        self.regs_avail = [self.D0, self.D1, self.D2, self.D3, self.D4, self.D5, self.D6, self.D7]
        self.gp_base = None
        self.reset_dstack()
        self.ctrl = []
        self.current_subroutine = None

    def reset_dstack(self):
        self.regs_dstack = [self.DC]
        self.dsp_offset = 0

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

    def commit_stack(self):
        if len(self.regs_dstack) < 2:
            return

        regs = self.regs_dstack[1:]
        regs.reverse()
        for r in regs:
            self.dsp_offset = self.dsp_offset - 8
            self.I.append(SD(r, self.dsp_offset, self.DSP))
            if r != self.DC:
                self.free_register(r)

    def commit_stack_cache(self):
        r = self.regs_dstack[0]
        self.I.append(ORI(self.DC, r, 0))
        self.free_register(r)

    def commit(self):
        self.commit_stack()

        if (len(self.regs_dstack) >= 1) and (self.regs_dstack[0] != self.DC):
            self.commit_stack_cache()
        elif len(self.regs_dstack) == 0:
            self.I.append(LD(self.DC, self.dsp_offset, self.DSP))
            self.dsp_offset = self.dsp_offset + 8

        if self.dsp_offset != 0:
            self.I.append(ADDI(self.DSP, self.DSP, self.dsp_offset))
            self.dsp_offset = 0

        self.reset_dstack()

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

    def xor(self):
        if len(self.regs_dstack) >= 2:
            rd = self.regs_dstack[1]
            rs = self.pop_register()
            self.I.append(XOR(rd, rd, rs))
        else:
            self.bind_s()
            self.xor()

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
        if len(self.regs_dstack) >= 1:
            self.pop_register()
        else:
            self.dsp_offset = self.dsp_offset + 8

    def nip(self):
        self.swap(); self.optimize()
        self.drop(); self.optimize()


    def add_imm(self, imm):
        rd = self.regs_dstack[0]
        self.I.append(ADDI(rd, rd, imm))

    def xor_imm(self, imm):
        rd = self.regs_dstack[0]
        self.I.append(XORI(rd, rd, imm))

    def subroutine(self, name):
        self.commit(); self.optimize()
        l = Label(name)
        self.I.append(l)
        self.current_subroutine = l

    def rfs(self):
        self.commit(); self.optimize()
        self.I.append(JALR(0, 0, self.RA))

    def If(self):
        if len(self.regs_dstack) < 1:
            self.bind_s()
            self.If()

        r = self.pop_register()

        self.commit(); self.optimize()
        self.ctrl.insert(0, Label())
        self.I.append(BEQ(r, 0, self.ctrl[0]))
    
    def Then(self):
        self.commit(); self.optimize()
        self.I.append(self.ctrl[0])
        self.ctrl = self.ctrl[1:]

    def call(self, name):
        self.commit(); self.optimize()
        self.I.append(JAL(self.RA, Label(name)))

    def recurse(self):
        self.commit(); self.optimize()
        self.I.append(JAL(self.RA, self.current_subroutine))

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
            if i0.opc == "xor" and i1.is_small_const():
                n1 = i1.imm12
                self.I = self.I[:-2]
                self.xor_imm(n1)
                return True
            elif i1.opc == "ori" and i1.imm12 == 0 and i0.opc == "ld" and i0.index == i1.dest:
                i = LD(i0.dest, i0.offset, i1.src1)
                self.I = self.I[:-2]
                self.I.append(i)
                return True
            elif i1.opc == "ori" and i1.imm12 == 0 and i0.opc == "sd" and i0.index == i1.dest:
                i = SD(i0.src, i0.offset, i1.src1)
                self.I = self.I[:-2]
                self.I.append(i)
                return True
            elif i1.opc == "ori" and i1.imm12 == 0 and i0.opc == "sd" and i0.src == i1.dest:
                i = SD(i1.src1, i0.offset, i0.index)
                self.I = self.I[:-2]
                self.I.append(i)
                return True
            elif i1.opc == "ori" and i1.imm12 == 0 and i0.opc in ["add", "xor"] and i0.dest == i0.src1 and i0.src2 == i1.dest:
                if i0.opc == "add":
                    i = ADD(i0.dest, i0.dest, i1.src1)
                elif i0.opc == "xor":
                    i = XOR(i0.dest, i0.dest, i1.src1)
                self.I = self.I[:-2]
                self.I.append(i)
                return True
            elif i1.opc == "jal" and i1.dest == self.RA and i0.opc == "jalr" and i0.dest == 0 and i0.offset == 0 and i0.index == self.RA:
                i = JAL(0, i1.label)
                self.I = self.I[:-2]
                self.I.append(i)
                return True
            elif i1.opc == "xor" and i1.dest == i1.src1 and i0.opc == "beq" and i0.src1 == i1.src1 and i0.src2 == 0:
                i = BEQ(i1.src1, i1.src2, i0.label)
                self.I = self.I[:-2]
                self.I.append(i)
                return True
        return False

    def dump(self):
        for c in self.C:
            print("\tDD\t{}".format(c))
        for i in self.I:
            print(i)
        print("\n")

o = Optimizer()
o.subroutine("cls0")
o.literal(65536); o.optimize()
o.over(); o.optimize()
o.xor(); o.optimize()
o.If(); o.optimize()
o.literal(0); o.optimize()
o.over(); o.optimize()
o.store(); o.optimize()
o.literal(8); o.optimize()
o.add(); o.optimize()
o.recurse(); o.optimize()
o.rfs(); o.optimize()
o.Then(); o.optimize()
o.drop(); o.optimize()
o.rfs(); o.optimize()

o.commit(); o.dump()

o = Optimizer()
o.subroutine("cls")
o.literal(49152); o.optimize()
o.call("cls0"); o.optimize()
o.rfs(); o.optimize()

o.commit(); o.dump()

