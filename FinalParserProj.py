import sys
import re

try:

    import pytoken
except ImportError:
    pytoken = None

if 1:

    # building the table to hold the symbols

    symbol_table = {}

    class symbol_base(object):

        id = None
        value = None
        first = second = third = None

        def nud(self):
            raise SyntaxError("Syntax error (%r)." % self.id)

        def led(self, left):
            raise SyntaxError("Unknown operator (%r)." % self.id)
    #the function that builds the structure of the parse trees
        def __repr__(self):
            if self.id == "(name)" or self.id == "(literal)":
                return "(%s %s)" % (self.id[1:-1], self.value)
            out = [self.id, self.first, self.second, self.third]
            out = map(str, filter(None, out))
            return "(" + " ".join(out) + ")"
    #the function that takes in a token and assigns its binding power to the table
    def symbol(id, bp=0):
        try:
            s = symbol_table[id]
        except KeyError:
            class s(symbol_base):
                pass
            s.__name__ = "symbol-" + id
            s.id = id
            s.value = None
            s.lbp = bp
            symbol_table[id] = s
        else:
            s.lbp = max(bp, s.lbp)
        return s

    # helpers
    #function that handles the left follow sets and their precedence
    def infix(id, bp):
        def led(self, left):
            self.first = left
            self.second = expression(bp)
            return self
        symbol(id, bp).led = led
    #function that handles the right follow sets and their precedence
    def infix_r(id, bp):
        def led(self, left):
            self.first = left
            self.second = expression(bp-1)
            return self
        symbol(id, bp).led = led
    #function that handles the first sets and their precedence
    def prefix(id, bp):
        def nud(self):
            self.first = expression(bp)
            return self
        symbol(id).nud = nud
    #function that pushes on to the next token
    def advance(id=None):
        global token
        if id and token.id != id:
            raise SyntaxError("Expected %r" % id)
        token = next()

    def method(s):
        # decorator
        assert issubclass(s, symbol_base)
        def bind(fn):
            setattr(s, fn.__name__, fn)
        return bind

    # python expression syntax to handle lambda functions that python creates
    symbol("lambda", 20)

    #operators that will populate the symbol table with their precedence
    infix_r("or", 30); infix_r("and", 40); prefix("not", 50)
    infix("in", 60); infix("not", 60) # not in
    infix("is", 60);
    infix("<", 60); infix("<=", 60)
    infix(">", 60); infix(">=", 60)
    infix("!=", 60); infix("==", 60)
    infix("|", 70); infix("^", 80); infix("&", 90)
    infix("+", 110); infix("-", 110)
    infix("*", 120); infix("/", 120); infix("//", 120)
    infix("%", 120)
    prefix("-", 130); prefix("+", 130); prefix("~", 130)
    infix_r("**", 140)

    symbol("(", 150)

    #using the lambda to handle returns of names and literals because they are symbols not operators
    symbol("(name)").nud = lambda self: self
    symbol("(literal)").nud = lambda self: self
    symbol("(end)")
    symbol(")")

    #function to tell program how to handle parentheses
    @method(symbol("("))
    def nud(self):
        # parenthesized form; replaced by tuple former below
        expr = expression()
        advance(")")
        return expr

    symbol(")"); symbol(",")

    @method(symbol("("))
    def led(self, left):
        self.first = left
        self.second = []
        if token.id != ")":
            while 1:
                self.second.append(expression())
                if token.id != ",":
                    break
                advance(",")
        advance(")")
        return self

    #specific function to tell program what values to return based on literals
    def constant(id):
        @method(symbol(id))
        def nud(self):
            self.id = "(literal)"
            self.value = id
            return self
    constant("None")
    constant("True")
    constant("False")

    # multitoken operators given tokens and test multiple functions in order to return accurate values
    @method(symbol("not"))
    def led(self, left):
        if token.id != "in":
            raise SyntaxError("Invalid syntax")
        advance()
        self.id = "not in"
        self.first = left
        self.second = expression(60)
        return self

    @method(symbol("is"))
    def led(self, left):
        if token.id == "not":
            advance()
            self.id = "is not"
        self.first = left
        self.second = expression(60)
        return self

    # displays to commandline
    @method(symbol("("))
    def nud(self):
        self.first = []
        comma = False
        if token.id != ")":
            while 1:
                if token.id == ")":
                    break
                self.first.append(expression())
                if token.id != ",":
                    break
                comma = True
                advance(",")
        advance(")")
        if not self.first or comma:
            return self # tuple
        else:
            return self.first[0]

    # built in python tokenizer
    def tokenize_python(program):
        import tokenize
        from cStringIO import StringIO
        type_map = {
            tokenize.NUMBER: "(literal)",
            tokenize.STRING: "(literal)",
            tokenize.OP: "(operator)",
            tokenize.NAME: "(name)",
            }
        for t in tokenize.generate_tokens(StringIO(program).next):
            try:
                yield type_map[t[0]], t[1]
            except KeyError:
                if t[0] == tokenize.NL:
                    continue
                if t[0] == tokenize.ENDMARKER:
                    break
                else:
                    raise SyntaxError("Syntax error")
        yield "(end)", "(end)"
    #using python's tokenizer with our program
    def tokenize(program):
        if isinstance(program, list):
            source = program
        else:
            source = tokenize_python(program)
        for id, value in source:
            if id == "(literal)":
                symbol = symbol_table[id]
                s = symbol()
                s.value = value
            else:
                # name or operator
                symbol = symbol_table.get(value)
                if symbol:
                    s = symbol()
                elif id == "(name)":
                    symbol = symbol_table[id]
                    s = symbol()
                    s.value = value
                else:
                    raise SyntaxError("Unknown operator (%r)" % id)
            yield s

    # parser, the algorithm that python is using to parse the given expression
    def expression(rbp=0):
        global token
        t = token
        token = next()
        left = t.nud()
        while rbp < token.lbp:
            t = token
            token = next()
            left = t.led(left)
        return left

    def parse(program):
        global token, next
        next = tokenize(program).next
        token = next()
        return expression()
    #program to run the parser
    def test(program):
        print ">>>", program
        print parse(program)




# samples
#test("+1")
#test("-1")
#test("1+2")
#test("1+2+3")
#test("1+2*3")
test(raw_input('Enter a string: '))
