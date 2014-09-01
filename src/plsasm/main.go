// Assembler for the Pulsar processor architecture.
package main

import (
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"strconv"
	"strings"
)

const (
	// Not really a token, but indicates we've reached the end of our input.
	EofKind = 1 + iota

	// CharKind captures all other characters that one could find in the input stream.
	CharKind

	// NameKind identifies unknown names.
	NameKind

	// NumberKind identifies all signed integers.
	NumberKind

	// LDAKind, et. al. represent opcodes
	LDAKind
	STAKind
	ISZKind
	DSZKind
	JMPKind
	JSRKind
)

type Token struct {
	Kind int
	Str  string
	I    int64
	B    byte
}

type Lexer struct {
	Source   io.Reader
	NextChar []byte
	Token
	Line  int
	Error error
}

type Label struct {
	Name     string
	Location int
}

var (
	statementHandlers map[int]func(*Lexer)
	leds              map[int]func(*Lexer) int64
	labels            []Label
	forwards          []Label
	loc               int
)

func isWhitespace(b byte) bool {
	return b < 33 // assumes ASCII
}

func isNewLine(b byte) bool {
	return b == 10 // assumes ASCII, Unix
}

func (l *Lexer) EatByte() {
	if l.Error != nil {
		return
	}
	_, l.Error = l.Source.Read(l.NextChar)
}

func (l *Lexer) SkipComment() {
	l.EatByte() // Eat ;
	for {
		if l.NextChar[0] == '\n' {
			break
		}
		l.EatByte()
	}
}

func (l *Lexer) SkipWhitespace() {
	for {
		if l.Error != nil {
			return
		}
		if l.NextChar[0] == ';' {
			l.SkipComment()
		}
		if !isWhitespace(l.NextChar[0]) {
			return
		}
		if isNewLine(l.NextChar[0]) {
			l.Line++
		}
		l.EatByte()
	}
}

func isStartOfName(b byte) bool {
	return (('A' <= b) && (b <= 'Z')) || (('a' <= b) && (b <= 'z')) || (b == '_')
}

func isNameChar(b byte) bool {
	return isStartOfName(b) || (('0' <= b) && (b <= '9'))
}

func (l *Lexer) lexName() {
	name := make([]byte, 1)
	name[0] = l.NextChar[0]
	l.EatByte()
	for {
		if l.Error != nil {
			return
		}
		if !isNameChar(l.NextChar[0]) {
			break
		}
		name = append(name, l.NextChar[0])
		l.EatByte()
	}
	l.Token.Kind = NameKind
	l.Token.Str = string(name)
	switch strings.ToLower(l.Token.Str) {
	case "lda":
		l.Token.Kind = LDAKind
	case "sta":
		l.Token.Kind = STAKind
	case "isz":
		l.Token.Kind = ISZKind
	case "dsz":
		l.Token.Kind = DSZKind
	case "jmp":
		l.Token.Kind = JMPKind
	case "jsr":
		l.Token.Kind = JSRKind
	}
}

func isDecimalDigit(b byte) bool {
	return ('0' <= b) && (b <= '9')
}

func isHexDigit(b byte) bool {
	return (('a' <= b) && (b <= 'f')) || (('A' <= b) && (b <= 'F'))
}

func isDigit(b byte) bool {
	return isDecimalDigit(b) || isHexDigit(b) || (b == 'x') || (b == 'X')
}

func (l *Lexer) lexNumber() {
	name := make([]byte, 1)
	name[0] = l.NextChar[0]
	l.EatByte()
	for {
		if l.Error != nil {
			return
		}
		if !isDigit(l.NextChar[0]) {
			break
		}
		name = append(name, l.NextChar[0])
		l.EatByte()
	}
	l.Token.Kind = NumberKind
	l.Token.Str = string(name)
	l.Token.I, l.Error = strconv.ParseInt(l.Token.Str, 0, 16)
}

func (l *Lexer) Next() {
	l.Token.Kind = 0
	l.SkipWhitespace()
	if l.Error != nil {
		if l.Error == io.EOF {
			l.Token.Kind = EofKind
		}
		return
	}
	nc := l.NextChar[0]
	switch {
	case isStartOfName(nc):
		l.lexName()
	case isDecimalDigit(nc):
		l.lexNumber()
	default:
		l.Token.Kind = CharKind
		l.Token.Str = string(l.NextChar)
		l.Token.B = nc
		l.EatByte()
	}
}

func NewLexer(s io.Reader) *Lexer {
	l := &Lexer{
		Source:   s,
		NextChar: []byte{10},
	}
	l.Next()
	return l
}

func handleLabel(l *Lexer) {
	labels = append(labels, Label{
		Name: l.Token.Str,
		Location: loc,
	})
	ff := make([]Label, 0)
	for _, f := range forwards {
		if f.Name != l.Token.Str {
			ff = append(ff, f)
		} else {
			log.Printf("Resolving forward reference to %s at %04X", f.Name, f.Location)
		}
	}
	forwards = ff
	l.Next()
}

func (l *Lexer) parseEffectiveAddress() (int64, int64) {
	handler, supported := leds[l.Token.Kind]
	if !supported {
		l.Error = fmt.Errorf("%d: Effective Address expression expected at \"%s\"", l.Line, l.Token.Str)
		return -1, -1
	}
	displacement := handler(l)
	if l.Error != nil {
		return -1, -1
	}
	indexReg := int64(1)	// Default to PC
	if (l.Token.Kind == CharKind) && (l.Token.B == ',') {
		l.Next()
		handler, supported = leds[l.Token.Kind]
		if !supported {
			l.Error = fmt.Errorf("%d: Index register expression expected at \"%s\"", l.Line, l.Token.Str)
			return -1, -1
		}
		indexReg = handler(l)
		if l.Error != nil {
			return -1, -1
		}
	}
	if (indexReg < 0) || (indexReg > 3) {
		l.Error = fmt.Errorf("%d: Index register must be 0, 1, 2, or 3.", l.Line)
		return -1, -1
	}
	return displacement, indexReg
}

func handleLDA(l *Lexer) {
	l.Next()
	handler, supported := leds[l.Token.Kind]
	if !supported {
		l.Error = fmt.Errorf("%d: Destination register expression expected at \"%s\"", l.Line, l.Token.Str)
		return
	}
	destReg := handler(l)
	if l.Error != nil {
		return
	}
	if (destReg < 0) || (destReg > 3) {
		l.Error = fmt.Errorf("%d: Destination register must be 0, 1, 2, or 3.", l.Line)
		return
	}
	if (l.Token.Kind != CharKind) || (l.Token.B != ',') {
		l.Error = fmt.Errorf("%d: Comma followed by effective Address expression expected at \"%s\"", l.Line, l.Token.Str)
		return
	}
	l.Next()
	displacement, indexReg := l.parseEffectiveAddress()
	if l.Error != nil {
		return
	}
	log.Printf("%04X LDA AC%d, %d, %s", loc, destReg, displacement, ([]string{"0", "PC", "AC2", "AC3"})[indexReg])
	loc++
}

func handleJMP(l *Lexer) {
	l.Next()
	displacement, indexReg := l.parseEffectiveAddress()
	if l.Error != nil {
		return
	}
	log.Printf("%04X JMP %d, %s", loc, displacement, ([]string{"0", "PC", "AC2", "AC3"})[indexReg])
	loc++
}

func handleNumber(l *Lexer) int64 {
	n := l.Token.I
	l.Next()
	return n
}

func handleForwardRef(l *Lexer) int64 {
	forwards = append(forwards, Label{
		Name:     l.Token.Str,
		Location: loc,
	})
	l.Next()
	return 0
}

func assemble(s io.Reader) error {
	labels = make([]Label, 0)
	forwards = make([]Label, 0)

	statementHandlers = map[int]func(*Lexer){
		NameKind: handleLabel,
		LDAKind:  handleLDA,
		JMPKind:  handleJMP,
	}

	leds = map[int]func(*Lexer) int64{
		NumberKind: handleNumber,
		NameKind:   handleForwardRef,
	}

	loc = 0
	l := NewLexer(s)
	for {
		if l.Error != nil {
			return l.Error
		}
		handler, supported := statementHandlers[l.Token.Kind]
		if !supported {
			return fmt.Errorf("%d: Unknown directive or opcode at \"%s\"", l.Line, l.Token.Str)
		}
		handler(l)
	}
}

func main() {
	flag.Parse()

	files := flag.Args()
	if len(files) < 1 {
		log.Fatal("Expected a file to assemble.")
	}
	if len(files) > 1 {
		log.Print("Ignoring additional arguments.")
	}
	s, err := os.Open(files[0])
	if err != nil {
		log.Fatal(err)
	}
	defer s.Close()
	err = assemble(s)
	if err != nil {
		log.Fatal(err)
	}
}
