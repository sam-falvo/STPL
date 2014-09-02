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
	"encoding/binary"
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

	// Pseudo-opcodes
	DCWKind
	DCBKind
)

type Token struct {
	Kind int
	Str  string
	I    int64
	B    byte
}

type Image struct {
	I []uint16
	P int
}

func (i *Image) AsmWord(w uint16) error {
	if i.P < len(i.I) {
		i.I[i.P] = w
		i.P++
		return nil
	}
	return fmt.Errorf("Attempt to assemble more than %d bytes", len(i.I))
}

type Lexer struct {
	Source   io.Reader
	NextChar []byte
	Token
	Line  int
	Error error
	Image
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
		if l.Error != nil {
			break
		}
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
	keywords := map[string]int{
		"lda": LDAKind,
		"sta": STAKind,
		"isz": ISZKind,
		"dsz": DSZKind,
		"jmp": JMPKind,
		"jsr": JSRKind,
		"dcw": DCWKind,
	}
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
	k, ok := keywords[strings.ToLower(l.Token.Str)]
	if ok {
		l.Token.Kind = k
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
	l.Token.I, l.Error = strconv.ParseInt(l.Token.Str, 0, 0)
}

func (l *Lexer) Next() {
	if l.Token.Kind == EofKind {
		l.Error = io.EOF
		return
	}
	l.Token.Kind = 0
	l.SkipWhitespace()
	if l.Error != nil {
		if l.Error == io.EOF {
			l.Token.Kind = EofKind
			l.Error = nil
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
		Image: Image{
			I: make([]uint16, 65536),
		},
	}
	l.Next()
	return l
}

func handleLabel(l *Lexer) {
	labels = append(labels, Label{
		Name: l.Token.Str,
		Location: l.Image.P,
	})
	ff := make([]Label, 0)
	for _, f := range forwards {
		if f.Name != l.Token.Str {
			ff = append(ff, f)
		} else {
      hi := l.Image.I[f.Location] & 0xFF00
      lo := (l.Image.I[f.Location] + uint16(l.Image.P)) & 0x00FF
      l.Image.I[f.Location] = hi | lo
		}
	}
	forwards = ff
	l.Next()
}

func (l *Lexer) parseEffectiveAddress() (int64, int64) {
	displacement := l.parseExpression("Effective address")
	if l.Error != nil {
		return -1, -1
	}
	indexReg := int64(1)	// Default to PC
	if (l.Token.Kind == CharKind) && (l.Token.B == ',') {
		l.Next()
		indexReg = l.parseExpression("Index register")
		if l.Error != nil {
			return -1, -1
		}
	} else {
		// No explicit base register specified; assume PC-relative addressing given absolute symbol value.
		displacement = displacement - int64(l.Image.P + 1)
	}
	if (indexReg < 0) || (indexReg > 3) {
		l.Error = fmt.Errorf("%d: Index register must be 0, 1, 2, or 3.", l.Line)
		return -1, -1
	}
  log.Printf("Returning %d(%d)", displacement, indexReg)
	return displacement, indexReg
}

func (l *Lexer) parseExpression(kind string) int64 {
	handler, supported := leds[l.Token.Kind]
	if !supported {
		l.Error = fmt.Errorf("%d: %s expression expected at \"%s\"", l.Line, kind, l.Token.Str)
		return -1
	}
	value := handler(l)
	if l.Error != nil {
		return -1
	}
	return value
}

func (l *Lexer) RequireComma(something string) {
	if (l.Token.Kind != CharKind) || (l.Token.B != ',') {
		l.Error = fmt.Errorf("%d: Comma followed by %s expected at \"%s\"", l.Line, something, l.Token.Str)
		return
	}
	l.Next()
}

func (l *Lexer) PeekComma() bool {
	if (l.Token.Kind == CharKind) && (l.Token.B == ',') {
		l.Next()
		return true
	}
	return false
}

func handleLDA(l *Lexer) {
	l.Next()
	destReg := l.parseExpression("Destination register")
	if l.Error != nil {
		return
	}
	if (destReg < 0) || (destReg > 3) {
		l.Error = fmt.Errorf("%d: Destination register must be 0, 1, 2, or 3.", l.Line)
		return
	}
	l.RequireComma("effective address expression")
	if l.Error != nil {
		return
	}
	displacement, indexReg := l.parseEffectiveAddress()
	if l.Error != nil {
		return
	}
	if displacement < -128 {
		l.Error = fmt.Errorf("%d: Displacement out of range (less than -128)", l.Line)
		return
	}
	if displacement > 127 {
		l.Error = fmt.Errorf("%d: Displacement out of range (greater than 127)", l.Line)
		return
	}
	l.Error = l.Image.AsmWord(uint16(0x2000 | (destReg << 11) | (indexReg << 8) | (displacement & 0xFF)))
}

func handleSTA(l *Lexer) {
	l.Next()
	srcReg := l.parseExpression("Source register")
	if l.Error != nil {
		return
	}
	if (srcReg < 0) || (srcReg > 3) {
		l.Error = fmt.Errorf("%d: Source register must be 0, 1, 2, or 3.", l.Line)
		return
	}
	l.RequireComma("effective address expression")
	if l.Error != nil {
		return
	}
	displacement, indexReg := l.parseEffectiveAddress()
	if l.Error != nil {
		return
	}
	if displacement < -128 {
		l.Error = fmt.Errorf("%d: Displacement out of range (less than -128)", l.Line)
		return
	}
	if displacement > 127 {
		l.Error = fmt.Errorf("%d: Displacement out of range (greater than 127)", l.Line)
		return
	}
	l.Error = l.Image.AsmWord(uint16(0x4000 | (srcReg << 11) | (indexReg << 8) | (displacement & 0xFF)))
}

func handleJMP(l *Lexer) {
	l.Next()
	displacement, indexReg := l.parseEffectiveAddress()
	if l.Error != nil {
		return
	}
	if displacement < -128 {
		l.Error = fmt.Errorf("%d: Displacement out of range (less than -128)", l.Line)
		return
	}
	if displacement > 127 {
		l.Error = fmt.Errorf("%d: Displacement out of range (greater than 127)", l.Line)
		return
	}
	l.Error = l.Image.AsmWord(uint16((indexReg << 8) | (displacement & 0xFF)))
}

func handleNumber(l *Lexer) int64 {
	n := l.Token.I
	l.Next()
	return n
}

func handleForwardRef(l *Lexer) int64 {
	for _, lab := range labels {
		if lab.Name == l.Token.Str {
			return int64(lab.Location)
		}
	}
	forwards = append(forwards, Label{
		Name:     l.Token.Str,
		Location: l.Image.P,
	})
	l.Next()
	return 0
}

func handleDCW(l *Lexer) {
	l.Next()
	for {
		l.Error = l.Image.AsmWord(uint16(l.parseExpression("An")))
		if l.Error != nil {
			break
		}
		if l.Token.Kind == EofKind {
			break
		}
		if !l.PeekComma() {
			break
		}
	}
}

func assemble(s io.Reader) (*Image, error) {
	labels = make([]Label, 0)
	forwards = make([]Label, 0)

	statementHandlers = map[int]func(*Lexer){
		NameKind: handleLabel,
		LDAKind:  handleLDA,
		STAKind:  handleSTA,
		JMPKind:  handleJMP,
		DCWKind:  handleDCW,
	}

	leds = map[int]func(*Lexer) int64{
		NumberKind: handleNumber,
		NameKind:   handleForwardRef,
	}

	l := NewLexer(s)
	for {
		if l.Token.Kind == EofKind {
			break
		}
		if l.Error != nil {
			return nil, l.Error
		}
		handler, supported := statementHandlers[l.Token.Kind]
		if !supported {
			return nil, fmt.Errorf("%d: Unknown directive or opcode at \"%s\"", l.Line, l.Token.Str)
		}
		handler(l)
	}
	if len(forwards) != 0 {
		unique := make(map[string]bool)
		log.Printf("Unresolved references:")
		for _, f := range forwards {
			if !unique[f.Name] {
				log.Printf("   %s", f.Name)
				unique[f.Name] = true
			}
		}
		return nil, fmt.Errorf("Please resolve unresolved references.")
	}
	return &l.Image, nil
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
	img, err := assemble(s)
	if err != nil {
		log.Fatal(err)
	}
	f, err := os.Create("a.out")
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()
	err = binary.Write(f, binary.BigEndian, img.I[:img.P])
	if err != nil {
		log.Fatal(err)
	}
}
