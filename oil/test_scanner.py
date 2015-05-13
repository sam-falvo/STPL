#!/usr/bin/env python

import unittest
import StringIO

import cstream
import scanner


cstream.CSFileLike.register(StringIO.StringIO)

noInput = StringIO.StringIO("")


class TestScanner(unittest.TestCase):
    def testCreation(self):
        s = scanner.Scanner(noInput)
        self.assertEquals(s.currentFilename(), "<unspecified>")
        self.assertEquals(s.currentLine(), 0)

    def testIdentifiers(self):
        sources = [
            StringIO.StringIO("i"),
            StringIO.StringIO("helloWorld"),
            StringIO.StringIO("Oberon07"),
            StringIO.StringIO("i18n"),
        ]
        scanners = [scanner.Scanner(source=s, filename="<>") for s in sources]
        tokens = [scanner.Identifier for _ in scanners]
        names = ["i", "helloWorld", "Oberon07", "i18n"]

        for i in range(len(tokens)):
            self.assertEquals(
                scanners[i].getSymbol(), tokens[i], msg="{}".format(i)
            )
            self.assertEquals(
                scanners[i].name, names[i],
                msg="{} != {}".format(scanners[i].name, names[i])
            )

    def testIdentifiersInSequence(self, text=None):
        text = text or "i helloWorld Oberon07 i18n"
        source = StringIO.StringIO(text)
        s = scanner.Scanner(source=source, filename="<>")
        names = ["i", "helloWorld", "Oberon07", "i18n"]
        for i in range(len(names)):
            self.assertEquals(s.getSymbol(), scanner.Identifier)
            self.assertEquals(
                s.name, names[i], msg="{} != {}".format(s.name, names[i])
            )

    def testSkipsWhitespace(self):
        return self.testIdentifiersInSequence(
            text="i  helloWorld\nOberon07\n\t\t\ti18n"
        )

    def testNumbers(self, source="12345", value=12345, kind=scanner.Cardinal):
        source = StringIO.StringIO(source)
        s = scanner.Scanner(source=source, filename="<>")
        self.assertEquals(s.getSymbol(), scanner.Number)
        self.assertEquals(s.kind, kind)
        self.assertEquals(s.value, value)
        
    def testHexNumbers(self):
        self.testNumbers(source="12345H", value=0x12345)
        return self.testNumbers(
            source="0FFFFFFFFFFFFFFFFh",
            value=0xFFFFFFFFFFFFFFFF
        )

    def testCharNumbers(self):
        return self.testNumbers(
            source="45X", value=0x45,
            kind=scanner.Cardinal|scanner.Character
        )


if __name__ == "__main__":
    unittest.main()

