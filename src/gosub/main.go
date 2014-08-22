package main

import (
	"flag"
	"fmt"
	"io"
	"log"
	"os"
)

// Keywords
var keywords = []string{
  "var", "func", "return",
}

// Token represents the "union type" of all kinds of tokens that can be found in the source file(s).
type Token interface{
  ParseStatement(*tokUnit) error
}

type tokChar struct {
	ch byte
}

type tokPlus struct {
}

type tokComma struct {
}

type tokId struct {
	name string
}

type tokVAR struct {
}

type tokSpace struct {
	space []byte
}

type tokUnit struct {
	vars []tokVar
	funcs []tokFunc
}

type tokVar struct {
}

type tokFunc struct {
}

// How tokens of various types handle being used as a statement.

func IllegalStatement(t Token) error {
  return fmt.Errorf("Illegal statement token: %#v", t)
}

func (t *tokChar) ParseStatement(_ *tokUnit) error {
  return IllegalStatement(t)
}

func (t *tokPlus) ParseStatement(_ *tokUnit) error {
  return IllegalStatement(t)
}

func (t *tokComma) ParseStatement(_ *tokUnit) error {
  return IllegalStatement(t)
}

func (t *tokId) ParseStatement(_ *tokUnit) error {
  return IllegalStatement(t)
}

func (t *tokSpace) ParseStatement(_ *tokUnit) error {
  // whitespace does nothing in the statement context.
  return nil
}

func (t *tokUnit) ParseStatement(_ *tokUnit) error {
  return IllegalStatement(t)
}

func (t *tokVar) ParseStatement(_ *tokUnit) error {
  return IllegalStatement(t)
}

func (t *tokFunc) ParseStatement(_ *tokUnit) error {
  return IllegalStatement(t)
}

func (t *tokVAR) ParseStatement(_ *tokUnit) error {
  return IllegalStatement(t)
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
}

// NewTokenizer creates a new tokenizing state machine instance.
func NewTokenizer(unit io.Reader) (*Tokenizer, error) {
	tokenizer := &Tokenizer{
		Unit: unit,
		Byte: make([]byte, 1),
	}
	tokenizer.NextByte()
	tokenizer.Next()
	return tokenizer, tokenizer.Error
}

// isKeyword yields true if the identifier named is really a keyword of the language.
func isKeyword(name string) bool {
  for _, x := range keywords {
    if name == x {
      return true
    }
  }
  return false
}

// recognizeIdentifier attempts to classify the kind of identifier token you received.
func recognizeIdentifier(id *tokId) Token {
  switch id.name {
  case "var":
    return &tokVAR{}
  default:
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
    t.Token = recognizeIdentifier(t.Token.(*tokId))
	case isWhitespace(t.Byte[0]):
		t.Token = t.readWhitespace()
	case t.Byte[0] == ',':
		t.Token = &tokComma{}
		t.NextByte()
	case t.Byte[0] == '+':
		t.Token = &tokPlus{}
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
func compile(unit io.Reader) (Token, error) {
	program := &tokUnit{
		vars: make([]tokVar, 0),
		funcs: make([]tokFunc, 0),
	}
	tok, err := NewTokenizer(unit)
	if err != nil {
		return nil, err
	}
	for tok.Error == nil {
		err := tok.Token.ParseStatement(program)
		if err != nil {
			return nil, err
		}
	}
	if tok.Error == io.EOF {
		return program, nil
	}
	return program, tok.Error
}

// compileFile will compile a single file, identified by filename.
func compileFile(filename string) (Token, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	return compile(file)
}

func main() {
	flag.Parse()
	sources := flag.Args()
	if len(sources) < 1 {
		log.Fatal("At least one source file is required.")
	}
	for _, s := range sources {
		_, err := compileFile(s)
		if err != nil {
			log.Fatalf("%s: %s", os.Args[0], err)
		}
	}
}
