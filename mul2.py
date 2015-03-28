from peephole import *

o = Optimizer()
o.subroutine("m")

o.dup(); o.optimize()
o.literal(1); o.optimize()
o.And(); o.optimize()
o.If(); o.optimize()
o.push(); o.optimize()
o.over(); o.optimize()
o.add(); o.optimize()
o.pop(); o.optimize()
o.Then(); o.optimize()
o.div2(); o.optimize()
o.push(); o.optimize()
o.push(); o.optimize()
o.mul2(); o.optimize()
o.pop(); o.optimize()
o.pop(); o.optimize()
o.rfs(); o.optimize()

o.commit()
o.dump()

o = Optimizer()
o.subroutine("eight_m")

o.call("m"); o.optimize()
o.call("m"); o.optimize()
o.call("m"); o.optimize()
o.call("m"); o.optimize()
o.call("m"); o.optimize()
o.call("m"); o.optimize()
o.call("m"); o.optimize()
o.call("m"); o.optimize()
o.rfs(); o.optimize()

o.commit()
o.dump()

o = Optimizer()
o.subroutine("mul32x32u")

o.literal(0); o.optimize()
o.swap(); o.optimize()
o.call("eight_m"); o.optimize()
o.call("eight_m"); o.optimize()
o.call("eight_m"); o.optimize()
o.call("eight_m"); o.optimize()
o.rfs(); o.optimize()

o.commit()
o.dump()

