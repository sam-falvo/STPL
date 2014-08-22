package main

import (
	"flag"
	"fmt"
	"io"
	"log"
	"os"
)

var types = []string{
  "int", "byte",
}

// Token represents the "union type" of all kinds of tokens that can be found in the source file(s).
type Token interface{
  ParseStatement(*tokUnit, *Tokenizer) error
}

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
  name string
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

type tokUnit struct {
	vars []tokVar
	funcs []tokFunc
}

type tokVar struct {
  names []string
  typename string
}

type tokFunc struct {
  name string
  returns *tokType
}

// How tokens of various types handle being used as a statement.

func IllegalStatement(t Token) error {
  return fmt.Errorf("Illegal statement token: %#v", t)
}

func (t *tokChar) ParseStatement(_ *tokUnit, _ *Tokenizer) error {
  return IllegalStatement(t)
}

func (t *tokPlus) ParseStatement(_ *tokUnit, _ *Tokenizer) error {
  return IllegalStatement(t)
}

func (t *tokComma) ParseStatement(_ *tokUnit, _ *Tokenizer) error {
  return IllegalStatement(t)
}

func (t *tokOpenBrace) ParseStatement(_ *tokUnit, _ *Tokenizer) error {
  return IllegalStatement(t)
}

func (t *tokCloseBrace) ParseStatement(_ *tokUnit, _ *Tokenizer) error {
  return IllegalStatement(t)
}

func (t *tokSemi) ParseStatement(_ *tokUnit, tt *Tokenizer) error {
  tt.Next()
  return nil
}

func (t *tokType) ParseStatement(_ *tokUnit, _ *Tokenizer) error {
  return IllegalStatement(t)
}

func (t *tokId) ParseStatement(_ *tokUnit, _ *Tokenizer) error {
  return IllegalStatement(t)
}

func (t *tokSpace) ParseStatement(_ *tokUnit, tt *Tokenizer) error {
  tt.Next()
  return nil
}

func (t *tokUnit) ParseStatement(_ *tokUnit, _ *Tokenizer) error {
  return IllegalStatement(t)
}

func (t *tokVar) ParseStatement(_ *tokUnit, _ *Tokenizer) error {
  return IllegalStatement(t)
}

func (t *tokFunc) ParseStatement(_ *tokUnit, _ *Tokenizer) error {
  return IllegalStatement(t)
}

func (t *tokVAR) ParseStatement(u *tokUnit, tt *Tokenizer) error {
  tt.Next() // eat "var"

  tv := tokVar{
    names: make([]string, 0),
  }

  for (tt.Error == nil) {
    _, ok := tt.Token.(*tokSemi)
    if ok {
      tt.Next()
      break
    }

    id, ok := tt.Token.(*tokId)
    if ok {
      tv.names = append(tv.names, id.name)
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
      tv.typename = tn.name
      tt.Next()
      continue
    }

    _, ok = tt.Token.(*tokSpace)
    if ok {
      tt.Next()
      continue
    }
  }

  if len(tv.names) > 0 {
    u.vars = append(u.vars, tv)
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
  typ := &tokType{}

  err := skipSpaces(tt)
  if err != nil {
    return typ, err
  }

  t, isType := tt.Token.(*tokType)
  if !isType {
    return typ, nil
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

func (t *tokFUNC) ParseStatement(u *tokUnit, tt *Tokenizer) error {
  tt.Next() // eat "func"

  funcName, err := getId(tt)
  if err != nil {
    return err
  }
  funcType, err := getOptType(tt)
  err = expectOpenBrace(tt)
  if err != nil {
    return err
  }
	for tt.Error == nil {
    err := skipSpaces(tt)
    if err != nil {
      return err
    }
    _, isEnd := tt.Token.(*tokCloseBrace)
    if isEnd {
      break
    }
		err = tt.Token.ParseStatement(u, tt)
		if err != nil {
			return err
		}
	}
  err = expectCloseBrace(tt)
  if err != nil {
    return err
  }
  u.funcs = append(u.funcs, tokFunc{name: funcName, returns: funcType})
  return tt.Error
}

func (t *tokRETURN) ParseStatement(u *tokUnit, tt *Tokenizer) error {
  tt.Next() // eat "return"

  err := skipSpaces(tt)
  if err != nil {
    return err
  }
  _, isSemi := tt.Token.(*tokSemi)
  for !isSemi {
    tt.Next()
    _, isSemi = tt.Token.(*tokSemi)
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

// recognizeIdentifier attempts to classify the kind of identifier token you received.
func recognizeIdentifier(id *tokId) Token {
  switch id.name {
  case "var":
    return &tokVAR{}
  case "func":
    return &tokFUNC{}
  case "return":
    return &tokRETURN{}

  case "int":
    fallthrough
  case "byte":
    return &tokType{name: id.name}

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
    err := skipSpaces(tok)
    if (err != nil) && (err != io.EOF) {
      return nil, err
    }
		err = tok.Token.ParseStatement(program, tok)
		if (err != nil) && (err != io.EOF) {
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
		o, err := compileFile(s)
		if err != nil {
			log.Fatalf("%s: %s", os.Args[0], err)
		}
    log.Printf("Output\n\n%#v", o)
	}
}
