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

    def testDecimalNumbers(self):
        source = StringIO.StringIO("12345")
        s = scanner.Scanner(source=source, filename="<>")
        self.assertEquals(s.getSymbol(), scanner.Number)
        self.assertEquals(s.kind, scanner.Cardinal)
        self.assertEquals(s.value, 12345)

    def testHexNumbers(self):
        source = StringIO.StringIO("12345H 0FFFFFFFFFFFFFFFFh")
        s = scanner.Scanner(source=source, filename="<>")
        self.assertEquals(s.getSymbol(), scanner.Number)
        self.assertEquals(s.kind, scanner.Cardinal)
        self.assertEquals(s.value, 0x12345)
        self.assertEquals(s.getSymbol(), scanner.Number)
        self.assertEquals(s.kind, scanner.Cardinal)
        self.assertEquals(s.value, 0xFFFFFFFFFFFFFFFF)

    def testCharNumbers(self):
        source = StringIO.StringIO("12345X")
        s = scanner.Scanner(source=source, filename="<>")
        self.assertEquals(s.getSymbol(), scanner.Number)
        self.assertEquals(s.kind, scanner.Character | scanner.Cardinal)
        self.assertEquals(s.value, 0x12345)


if __name__ == "__main__":
    unittest.main()
