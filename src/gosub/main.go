package main

import (
	"flag"
	"fmt"
	"io"
	"log"
	"os"
)

// TypeDesc describes a type at a relatively lower level.
type TypeDesc struct {
	name string
	size int
	kind int
}

const (
	VoidKind = 1 << iota
	IntKind
	ByteKind
)

var types []*TypeDesc

// The complete set of tokens this language supports.
type Token interface{}

// Some tokens can be used to denote entire statements.
type Statementer interface {
	ParseStatement(*Tokenizer) error
}

// Some tokens can also be used as infix operators.
type Infixer interface {
	ParseInfix(*Tokenizer) error
}

// Some tokens can be used to start an expression.
type Expressioner interface {
	ParseExpression(*Tokenizer) error
}

// Specific kinds of tokens hold state/data relevant to them.

type tokChar struct {
	ch byte
}

type tokPlus struct {
}

type tokComma struct {
}

type tokSemi struct {
}

type tokOpenBrace struct {
}

type tokCloseBrace struct {
}

type tokId struct {
	name string
}

type tokType struct {
	T *TypeDesc
}

type tokVAR struct {
}

type tokFUNC struct {
}

type tokRETURN struct {
}

type tokSpace struct {
	space []byte
}

type tokVar struct {
	name string
}

type tokFunc struct {
	name    string
	returns *tokType
}

// How tokens of various types handle being used as infix operators.

func (t *tokPlus) ParseInfix(tt *Tokenizer) error {
	tt.Next()
	err := skipSpaces(tt)
	if err != nil {
		return err
	}
	err = tt.getExpression()
	if err != nil {
		return err
	}
	tt.cg.Add()
	return err
}

// How tokens of various types handle being used in an expression.

func IllegalExpression(t Token) error {
	return fmt.Errorf("Illegal expression token: %#v", t)
}

func (t *Tokenizer) getExpression() error {
	e, isExpr := t.Token.(Expressioner)
	if !isExpr {
		return IllegalExpression(t.Token)
	}
	return e.ParseExpression(t)
}

func (t *tokSemi) ParseExpression(tt *Tokenizer) error {
	tt.Next()
	return nil
}

func (t *tokVar) ParseExpression(tt *Tokenizer) error {
	tt.cg.FetchVar(t.name)
	tt.Next()
	return nil
}

// How tokens of various types handle being used as a statement.

func IllegalStatement(t Token) error {
	return fmt.Errorf("Illegal statement token: %#v", t)
}

func (t *Tokenizer) doStatement() error {
	s, isStmt := t.Token.(Statementer)
	if !isStmt {
		return IllegalStatement(t.Token)
	}
	return s.ParseStatement(t)
}

func (t *tokSemi) ParseStatement(tt *Tokenizer) error {
	tt.Next()
	return nil
}

func (t *tokVAR) ParseStatement(tt *Tokenizer) error {
	tt.Next() // eat "var"

	names := make([]string, 0)
	for tt.Error == nil {
		_, ok := tt.Token.(*tokSemi)
		if ok {
			tt.Next()
			break
		}

		id, ok := tt.Token.(*tokId)
		if ok {
			names = append(names, id.name)
			tt.Next()
			continue
		}

		_, ok = tt.Token.(*tokComma)
		if ok {
			tt.Next()
			continue
		}

		tn, ok := tt.Token.(*tokType)
		if ok {
			switch tn.T.name {
			case "int":
				for _, n := range names {
					tt.cg.DeclareInt(n)
				}
			case "byte":
				for _, n := range names {
					tt.cg.DeclareByte(n)
				}
			}
			tt.Next()
			continue
		}

		_, ok = tt.Token.(*tokSpace)
		if ok {
			tt.Next()
			continue
		}
	}

	return tt.Error
}

func skipSpaces(tt *Tokenizer) error {
	_, isWS := tt.Token.(*tokSpace)
	for isWS && (tt.Error == nil) {
		tt.Next()
		_, isWS = tt.Token.(*tokSpace)
	}
	return tt.Error
}

func getId(tt *Tokenizer) (string, error) {
	err := skipSpaces(tt)
	if err != nil {
		return "", err
	}

	i, isId := tt.Token.(*tokId)
	if !isId {
		return "", fmt.Errorf("Expected function name; got %#v", tt.Token)
	}
	tt.Next()
	return i.name, nil
}

func getOptType(tt *Tokenizer) (*tokType, error) {
	err := skipSpaces(tt)
	if err != nil {
		return nil, err
	}

	t, isType := tt.Token.(*tokType)
	if !isType {
		return nil, nil
	}
	tt.Next()
	return t, nil
}

func expectOpenBrace(tt *Tokenizer) error {
	err := skipSpaces(tt)
	if err != nil {
		return err
	}
	_, brace := tt.Token.(*tokOpenBrace)
	if !brace {
		return fmt.Errorf("Syntax error: expected {, but got %#v", tt.Token)
	}
	tt.Next() // eat "{"
	return nil
}

func expectCloseBrace(tt *Tokenizer) error {
	err := skipSpaces(tt)
	if err != nil {
		return err
	}
	_, brace := tt.Token.(*tokCloseBrace)
	if !brace {
		return fmt.Errorf("Syntax error: expected }, but got %#v", tt.Token)
	}
	tt.Next() // eat "}"
	return nil
}

func (t *tokFUNC) ParseStatement(tt *Tokenizer) error {
	tt.Next() // eat "func"

	funcName, err := getId(tt)
	if err != nil {
		return err
	}
	_, err = getOptType(tt)
	err = expectOpenBrace(tt)
	if err != nil {
		return err
	}
	tt.cg.DeclareFunc(funcName)
	for tt.Error == nil {
		err := skipSpaces(tt)
		if err != nil {
			return err
		}
		_, isEnd := tt.Token.(*tokCloseBrace)
		if isEnd {
			break
		}
		err = tt.doStatement()
		if err != nil {
			return err
		}
	}
	err = expectCloseBrace(tt)
	if err != nil {
		return err
	}
	tt.cg.EmitReturn()
	return tt.Error
}

func (t *tokRETURN) ParseStatement(tt *Tokenizer) error {
	tt.Next() // eat "return"

	err := skipSpaces(tt)
	if err != nil {
		return err
	}
	_, isSemi := tt.Token.(*tokSemi)
	if !isSemi {
		err := tt.getExpression()
		if err != nil {
			return err
		}
		for {
			err := skipSpaces(tt)
			if err != nil {
				return err
			}
			i, isInfix := tt.Token.(Infixer)
			if !isInfix {
				break
			}
			err = i.ParseInfix(tt)
			if err != nil {
				return err
			}
		}
	}
	_, isSemi = tt.Token.(*tokSemi)
	if !isSemi {
		return fmt.Errorf("Semicolon expected after expression in RETURN statement")
	}
	tt.Next() // eat ";"
	return nil
}

// Tokenizer is a state machine which takes raw source input and produces one or more Tokens as output.
type Tokenizer struct {
	// Unit represents the current source file (compilation "unit").
	Unit io.Reader
	// Byte is the next byte from the source file, assuming Error == nil.  Undefined otherwise.
	Byte []byte
	// Error records the most recent error encountered when processing the source file.
	Error error
	// Token is the most recently read token.
	Token
	// cg is the code generator used to maintain the symbol table with.
	cg *CG
}

// NewTokenizer creates a new tokenizing state machine instance.
func NewTokenizer(unit io.Reader, cg *CG) (*Tokenizer, error) {
	tokenizer := &Tokenizer{
		Unit: unit,
		Byte: make([]byte, 1),
		cg:   cg,
	}
	tokenizer.NextByte()
	tokenizer.Next()
	return tokenizer, tokenizer.Error
}

// recognizeIdentifier attempts to classify the kind of identifier token you received.
func recognizeIdentifier(id *tokId, cg *CG) Token {
	switch id.name {
	case "var":
		return &tokVAR{}
	case "func":
		return &tokFUNC{}
	case "return":
		return &tokRETURN{}

	default:
		for _, t := range types {
			if t.name == id.name {
				return &tokType{T: t}
			}
		}
		for _, v := range cg.vars {
			if v == id.name {
				return &tokVar{name: id.name}
			}
		}
		return id
	}
}

// readIdentifier will return a single identifier token.
// Beware: the identifier returned may be a never-before-seen identifier, a previously defined/declared identifier, or even a keyword.
// This function makes no attempt to distinguish between these.
// See also recognizeIdentifier().
func (t *Tokenizer) readIdentifier() *tokId {
	name := make([]byte, 1)
	name[0] = t.Byte[0]
	for t.Error == nil {
		t.NextByte()
		if !stillIdentifier(t.Byte[0]) {
			break
		}
		name = append(name, t.Byte[0])
	}
	return &tokId{name: string(name)}
}

// readWhitespace will return a single whitespace token containing all available whitespace until the next token.
func (t *Tokenizer) readWhitespace() *tokSpace {
	spaces := make([]byte, 1)
	spaces[0] = t.Byte[0]
	for t.Error == nil {
		t.NextByte()
		if !isWhitespace(t.Byte[0]) {
			break
		}
		spaces = append(spaces, t.Byte[0])
	}
	return &tokSpace{space: spaces}
}

// NextByte reads in the next byte from the input stream.
// This does not affect the current setting for Token.
func (t *Tokenizer) NextByte() {
	n := 0
	n, t.Error = t.Unit.Read(t.Byte)
	if t.Error != nil {
		return
	}
	if n != 1 {
		t.Error = fmt.Errorf("Expected to read 1 character; got %d", n)
	}
}

// Next reads in the next token from the input stream.
func (t *Tokenizer) Next() {
	if t.Error != nil {
		return
	}
	switch {
	case startsIdentifier(t.Byte[0]):
		t.Token = t.readIdentifier()
		t.Token = recognizeIdentifier(t.Token.(*tokId), t.cg)
	case isWhitespace(t.Byte[0]):
		t.Token = t.readWhitespace()
	case t.Byte[0] == '{':
		t.Token = &tokOpenBrace{}
		t.NextByte()
	case t.Byte[0] == '}':
		t.Token = &tokCloseBrace{}
		t.NextByte()
	case t.Byte[0] == ',':
		t.Token = &tokComma{}
		t.NextByte()
	case t.Byte[0] == '+':
		t.Token = &tokPlus{}
		t.NextByte()
	case t.Byte[0] == ';':
		t.Token = &tokSemi{}
		t.NextByte()
	default:
		t.Token = &tokChar{ch: t.Byte[0]}
		t.NextByte()
	}
}

// Character class utilities.

func startsIdentifier(b byte) bool {
	return (('a' <= b) && (b <= 'z')) || (('A' <= b) && (b <= 'Z')) || (b == '_')
}

func stillIdentifier(b byte) bool {
	return startsIdentifier(b) || (('0' <= b) && (b <= '9'))
}

func isWhitespace(b byte) bool {
	return b <= 0x20
}

// compile will compile a single translation unit, expressed as an io.Reader.
// The compiled translation unit will be returned as a single tokUnit token.
func compile(unit io.Reader, cg *CG) error {
	tok, err := NewTokenizer(unit, cg)
	if err != nil {
		return err
	}
	for tok.Error == nil {
		tok.Error = skipSpaces(tok)
		if tok.Error != nil {
			break
		}
		tok.Error = tok.doStatement()
		if tok.Error != nil {
			break
		}
	}
	if tok.Error == io.EOF {
		return nil
	}
	return tok.Error
}

// compileFile will compile a single file, identified by filename.
func compileFile(filename string, cg *CG) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()
	return compile(file, cg)
}

func main() {
	types = make([]*TypeDesc, 3)
	types[0] = &TypeDesc{
		name: "void",
		size: 0,
		kind: VoidKind,
	}
	types[1] = &TypeDesc{
		name: "int",
		size: 2,
		kind: IntKind,
	}
	types[2] = &TypeDesc{
		name: "byte",
		size: 1,
		kind: ByteKind,
	}
	flag.Parse()
	sources := flag.Args()
	if len(sources) < 1 {
		log.Fatal("At least one source file is required.")
	}
	cg := &CG{}
	for _, s := range sources {
		err := compileFile(s, cg)
		if err != nil {
			log.Fatalf("%s: %s", os.Args[0], err)
		}
	}
}
