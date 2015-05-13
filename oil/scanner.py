import string

import cstream


def mkEnum(items, starting_at=1, transformer=lambda x: x):
    """
    Creates attributes such that each equals its ordinal position in a list.
    """
    g = globals()
    counter = starting_at
    for i in items:
        g[i] = transformer(counter)
        counter = counter + 1
        

mkEnum([
    # Unknown token scanned; usually indicates an error.
    "Unknown",

    # Identifier discovered; its name is in the scanner's name field.
    # The kind of identifier is refined through the scanner's kind flags.
    "Identifier",

    # Number discovered; its value is in the scanner's value field.
    # The kind of number is refined through the scanner's kind flags.
    # Its textual representation can be found via the name field, as it's
    # written in the source program.
    "Number",

    # String or character discovered.  Its literal representation is available
    # in the name field.  If a character, its ordinal number is in the value
    # field, and the kind has the Character flag set.
    "String",
])


mkEnum([
    # Set if the token is a cardinal number.
    "Cardinal",

    # Set if an integer token is expressed as a character.
    "Character",
], starting_at=0, transformer=lambda x: 1<<x)


lowercaseLetters = [chr(z) for z in range(97, 123)]
uppercaseLetters = [chr(z) for z in range(65, 91)]
digits = [chr(z) for z in range(48, 58)]
hexDigits = digits + [chr(z) for z in range(65, 71)]
whitespace = [' ', '\t', '\r', '\n']


class Scanner(object):
    """
    This class implements a text scanner suitable for tokenizing an Oberon
    source listing.
    """

    def __init__(self, source, filename=None):
        assert(isinstance(source, cstream.CSFileLike))
        self._source = cstream.CStream(source)
        self._filename = filename or "<unspecified>"
        self._line = 0
        self.name = ""

    def currentFilename(self):
        """Report the current source file.  Typically for error reporting."""
        return self._filename

    def currentLine(self):
        """Report the current line number.  Typically for error reporting."""
        return self._line

    def getIdentifier(self):
        """Reads an identifier from the input stream."""
        ch = self._source.peek()
        while ch in lowercaseLetters + uppercaseLetters + digits:
            self.name = self.name + self._source.get()
            ch = self._source.peek()
        return Identifier

    def skipWhitespace(self):
        ch = self._source.peek()
        while ch in whitespace:
            self._source.get()
            ch = self._source.peek()

    def getNumber(self):
        """Reads a number from the input stream."""
        def nxt():
            if self._source.peek() in ['a','b','c','d','e','f']:
                return string.upper(self._source.peek())
            else:
                return self._source.peek()

        ch = nxt()
        while ch in hexDigits:
            self.name = self.name + self._source.get()
            ch = nxt()

        if ch in ['x', 'X']:
            self.name = self.name + self._source.get()
            self.value = string.atoi(self.name[:-1], 16)
            self.kind = Cardinal | Character
        elif ch in ['h', 'H']:
            self.name = self.name + self._source.get()
            self.value = string.atoi(self.name[:-1], 16)
            self.kind = Cardinal
        else:
            self.value = string.atoi(self.name, 10)
            self.kind = Cardinal
        return Number

    def getString(self):
        """Reads a string from the input stream."""
        self._source.get()
        ch = self._source.peek()
        while True:
            if ch == '"':
                self._source.get()
                if len(self.name) == 1:
                    self.kind = Character
                    self.value = ord(self.name[0])
                return String
            if ch is cstream.CSEOF:
                raise Exception("End of string detected")

            self.name = self.name + self._source.get()
            ch = self._source.peek()
            
    def getSymbol(self):
        """
        Interpret the next token from the current input stream.  Adjust
        scanner settings based on the token recognized, if any.  Return the
        kind of token.
        """
        self.name = ""
        self.kind = 0
        self.value = 0

        ch = self._source.peek()

        if ch in lowercaseLetters:
            return self.getIdentifier()

        if ch in uppercaseLetters:
            return self.getIdentifier()

        if ch in whitespace:
            self.skipWhitespace()
            return self.getSymbol()

        if ch in digits:
            return self.getNumber()

        if ch == '"':
            return self.getString()

        return Unknown

