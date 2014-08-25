package main

import (
	"log"
)

const (
	IN_CODE = iota
	IN_DATA
)

type CG struct {
	in   int
	vars []string
}

func (cg *CG) InData() {
	if cg.in != IN_DATA {
		log.Printf("    .DATA")
		cg.in = IN_DATA
	}
}

func (cg *CG) InCode() {
	if cg.in != IN_CODE {
		log.Printf("    .CODE")
		cg.in = IN_CODE
	}
}

func (cg *CG) Add() {
	cg.InCode()
	log.Printf("    ADD")
}

func (cg *CG) FetchVar(name string) {
	cg.InCode()
	log.Printf("    LIT _%s", name)
	log.Printf("    FWM")
}

func (cg *CG) DeclareInt(name string) {
	cg.InData()
	log.Printf("_%s: DCW 0", name)
	cg.vars = append(cg.vars, name)
}

func (cg *CG) DeclareByte(name string) {
	cg.InData()
	log.Printf("_%s: DCB 0", name)
	cg.vars = append(cg.vars, name)
}

func (cg *CG) DeclareFunc(name string) {
	cg.InCode()
	log.Printf("_%s:", name)
}

func (cg *CG) EmitReturn() {
	log.Printf("    RFS")
}
