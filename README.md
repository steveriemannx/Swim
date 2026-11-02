# swim

**swim** is a programming language that uses **Swift syntax** and compiles to
**Nim** for execution. Source files use the `.sw` extension.

> Design goal: **write Swift syntax only — never mix in Nim**. Every token in a
> `.sw` file is Swift-style; Nim is only the invisible execution backend. The
> generated Nim is readable and inspectable (`swim emit`), but you never need
> to (and should not) edit it directly.

```swift
// Every swim program starts executing at its top-level statements.
let language = "swim"
let backend = "Nim"

func greet(_ name: String) -> String {
    return "Hello, \(name)!"
}

print(greet(language))
print("Swift syntax, \(backend) backend.")
```

```console
$ swim run examples/hello.sw
Hello, swim!
Swift syntax, Nim backend.
```

Repository: <https://github.com/steveriemannx/Swim>

---

## Table of contents

- [Features](#features)
- [Independent implementation](#independent-implementation)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Language tour](#language-tour)
- [Swift types → Nim types](#swift-types--nim-types)
- [Runtime API](#runtime-api)
- [Modules and library imports](#modules-and-library-imports)
- [How it works](#how-it-works)
- [Memory management (ARC)](#memory-management-arc)
- [Project layout](#project-layout)
- [Testing](#testing)
- [Differences from Swift / limitations](#differences-from-swift--limitations)
- [Editor support](#editor-support)
- [License](#license)

---

## Features

- **Swift syntax**: `let`/`var`, `func`, `struct`/`class`/`enum`/`protocol`/
  `extension`, argument labels, default parameters, closures and trailing
  closures, `$0`, `if let`/`guard let`, optional chaining `?.`/`!`/`??`,
  `switch` pattern matching, `do`/`catch`, `defer`, `@main`, and more.
- **Nim backend**: compiles to native executables with Nim/C-class speed, using
  Nim's **ARC** (automatic reference counting) memory management — no tracing
  GC, no cycle collector.
- **Semantic parity**: structs are value types, classes are reference types;
  enums support associated values, raw values and recursion; protocols map to
  Nim concepts (statically checked); generics are zero-cost.
- **Readable compiler output**: `swim emit` prints commented, indented Nim.
  Compile errors are mapped back to `.sw` source lines with a highlighted
  snippet.
- **Multi-file modules**: `import Foo` resolves `Foo.sw` next to the source or
  on `SWIM_PATH`; modules are compiled together into one executable.
  `swim deps` shows the resolved import graph and execution order.
- **Zero-dependency compiler**: the compiler is pure Python 3 standard library;
  the runtime is a single Nim module.
- **Complete toolchain**: `run` / `build` / `check` / `emit` / `deps` / `new` /
  `test`; build caching makes repeated runs take about 0.1 s.
- **MIT licensed and fully original**: the compiler and runtime are independent
  implementations. No code is included, linked, or copied from the Swift
  repository (swiftlang/swift) or the Swift standard library.

## Independent implementation

swim **does not use any code from the Swift repository (swiftlang/swift) or the
Swift standard library**:

- The compiler in `src/swimc/` is a brand-new Python implementation: lexer,
  recursive-descent/Pratt parser, type system and Nim code generator are all
  original. It does not depend on a Swift toolchain and does not copy Swift
  sources.
- The runtime in `runtime/swimrt.nim` is an original Nim module; generated
  programs only depend on it and the Nim standard library.
- At the language-design level, swim follows Swift's syntax conventions
  (keywords, operator precedence, optional semantics, ...). Those are syntax
  conventions, not Swift implementation code; the repository contains no source
  file, compiler code or standard-library code copied from the Swift project.
- The project is released under the MIT license (see [LICENSE](LICENSE)) and
  contains no Swift project copyright files or third-party Swift code.

The whole repository is: a Python compiler, a Nim runtime, examples, tests,
documentation and editor grammar definitions.

## Installation

Requirements:

1. **Nim 2.x** (including the Nim compiler): <https://nim-lang.org/install.html>
2. **Python 3.9+** (only for the compiler; standard library is enough)

Verify your environment:

```console
$ nim --version
Nim Compiler Version 2.2.12
$ python3 --version
Python 3.14.4
```

Run directly from a checkout (no installation needed):

```console
$ ./bin/swim run examples/hello.sw
```

Install into your `PATH` (creates a symlink in `PREFIX/bin`, default
`/usr/local`):

```console
$ ./install.sh                 # or: PREFIX=$HOME/.local ./install.sh
$ swim version
```

## Quick start

```console
$ swim new hello               # create hello.sw from a template
$ swim run hello.sw            # compile and run
$ swim build hello.sw -o hello # produce a native executable
$ swim emit hello.sw           # inspect the generated Nim source
$ swim check hello.sw          # compile without running
$ swim deps app.sw             # show resolved imports and module order
```

`swim run` passes arguments after `--` to the program (plain arguments after
the file name also work):

```console
$ swim run app.sw one two
```

## Language tour

### Variables and constants

```swift
let name = "swim"        // constant
var count = 3            // variable
count += 1
let ratio: Double = 3.5  // explicit type annotation
```

### Functions

```swift
func greet(name: String, from city: String = "the world") -> String {
    return "Hi \(name) from \(city)"
}

print(greet(name: "Ada"))
print(greet(name: "Ada", from: "Paris"))

func swapValues(_ a: inout Int, _ b: inout Int) { ... }
swapValues(&count, &count)
```

### Structs, classes, enums

```swift
struct Point: Equatable {
    var x: Int
    var y: Int
    func lengthSquared() -> Int { x * x + y * y }
    mutating func move(dx: Int, dy: Int) { x += dx; y += dy }
    static func origin() -> Point { Point(x: 0, y: 0) }
}

class Animal {
    var name: String
    init(name: String) { self.name = name }
    func speak() -> String { "..." }
}
class Dog: Animal {
    override func speak() -> String { "Woof" }
}

enum Shape {
    case circle(radius: Double)
    case point
}
func area(_ shape: Shape) -> Double {
    switch shape {
    case .circle(let radius): return 3.14159 * radius * radius
    case .point: return 0
    }
}
```

### Optionals

```swift
let present: Int? = 5
let missing: Int? = nil
print(present!, present ?? 0)

if let value = present {
    print(value)
}
guard let value = Int("42") else { return }
print(present != nil)

struct Engine { var power: Int }
struct Car { var engine: Engine? }
let car = Car(engine: Engine(power: 300))
print(car.engine?.power ?? 0)
```

### Closures and higher-order functions

```swift
let double = { (value: Int) -> Int in value * 2 }
let numbers = [1, 2, 3, 4, 5]

print(numbers.map { $0 * $0 })
print(numbers.filter { $0 % 2 == 0 })
print(numbers.reduce(0) { $0 + $1 })
print(numbers.sorted { $0 > $1 })
print(numbers.first(where: { $0 > 2 })!)
```

### Error handling

```swift
enum ValidationError: Error {
    case empty
    case tooShort(minimum: Int)
}

func validate(_ password: String) throws -> String {
    if password.isEmpty { throw ValidationError.empty }
    if password.count < 6 {
        throw ValidationError.tooShort(minimum: 6)
    }
    return "ok"
}

do {
    print(try validate("abc123"))
} catch ValidationError.tooShort(let minimum) {
    print("need \(minimum) characters")
} catch {
    print("other error")
}
```

### Generics and protocols

```swift
protocol Shape {
    func area() -> Double
    var name: String { get }
}

extension Shape {
    func describe() -> String { "\(name): \(area())" }
}

struct Square: Shape {
    var side: Double
    var name: String { "square" }
    func area() -> Double { side * side }
}

func largest<T: Comparable>(_ values: [T]) -> T? { ... }

struct Stack<Element> {
    private var items: [Element] = []
    mutating func push(_ item: Element) { items.append(item) }
    mutating func pop() -> Element? { items.popLast() }
}
```

## Swift types → Nim types

| swim (Swift syntax) | generated Nim type | notes |
| --- | --- | --- |
| `Int` / `Int8` … `Int64` | `int` / `int8` … `int64` | signed integers |
| `UInt` … | `uint` … | unsigned integers |
| `Double` / `Float` | `float` / `float32` | floating point |
| `Bool` | `bool` | |
| `String` | `string` | |
| `Character` | `char` | |
| `T?` / `T!` | `Option[T]` | `nil`, `!`, `??` all work |
| `[T]` | `seq[T]` | dynamic array |
| `[K: V]` | `Table[K, V]` | hash table; subscript returns `V?` |
| `Set<T>` | `HashSet[T]` | |
| `(A, B)` / `(x: A, y: B)` | `(A, B)` / `tuple[x: A, y: B]` | |
| `(A) -> B` | `proc (a: A): B {.closure.}` | closure |
| `struct` | `object` (value type) | value semantics |
| `class` (with inheritance) | `ref object of RootObj` (reference type) | dynamic dispatch via Nim `method` |
| `enum` (no associated values) | `{.pure.} enum` | |
| `enum` (associated values) | kind enum + variant object | recursive enums automatically use `ref` |
| `enum E: Error` | exception type hierarchy (`CatchableError`) | `throw` / `catch` |
| `protocol` | Nim `concept` constraint + structural checks | generic constraints |
| `extension` | top-level `proc` (with a `self` parameter) | also extends `Int`/`String`/`Array` |
| `typealias` | `type` alias | |
| `@main struct` | generated `main()` call | |

Enum kind/raw values, exception types, `$`, `==`, `hash` and `allCases` helpers
are generated by the compiler.

## Runtime API

`runtime/swimrt.nim` provides a Swift-style standard library (generated code
automatically imports it):

- **Printing**: `print(_:)` (with `separator:` and `terminator:`),
  `debugPrint`, `fatalError`, `assert`, `precondition`, `readLine()`, `exit()`.
- **Strings**: `count`, `isEmpty`, `uppercased/lowercased/capitalized`,
  `hasPrefix/hasSuffix/contains`, `split(separator:)`,
  `components(separatedBy:)`, `joined(separator:)`,
  `replacingOccurrences(of:with:)`, `trimmingCharacters(in:)`,
  `prefix/suffix/dropFirst/dropLast`, `reversed()`, `index(of:)`,
  `firstIndex(of:)`, `first/last`, string repetition initializers.
- **Characters**: `isNumber/isLetter/isWhitespace/isUppercase/isLowercase`,
  `wholeNumberValue`, case conversion.
- **Arrays**: `count/isEmpty/first/last`, `append/insert/remove/removeFirst/
  removeLast/removeAll(where:)/popLast`, `contains`, `first(where:)`,
  `firstIndex(where:)/(of:)`, `map/filter/reduce/forEach/allSatisfy`,
  `sorted/sorted(by:)/sort`, `reversed/enumerated/min/max/swapAt`,
  `prefix/suffix/dropFirst/dropLast`, `joined`.
- **Dictionaries**: `count/isEmpty/keys/values`, `updateValue(_:forKey:)`,
  `removeValue(forKey:)`, `sorted(by:)`.
- **Sets**: `count/isEmpty/insert/remove/contains`.
- **Numbers**: `description`, `isMultiple(of:)`, `squareRoot()`, `rounded()`,
  `Int.max/min`, `Double.pi/infinity/nan`, `Int.random(in:)`,
  `abs/min/max/pow/sqrt/floor/ceil/round/sin/cos/...`.
- **Optionals**: `!`, `??`, `if let`, `guard let`, `?.`, `map`, `flatMap`.
- **Ranges**: `a..<b`, `a...b`, `stride(from:to:by:)`,
  `stride(from:through:by:)`.

## Modules and library imports

Imports come in three layers. **Only Swift syntax is ever used; no Nim code is
imported into `.sw` files.**

### 1. Built-in modules (zero cost, provided by the runtime)

The following module names are accepted and treated as no-ops (the `swimrt`
runtime already provides the corresponding Swift-style API):

```swift
import Foundation
import Swift
import Glibc        // also Darwin / Dispatch / ObjectiveC
import Math         // also Strings / Collections / Random / Time
```

`Foundation` etc. exist for source compatibility with Swift; swim does not
emulate the complete Foundation/Cocoa APIs (there is no `URLSession` or
`JSONDecoder`, for example).

### 2. swim modules (the recommended way)

`import Foo` / `import Foo.Bar` resolves to a **`.sw` source file**:

```swift
// MathX.sw
func triple(_ value: Int) -> Int { value * 3 }

// Greeter.sw
import MathX

struct Greeter {
    var name: String
    func greet() -> String { "Hi \(name), triple=\(triple(name.count))" }
}

// main.sw
import Greeter
print(Greeter(name: "swim").greet())
print(triple(7))
```

```console
$ swim run main.sw
Hi swim, triple=12
21
```

Resolution rules:

- `import Foo` → `Foo.sw` or `Foo/main.sw`
- `import Foo.Bar` → `Foo/Bar.sw` or `Foo/Bar/main.sw`
- Search order: **directory of the importing file → entry file directory →
  current working directory → `SWIM_PATH` (colon-separated list of
  directories)**
- A local `.sw` file takes precedence over a built-in module name (so you can
  shadow names like `Math`).
- There is no package manager or dependency download: modules are source files
  placed in one of the search locations.

Compilation model:

- All imported modules and the entry file are **merged into one program** and
  compiled together.
- Top-level statements of imported modules run **dependencies first** (each
  module runs at most once), then the entry file's top-level statements. Import
  cycles expand deterministically by first-load order.
- Declarations share one flat namespace; declaring the same type, global
  variable or function signature in two different files is a compile error.
  Same-name functions with different signatures are overloads.
- Only the entry file may declare `@main`.

Inspect the resolved graph and execution order:

```console
$ swim deps main.sw
module import graph for main.sw (execution order, dependencies first):
  1. MathX.sw
  2. Greeter.sw
     imports: MathX -> MathX.sw
  3. main.sw  (entry)
     imports: Greeter -> Greeter.sw
```

### 3. Nim ecosystem libraries (not directly supported)

Because swim's hard constraint is "**Swift syntax only, no mixing with Nim**",
a `.sw` file **cannot** contain `import std/xxx`, `importcpp`, pragmas, or any
other Nim code, so it cannot directly import arbitrary Nim libraries. When you
need a new library capability there are two controlled extension paths:

1. Wrap the Nim library in `runtime/swimrt.nim` and expose it under a built-in
   module name.
2. Extend the swim compiler/runtime with Swift-style declarations (see "How to
   extend" in [docs/internals.md](docs/internals.md)).

This guarantees that every `.sw` file contains only Swift syntax; Nim lives
exclusively in the invisible backend and runtime.

## How it works

```
 .sw source files (one or more; imports resolved first)
   │  modules.py   resolve imports, load dependencies, merge ASTs
   │  lexer.py     tokenize Swift syntax (including string interpolation)
   │  parser.py    recursive descent → AST
   │  types.py     collect types/functions/members, build symbol tables
   │  codegen.py   emit Nim (with line mapping and helper procedures)
   ▼
 .nim file ──► Nim compiler ──► native executable (linked with swimrt)
```

- Generated programs always have the same structure: type declarations →
  global variables → forward declarations → procedure definitions → top-level
  statements in source order (including global initialization).
- Swift's optional chaining `a?.b?.c` becomes `swimOptFlatMap`; `if let` /
  `guard let` become `Option` `isSome`/`get` checks; enum pattern matching
  becomes guarded `if` chains.
- Programs are always compiled with `--mm:arc` (ARC). Nim compile errors are
  mapped back to `.sw` line numbers, for example:

```console
$ swim run broken.sw
broken.sw:1:14: error: expected parameter name, found '->'

   1 | func broken( -> Int {
                    ^
```

Actual `swim emit examples/hello.sw` output (excerpt):

```nim
import swimrt

var language: string
var backend: string

language = "swim"
backend = "Nim"
swimPrint(swimStr("Hello, " & swimStr(language) & "!"))
swimPrint(swimStr("Swift syntax, " & swimStr(backend) & " backend."))
```

## Memory management (ARC)

Every swim program uses **ARC (Automatic Reference Counting)**:

- The compiler always invokes Nim with `--mm:arc` (see
  `NIM_MEMORY_MANAGEMENT` in `src/swimc/cli.py`). Generated binaries contain
  **no** tracing garbage collector and no Nim ORC cycle collector.
- `class` instances are ARC-managed references; `struct`/`enum` are value types
  and are copied by value.
- As with Swift ARC, **reference cycles are not collected automatically**. If
  two classes hold strong references to each other (for example
  `parent`/`children`), break the cycle manually (set one side to `nil` or
  redesign).
- `weak` / `unowned` are parsed today but do not yet generate weak-reference
  semantics; avoid cycles instead.
- Values captured by closures are also ARC-managed.

## Project layout

```
swim/
├── bin/swim                  # launcher (Python compiler entry point)
├── src/swimc/                # compiler (Python, standard library only)
│   ├── lexer.py              # lexer
│   ├── parser.py             # recursive-descent parser
│   ├── modules.py            # import resolution / multi-file merging
│   ├── ast_nodes.py          # AST nodes
│   ├── types.py              # type system / symbol tables / registry
│   ├── codegen.py            # Nim code generation
│   ├── cli.py                # command line interface
│   └── errors.py             # diagnostics
├── runtime/swimrt.nim        # swim runtime + Swift-style standard library
├── tests/                    # end-to-end tests (20 programs + 15 error cases)
│   ├── run_tests.py
│   ├── cases/                # single-file .sw programs
│   ├── projects/             # multi-file projects (main.sw + modules)
│   ├── expected/             # expected output
│   └── errors/               # expected compile failures
├── examples/                 # getting-started examples
├── docs/                     # language reference and implementation notes
├── editors/vscode/swim/      # VS Code syntax highlighting extension
├── install.sh
├── LICENSE                   # MIT
└── README.md
```

## Testing

```console
$ python3 tests/run_tests.py            # run all end-to-end tests in parallel
$ python3 tests/run_tests.py -v         # more detail
$ python3 tests/run_tests.py --filter optional
$ python3 tests/run_tests.py --update   # regenerate expected output
$ swim test                             # same, from the repository
```

Currently **35/35 tests pass**, covering: basic types and control flow,
functions and closures, optionals, collections, structs, classes and
inheritance, enums and pattern matching, protocols and generics, error
handling, string APIs, `@main`, multi-file module imports, plus 15 compile
error diagnostics.

## Differences from Swift / limitations

swim is not a complete implementation of Swift, nor a Swift compiler. Explicit
limitations:

- **No mixing with Nim**: you cannot write Nim inside `.sw` files (no
  `importcpp`, no `{.pragma.}`, ...). To add capabilities, extend the runtime or
  the compiler instead of inlining Nim.
- **Not supported** (they produce compile errors or are ignored): `subscript`,
  custom operators, `associatedtype` / generic protocols, `async`/`await`
  (keywords are ignored), `#if` conditional compilation, `fallthrough`,
  property observers `willSet`/`didSet` (ignored), failable `init?`, dynamic
  protocol existentials (`any P` as a variable type), `Any` type erasure, and
  Cocoa/Foundation APIs (`import Foundation` is accepted and ignored).
- **String subscripts use integers** (`text[0]` returns a `Character`) rather
  than Swift's `String.Index`.
- **Protocols** are checked statically via Nim concepts; generic functions and
  structs with `T: Protocol` work well, but heterogeneous protocol arrays
  (`[any Shape]`) are not supported.
- **Integer division**: `/` between integers generates `div` (truncating
  toward zero) and `%` generates `mod`.
- **Print formatting** is close to Swift but not identical: `Optional(5)`,
  arrays as `[1, 2]`, structs as `Point(x: 1, y: 2)`, classes print their name
  by default.
- Recursive enums use reference representation automatically (Nim cannot inline
  recursive objects), so recursive enums have reference semantics.
- ARC memory management: reference cycles are not collected automatically;
  `weak`/`unowned` have no semantics yet.
- **No package manager**: modules are source files resolved from directories /
  `SWIM_PATH`; dependencies are never downloaded automatically.
- **No direct Nim ecosystem imports**: `.sw` files may not contain Nim code
  (see the extension paths above).
- Declarations across modules share a flat namespace; duplicate same-name
  types/global variables/same-signature functions in different files are
  compile errors (same-name overloads with different signatures are allowed).

## Editor support

`editors/vscode/swim/` contains a VS Code extension (syntax highlighting,
bracket matching, indentation rules):

```console
$ cd editors/vscode/swim
$ code --extensionDevelopmentPath="$(pwd)"
```

`editors/vscode/swim/syntaxes/swim.tmLanguage.json` is a standard TextMate
grammar and also works with Sublime Text / TextMate / Zed and other editors.

## License

swim is released under the **MIT License**, see [LICENSE](LICENSE).

Copyright (c) 2026 steveriemannx

This is an independent implementation: no code from the official Swift
repository (swiftlang/swift) or the Swift standard library is used.
