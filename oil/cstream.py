import abc


class CSEOF(object):
    """
    Intended to be a singleton class, an instance of CSEOF serves as a sentinel
    indicating no more input on the CStream is available.
    """


EOF = CSEOF()


class CSFileLike(object):
    """
    This ABC/interface indicates that your object implements File-like
    operations compatible with CStream's requirements.
    """
    __metaclass__ = abc.ABCMeta


CSFileLike.register(file)


class CStream(object):
    """
    Implements a simple stream of characters with a single character
    look-ahead.
    """
    def _read(self):
        ch = self._f.read(1)
        if not ch:
            return EOF
        return ch

    def __init__(self, f):
        assert(isinstance(f, CSFileLike))
        self._f = f
        self._lookAhead = self._read()

    def peek(self):
        return self._lookAhead

    def get(self):
        la = self._lookAhead
        self._lookAhead = self._read()
        return la

