import cstream


Unknown = 1
Identifier = Unknown+1


lowercaseLetters = [chr(z) for z in range(97, 123)]
uppercaseLetters = [chr(z) for z in range(65, 91)]
digits = [chr(z) for z in range(48, 58)]
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

    def getSymbol(self):
        """
        Interpret the next token from the current input stream.  Adjust
        scanner settings based on the token recognized, if any.  Return the
        kind of token.
        """
        self.name = ""
        ch = self._source.peek()

        if ch in lowercaseLetters:
            return self.getIdentifier()

        if ch in uppercaseLetters:
            return self.getIdentifier()

        if ch in whitespace:
            self.skipWhitespace()
            return self.getSymbol()

        return Unknown

