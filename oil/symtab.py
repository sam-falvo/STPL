from parser import Item

class SymTab(object):
    def lookup(self, item, name):
        item.typ = Item.Unknown
