package main

import (
  "fmt"
  "flag"
  "log"
  "io"
  "os"
)

type Tokenizer struct {
  Unit io.Reader
  Byte []byte
  Error error
  Token
}

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

func NewTokenizer(unit io.Reader) (*Tokenizer, error) {
  tokenizer := &Tokenizer{
    Unit: unit,
    Byte: make([]byte, 1),
  }
  tokenizer.NextByte()
  tokenizer.Next()
  return tokenizer, tokenizer.Error
}

func startsIdentifier(b byte) bool {
  return (('a' <= b) && (b <= 'z')) || (('A' <= b) && (b <= 'Z')) || (b == '_')
}

func stillIdentifier(b byte) bool {
  return startsIdentifier(b) || (('0' <= b) && (b <= '9'))
}

func startsWhitespace(b byte) bool {
  return b <= 0x20
}

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

func (t *Tokenizer) readWhitespace() *tokSpace {
  spaces := make([]byte, 1)
  spaces[0] = t.Byte[0]
  for t.Error == nil {
    t.NextByte()
    if !startsWhitespace(t.Byte[0]) {
      break
    }
    spaces = append(spaces, t.Byte[0])
  }
  return &tokSpace{spaces}
}

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

func (t *Tokenizer) Next() {
  if t.Error != nil {
    return
  }
  switch {
  case startsIdentifier(t.Byte[0]):
    t.Token = t.readIdentifier()
  case startsWhitespace(t.Byte[0]):
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

