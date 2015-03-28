from peephole import *

o = Optimizer()
o.subroutine("rows")

o.dup(); o.optimize()
o.literal(8); o.optimize()
o.xor(); o.optimize()
o.If(); o.optimize()
o.drop(); o.optimize()
o.drop(); o.optimize()
o.drop(); o.optimize()
o.rfs(); o.optimize()
o.Then(); o.optimize()
o.over(); o.optimize()
o.cfetch(); o.optimize()
o.over(); o.optimize()
o.cstore(); o.optimize()
o.literal(80); o.optimize()
o.add(); o.optimize()
o.swap(); o.optimize()
o.literal(256); o.optimize()
o.add(); o.optimize()
o.swap(); o.optimize()
o.call("rows"); o.optimize()
o.rfs(); o.optimize()

o.commit()
o.dump()

o = Optimizer()
o.subroutine("plotch")

o.literal(8); o.optimize()
o.call("rows"); o.optimize()
o.rfs(); o.optimize()

o.commit()
o.dump()

