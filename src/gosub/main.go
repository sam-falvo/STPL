package main

import (
	"flag"
	"fmt"
	"io"
	"log"
	"os"
)

// Token represents the "union type" of all kinds of tokens that can be found in the source file(s).
type Token interface{}

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

type tokSpace struct {
	space []byte
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
	return &tokId{string(name)}
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
	return &tokSpace{spaces}
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
	case isWhitespace(t.Byte[0]):
		t.Token = t.readWhitespace()
	case t.Byte[0] == ',':
		t.Token = &tokComma{}
		t.NextByte()
	case t.Byte[0] == '+':
		t.Token = &tokPlus{}
		t.NextByte()
	default:
		t.Token = &tokChar{t.Byte[0]}
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
func compile(unit io.Reader) error {
	tok, err := NewTokenizer(unit)
	if err != nil {
		return err
	}
	for tok.Error == nil {
		log.Printf("Token: %#v", tok.Token)
		tok.Next()
	}
	if tok.Error == io.EOF {
		return nil
	}
	return tok.Error
}

// compileFile will compile a single file, identified by filename.
func compileFile(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
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
		err := compileFile(s)
		if err != nil {
			log.Fatalf("%s: %s", os.Args[0], err)
		}
	}
}
