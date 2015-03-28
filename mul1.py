from peephole import *

o = Optimizer()
o.subroutine("mul0")

o.dup(); o.optimize()
o.If(); o.optimize()
o.push(); o.optimize()
o.over(); o.optimize()
o.add(); o.optimize()
o.pop(); o.optimize()
o.literal(-1); o.optimize()
o.add(); o.optimize()
o.call("mul0"); o.optimize()
o.rfs(); o.optimize()
o.Then(); o.optimize()
o.drop(); o.optimize()
o.nip(); o.optimize()
o.rfs(); o.optimize()

o.commit()
o.dump()

