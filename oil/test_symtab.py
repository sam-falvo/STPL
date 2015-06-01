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


if __name__ == "__main__":
    unittest.main()

