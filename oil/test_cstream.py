#!/usr/bin/env python

import unittest
import StringIO

import cstream


# Tell CStream that our strings are sufficiently file-like for its needs.
# Otherwise, an isinstance assertion will trigger.
cstream.CSFileLike.register(StringIO.StringIO)


class TestCStream(unittest.TestCase):
    def testCreation(self):
        cs = cstream.CStream(StringIO.StringIO("hello"))
        self.assertEquals(cs.peek(), 'h')

    def testGet(self):
        cs = cstream.CStream(StringIO.StringIO("hello"))
        self.assertEquals(cs.get(), 'h')
        self.assertEquals(cs.peek(), 'e')

    def testEOF(self):
        cs = cstream.CStream(StringIO.StringIO("X"))
        self.assertEquals(cs.get(), 'X')
        self.assertEquals(cs.peek(), cstream.EOF)
        self.assertEquals(cs.get(), cstream.EOF)
        self.assertEquals(cs.peek(), cstream.EOF)


if __name__ == "__main__":
    unittest.main()

