package main

import (
	"log"
)

const (
	IN_CODE = iota
	IN_DATA
)

type VarDesc struct {
	name	string
	T	*TypeDesc
}

type CG struct {
	in   int
	vars []*VarDesc
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

func (cg *CG) FetchVar(v *VarDesc) {
	cg.InCode()
	log.Printf("    LIT _%s", v.name)
  switch {
  case v.T.kind & IntKind != 0:
    log.Printf("    FWM")
  case v.T.kind & ByteKind != 0:
    log.Printf("    FBM")
  }
}

func (cg *CG) DeclareInt(name string) {
	cg.InData()
	log.Printf("_%s: DCW 0", name)
	vd := &VarDesc {
		name: name,
		T: findTypeDesc("int"),
	}
	cg.vars = append(cg.vars, vd)
}

func (cg *CG) DeclareByte(name string) {
	cg.InData()
	log.Printf("_%s: DCB 0", name)
	vd := &VarDesc {
		name: name,
		T: findTypeDesc("byte"),
	}
	cg.vars = append(cg.vars, vd)
}

func (cg *CG) DeclareFunc(name string) {
	cg.InCode()
	log.Printf("_%s:", name)
}

func (cg *CG) EmitReturn() {
	log.Printf("    RFS")
}
