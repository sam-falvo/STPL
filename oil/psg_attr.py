"""
Parser, Symbol table, and code Generator common functions and data structures.
This module exists to break a circular dependency.  I know that circular
dependencies aren't necessarily a problem in Python, but I find them difficult
when maintaining code over the long term.
"""

import attr


@attr.s
class Item(object):
    """Attributes for in-flight expressions and code generation."""
    typ = attr.ib(default=None)  # Type of the expression this represents.
    cls = attr.ib(default=None)  # Variable?  Constant?  In CPU register?
    a = attr.ib(default=None)    # Depends on cls.

    # Types
    Unknown = 0
    Integer = 1

    # Classes
    Constant = 1  # a = value of the constant
    Global = 2    # a = Displacement from GP
    Register = 3  # a = Register number
