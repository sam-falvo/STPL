#!/usr/bin/env python

import unittest

import attr


from symtab import SymTab


@attr.s
class Item(object):
    # Stub until we merge with master
    typ = attr.ib(default=None)
    cls = attr.ib(default=None)
    a = attr.ib(default=None)

    Unknown = 0


class TestSymTab(unittest.TestCase):
    def testCreation(self):
        st = SymTab()

    def testQueryNotExist(self):
        st = SymTab(); i = Item()
        st.lookup(i, "foo")
        self.assertEquals(i.typ, Item.Unknown)


if __name__ == "__main__":
    unittest.main()

