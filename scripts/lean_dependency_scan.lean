import AlgebraicCombinatorics
import Lean
import Lean.Util.FoldConsts

open Lean

def nameStartsWith (prefix : Name) (name : Name) : Bool :=
  prefix.isPrefixOf name

def moduleOf? (env : Environment) (name : Name) : Option Name :=
  match env.getModuleIdxFor? name with
  | some idx => env.allImportedModuleNames[idx]?
  | none => none

def kindOfConstant : ConstantInfo → String
  | .axiomInfo _ => "axiom"
  | .defnInfo _ => "def"
  | .thmInfo _ => "theorem"
  | .opaqueInfo _ => "opaque"
  | .quotInfo _ => "quot"
  | .inductInfo _ => "inductive"
  | .ctorInfo _ => "constructor"
  | .recInfo _ => "recursor"

def sortedNames (set : NameSet) : Array Name :=
  let mut names := #[]
  for name in set do
    names := names.push name
  names.qsort fun left right => Name.quickLt left right

def jsonNames (names : Array Name) : Json :=
  toJson (names.map toString)

def classifyUsedConstants (env : Environment) (self : Name) (used : NameSet) :
    Array Name × Array Name × Array Name :=
  let mut mathlib := #[]
  let mut project := #[]
  let mut other := #[]
  for usedName in sortedNames used do
    if usedName == self then
      continue
    match moduleOf? env usedName with
    | some moduleName =>
        if nameStartsWith `Mathlib moduleName then
          mathlib := mathlib.push usedName
        else if nameStartsWith `AlgebraicCombinatorics moduleName then
          project := project.push usedName
        else
          other := other.push usedName
    | none =>
        other := other.push usedName
  (mathlib, project, other)

def emitDecl (env : Environment) (name : Name) (info : ConstantInfo) : IO Unit := do
  let moduleName := moduleOf? env name |>.map toString |>.getD ""
  let used := info.getUsedConstantsAsSet
  let (mathlib, project, other) := classifyUsedConstants env name used
  let line := Json.mkObj [
    ("declaration", toJson name),
    ("kind", toJson (kindOfConstant info)),
    ("module", toJson moduleName),
    ("used_mathlib", jsonNames mathlib),
    ("used_project", jsonNames project),
    ("used_other", jsonNames other),
    ("used_mathlib_count", toJson mathlib.size),
    ("used_project_count", toJson project.size),
    ("used_other_count", toJson other.size)
  ]
  IO.println line.compress

def main (_args : List String) : IO UInt32 := do
  let env ← importModules #[{ module := `AlgebraicCombinatorics }] {}
  for (name, info) in env.constants do
    match moduleOf? env name with
    | some moduleName =>
        if nameStartsWith `AlgebraicCombinatorics moduleName then
          emitDecl env name info
    | none => pure ()
  return 0
