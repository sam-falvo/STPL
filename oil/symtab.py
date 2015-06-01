import attr

from parser import Item


@attr.s
class SymTab(object):
    scopes = attr.ib(default=None)

    def lookup(self, item, name):
        if self.scopes is not None:
            for scope in self.scopes:
                if name in scope:
                    j = scope[name]
                    item.typ = j.typ
                    item.cls = j.cls
                    item.a = j.a
                    return
        item.typ = Item.Unknown

    def openScope(self):
        if self.scopes is None:
            self.scopes = list()
        self.scopes.insert(0, {})

    def closeScope(self):
        if self.scopes is not None:
            if len(self.scopes) > 0:
                self.scopes = self.scopes[1:]

    def insert(self, item, name):
        if len(self.scopes) > 0:
            scope = self.scopes[0]
            scope[name] = item
        else:
            raise Exception("No scope available to insert into")

