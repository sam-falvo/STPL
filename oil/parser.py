import attr

import scanner
from psg_attr import Item


@attr.s
class Parser(object):
    """Parses an Oberon module."""
    scanner = attr.ib()
    symtab = attr.ib(default=None)
    cg = attr.ib(default=None)

    def scan(self):
        self.nextToken = self.scanner.getSymbol()

    def SimpleExpression(self, i):
        self.Factor(i)
        while self.nextToken in [scanner.Minus, scanner.Plus]:
            op = self.nextToken; self.scan()
            j = Item()
            self.Factor(j)
            if (i.typ != Item.Integer) or (j.typ != Item.Integer):
                self.scanner.mark("Type mismatch; integer expected")
            elif (i.cls == Item.Constant) and (j.cls == Item.Constant):
                i.a = {
                    scanner.Plus: i.a + j.a,
                    scanner.Minus: i.a - j.a,
                }[op]
            else:
                self.cg.load(i); self.cg.load(j)
                if op == scanner.Plus:
                        self.cg.add(i, j)
                else:
                        self.cg.sub(i, j)

    def Factor(self, i):
        if self.nextToken == scanner.Number:
            i.typ = Item.Integer
            i.cls = Item.Constant
            i.a = self.scanner.value
            self.scan()
        elif self.nextToken == scanner.Identifier:
            self.Designator(i)
        elif self.nextToken == scanner.Plus:
            self.scan()
            self.Factor(i)
        elif self.nextToken == scanner.Minus:
            self.scan()
            self.Factor(i)
            if i.typ == Item.Integer:
                if i.cls == Item.Constant:
                    i.a = -i.a 
                else:
                    self.scanner.mark("How to negate this?")
            else:
                self.scanner.mark("Cannot negate a non-number")

    def Designator(self, i):
        self.symtab.lookup(i, self.scanner.name)
        if i.typ == Item.Unknown:
            self.scanner.mark("Undefined identifier {}".format(self.scanner.name))
        else:
            self.scan()
