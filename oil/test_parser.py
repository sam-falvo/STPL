#!/usr/bin/env python

import StringIO
import unittest

from parser import (Parser, Item)
from cstream import CSFileLike
from scanner import Scanner


CSFileLike.register(StringIO.StringIO)


def scannerFor(s):
    return Scanner(StringIO.StringIO(s))


class TestItem(unittest.TestCase):
    def testCreation(self):
        i = Item()
        self.assertEquals(i.typ, None)
        self.assertEquals(i.cls, None)

class TestParser(unittest.TestCase):
    def testIntegerLiteral(self):
        s = scannerFor("12345")
        p = Parser(scanner=s); p.scan()
        i = Item()
        p.Factor(i)
        self.assertEquals(i.typ, Item.Integer)
        self.assertEquals(i.cls, Item.Constant)
        self.assertEquals(i.a, 12345)
        self.assertEquals(s.hasErrors(), False)

    def testPositiveLiteral(self):
        s = scannerFor("+12345")
        p = Parser(scanner=s); p.scan()
        i = Item()
        p.Factor(i)
        self.assertEquals(i.typ, Item.Integer)
        self.assertEquals(i.cls, Item.Constant)
        self.assertEquals(i.a, 12345)
        self.assertEquals(s.hasErrors(), False)

    def testNegativeIntegerLiteral(self):
        s = scannerFor("-12345")
        p = Parser(scanner=s); p.scan()
        i = Item()
        p.Factor(i)
        self.assertEquals(i.typ, Item.Integer)
        self.assertEquals(i.cls, Item.Constant)
        self.assertEquals(i.a, -12345)
        self.assertEquals(s.hasErrors(), False)

    def testSimpleExpression(self):
        s = scannerFor("-12345+-2")
        p = Parser(scanner=s); p.scan()
        i = Item()
        p.SimpleExpression(i)
        self.assertEquals(i.typ, Item.Integer)
        self.assertEquals(i.cls, Item.Constant)
        self.assertEquals(i.a, -12347)
        self.assertEquals(s.hasErrors(), False)

    def testGlobalVarNotExist(self):
        class MySymtab(object):
            def lookup(self, i, name):
                i.typ = Item.Unknown

        s = scannerFor("glb"); st = MySymtab()
        p = Parser(scanner=s, symtab=st); p.scan()
        i = Item()
        p.SimpleExpression(i)
        self.assertEquals(s.hasErrors(), True)

    def testGlobalVarExist(self):
        class MySymtab(object):
            def __init__(self, test):
                self.test = test

            def lookup(self, i, name):
                self.test.assertEquals(name, "glb")
                i.typ = Item.Integer
                i.cls = Item.Global
                i.a = 8

        s = scannerFor("glb"); st = MySymtab(self)
        p = Parser(scanner=s, symtab=st); p.scan()
        i = Item()
        p.SimpleExpression(i)
        self.assertEquals(s.hasErrors(), False)
        self.assertEquals(i.typ, Item.Integer)
        self.assertEquals(i.cls, Item.Global)
        self.assertEquals(i.a, 8)

    def testGlobalArithmetic(self):
        class MySymtab(object):
            def lookup(self, i, name):
                i.typ = Item.Integer; i.cls = Item.Global
                if name == 'p':
                    i.a = 8
                elif name == 'q':
                    i.a = 16
                else:
                    i.typ = Item.Unknown

        class MyCG(object):
            def __init__(self):
                self.loaded = []
                self.addCalled = False
                self.subCalled = False
                self.rh = 2

            def load(self, i):
                if i.cls == Item.Register:
                    return  # already loaded.
                elif i.cls == Item.Global:
                    self.loaded.append(i.a)
                    print("\tld\tx{}, {}(gp)".format(self.rh, i.a))
                    i.cls = Item.Register
                    i.a = self.rh
                    self.rh = self.rh + 1
                elif i.cls == Item.Constant:
                    print("\taddi\tx{}, x0, {}".format(self.rh, i.a))
                    i.cls = Item.Register
                    i.a = self.rh
                    self.rh = self.rh + 1
                else:
                    print("Unknown load {}".format(i))

            def add(self, i, j):
                print("\tadd\tx{}, x{}, x{}".format(i.a, i.a, j.a))
                self.rh = self.rh - 1
                self.addCalled = True

            def sub(self, i, j):
                print("\tsub\tx{}, x{}, x{}".format(i.a, i.a, j.a))
                self.rh = self.rh - 1
                self.subCalled = True

        s = scannerFor("p+q-32"); st = MySymtab(); cg = MyCG()
        p = Parser(scanner=s, symtab=st, cg=cg); p.scan()
        i = Item()
        p.SimpleExpression(i)
        self.assertEquals(i.typ, Item.Integer)
        self.assertEquals(i.cls, Item.Register)
        self.assertEquals(i.a, 2)
        self.assertEquals(8 in cg.loaded, True)
        self.assertEquals(16 in cg.loaded, True)
        self.assertEquals(cg.addCalled, True)
        self.assertEquals(cg.subCalled, True)
        self.assertEquals(cg.rh, 3)


if __name__ == "__main__":
    unittest.main()

