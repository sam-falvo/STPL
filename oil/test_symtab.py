#!/usr/bin/env python

import unittest

import attr


from parser import Item
from symtab import SymTab


class TestSymTab(unittest.TestCase):
    def testCreation(self):
        st = SymTab()

    def testQueryNotExist(self):
        st = SymTab(); i = Item()
        st.lookup(i, "foo")
        self.assertEquals(i.typ, Item.Unknown)

    def testInsert(self):
        st = SymTab(); st.openScope()
        i = Item(typ=Item.Integer, cls=Item.Global, a=16)
        st.insert(i, "foo")
        j = Item()
        st.lookup(j, "foo")
        self.assertEquals(i.typ, j.typ)
        self.assertEquals(i.cls, j.cls)
        self.assertEquals(i.a, j.a)

    def testScopes(self):
        st = SymTab(); st.openScope()
        st.insert(Item(typ=Item.Integer, cls=Item.Constant, a=100), "foo")
        st.insert(Item(typ=Item.Integer, cls=Item.Constant, a=200), "bar")
        st.openScope()
        st.insert(Item(typ=Item.Integer, cls=Item.Global, a=0), "foo")
        j = Item()
        st.lookup(j, "foo")
        self.assertEquals(j.typ, Item.Integer)
        self.assertEquals(j.cls, Item.Global)
        self.assertEquals(j.a, 0)
        st.lookup(j, "bar")
        self.assertEquals(j.typ, Item.Integer)
        self.assertEquals(j.cls, Item.Constant)
        self.assertEquals(j.a, 200)
        st.closeScope()
        st.lookup(j, "foo")
        self.assertEquals(j.typ, Item.Integer)
        self.assertEquals(j.cls, Item.Constant)
        self.assertEquals(j.a, 100)
        st.lookup(j, "bar")
        self.assertEquals(j.typ, Item.Integer)
        self.assertEquals(j.cls, Item.Constant)
        self.assertEquals(j.a, 200)
        st.closeScope()
        st.lookup(j, "foo")
        self.assertEquals(j.typ, Item.Unknown)


if __name__ == "__main__":
    unittest.main()

