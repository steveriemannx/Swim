# swim implementation notes

This document is for developers who want to modify the swim compiler or
runtime.

## Compilation pipeline

```
swimc/cli.py
  ├─ modules.py   : import resolution → multi-file project (dependency order,
  │                 merged AST, line offsets)
  ├─ lexer.py     : source → token stream (with string interpolation parts)
  ├─ parser.py    : token stream → AST (ast_nodes.py)
  ├─ types.py     : AST → Registry (types/members/functions/aliases/extensions)
  ├─ codegen.py   : Registry + AST → Nim source + line mapping
  └─ nim compiler : Nim source + runtime/swimrt.nim → native executable
```

Entry point: `bin/swim` → `src/swimc/main.py` → `swimc.cli:main`.

### 1. Lexer (`lexer.py`)

- Emits `Token(kind, value, line, col)` with kinds
  `ident/keyword/number/string/op/punct/eof`.
- String literals are split into `parts`: `("text", str)` or
  `("expr", source, line, col)`; interpolation expressions are parsed
  recursively by the parser.
- Comments (`//`, nested `/* */`) and multiline-string dedenting are handled in
  the lexer.
- No newline tokens are produced; the few line-sensitive places (such as a bare
  `return`) use the token's `line`.

### 1.5 Module loading (`modules.py`)

- `load_project(entry)` starts at the entry file and resolves every `import`:
  - built-in module names (`Foundation`, `Swift`, `Math`, ...) → no-op;
  - otherwise search for `<Name>.sw` or `<Name>/main.sw` in "importing file
    directory → entry file directory → cwd → `SWIM_PATH`";
  - report an error listing the search locations when not found.
- Dependencies are collected in post-order (dependencies before dependents);
  each file is loaded once. Import cycles are safely cut by first-visit order.
- Merging concatenates each file's `top_items` and rewrites every AST node's
  `line` with the file's line offset. A `line_owner` table (composed line →
  real file + line) is built for diagnostics.
- Validation: duplicate types/global variables/same-signature functions across
  files are errors; only the entry file may declare `@main`.
- `Project` stores file order, the merged AST, `line_owner`, per-file source
  text and the import graph. `swim deps` uses this information directly.

### 2. Parser (`parser.py`)

- Recursive descent plus Pratt expression parsing (Swift precedence table in
  `PREC`).
- Dedicated functions for type parsing, generic parameters/constraints,
  closure signatures and patterns (`switch` cases, `catch`).
- Declarations and statements have separate entry points; type members
  (`struct/class/enum/protocol/extension`) each have their own member loop.
- Backtracking (`Backtrack` exception) implements generic inference for
  `Box<Int>(...)` and `Box<Int>.case(...)`.
- Top-level declarations/statements are kept in source order in
  `Module.top_items` (execution order depends on it).

### 3. Type system and symbol tables (`types.py`)

- `Ty`: an immutable type representation (`kind` + `name` + `args` + `labels`)
  covering integers/floats/strings/arrays/dictionaries/optionals/tuples/
  closures/named types/generic parameters/ranges/types.
- `Registry`:
  - Two passes over the module build `TypeInfo` (struct/class/enum/protocol),
    `FuncInfo`, `EnumCaseInfo`, `ComputedProp` and `ExtensionInfo`.
  - Resolves inheritance, protocol constraints, type aliases and extension
    members.
  - Provides queries such as `find_methods` / `find_functions` / `field_type` /
    `resolve_type`, and performs generic substitution (`substitute`).
- Error enums (`enum E: Error`) are recorded with `is_error`; codegen emits the
  exception type hierarchy.

### 4. Code generation (`codegen.py`)

Emission order is fixed:

1. header (version, `import swimrt`)
2. type declarations (structs/classes/enums/protocol concepts/error types/
   aliases)
3. global variable declarations (without initializers)
4. forward declarations for all procedures
5. procedure definitions (free functions, methods, initializers, computed
   properties, static members, extensions, enum helpers, synthesized
   `$`/`==`/`hash`/`allCases`, ...)
6. static variable initialization
7. top-level code (global initialization and top-level statements in source
   order)
8. `@main` entry call

Key designs:

- **Forward declarations**: Nim requires declaration before use, so every proc
  gets a signature first and its body later. Default parameter values are
  emitted on the declaration and omitted on the definition.
- **Naming**: `nim_ident()` handles Nim keyword/runtime symbol collisions with
  a `sw_` prefix. User type names that collide with Nim names get a `Swim`
  prefix. Static methods, constructors and enum constructors use names such as
  `Type_method`, `newType`, `Type_case` to avoid collisions.
- **Structs**: `object`; `mutating` methods take `self: var T`.
- **Classes**: `ref object of RootObj`. Covered methods with inheritance
  generate an "impl proc + method wrapper" pair to support dynamic dispatch and
  static `super.method()` calls.
- **Enums**: no associated values → `{.pure.} enum`; associated values → kind
  enum + variant object; recursive enums automatically use
  `ref object of RootObj`; string raw values generate `rawValue`/`fromRaw`.
- **Protocols**: generate Nim concepts (method/property requirements); protocol
  extensions generate generic procs constrained by the concept.
- **Optional chaining**: `a?.b?.c` compiles to nested `swimOptFlatMap` template
  calls (defined by the runtime).
- **`if let` / `guard let`**: generate a temporary plus `isSome` checks and
  `get`.
- **Pattern matching**: `switch` compiles to an `if` chain guarded by a
  `swMatched` flag; enum associated values are only read after the condition
  succeeds, avoiding variant-object field access errors.
- **Top-level order**: global variables are declared first (so procs can
  reference them); initialization and top-level statements execute in
  `top_items` order, matching Swift's top-level execution order.
- **Error mapping**: `CodeGen.line_map` records generated Nim line → composed
  line; `Project.line_owner` maps composed lines back to (module file, local
  line), and `cli.translate_nim_errors` /
  `Project.normalize_codegen_error` print the correct module snippet.
- **Closures**: single-expression closures generate `{.closure.}` proc
  literals; multi-statement closures generate proc literals with bodies.
  Higher-order trailing closures prefer the It-template path (`mapIt`, etc.).

### 5. Compiler CLI (`cli.py`)

- Subcommands `run/build/check/emit/new/deps/test`; plain `swim file.sw` is
  equivalent to `run`.
- Generated files and binaries are cached in the system temp directory under
  `swim-build-cache/src-<hash>`. The cache key includes the paths and sources of
  **all** project modules (any change recompiles), the compiler version, the
  runtime source hash, Nim flags and the memory-management mode.
- `deps` reuses `modules.Project` to print the import graph and dependency
  execution order.
- Nim subprocess: `nim c --mm:arc --hints:off --warnings:off --path:<runtime>`.
  `--mm:arc` is the fixed memory-management strategy (ARC, no tracing GC); the
  `NIM_MEMORY_MANAGEMENT` constant in `cli.py` also participates in the cache
  key.

## Memory management

- Generated programs are always compiled with `--mm:arc`: class instances use
  reference counting and are released immediately when the count reaches zero.
- Nim ref-object cycles are not collected (ARC has no cycle collector), which
  matches Swift ARC. The runtime does not introduce a GC.
- Value types (`struct`/`enum`) do not involve reference counting; recursive
  enums are represented with `ref`, so they are ARC-managed.

## Runtime (`runtime/swimrt.nim`)

- Re-exports `options`, `tables`, `sequtils`, `strutils`, `math`, `algorithm`,
  `sets`, `hashes`, `os`, etc.
- Defines the Swift-style API: `swimStr` (print formatting), `print`, array/
  string/dictionary helpers, optional helpers, `swimOptFlatMap`, sort
  templates, stride iterators, protocol concepts, character classification,
  hash/exception helpers, etc.
- Changing the runtime changes the cache key of generated programs, so they
  recompile automatically.

## How to extend

### Add a standard-library method

1. Add a `proc`/`template` to `runtime/swimrt.nim` (avoid name collisions with
   existing symbols).
2. Register it in the corresponding place in `codegen.py`:
   - collection/string methods → `_array_method`, `_string_method`,
     `_dict_method`, `_set_method`, `_numeric_method`, `_optional_method`;
   - properties → `code_builtin_property`;
   - static members/constructors → `code_prim_static_member`,
     `code_prim_static_call`, `code_builtin_type_construct`;
   - global functions → `code_builtin_free_call`.
3. Add `tests/cases/*.sw` plus expected output, then run
   `python3 tests/run_tests.py`.

### Add a built-in module

1. Implement/wrap the functionality in `runtime/swimrt.nim` and `export` the
   Nim modules you need.
2. Register the module name in `modules.BUILTIN_MODULES` (`Foundation`, etc.
   live there).
3. If the module name needs extra compiler support (special static members,
   for example), implement it in `codegen.py`.
4. Add a test that imports the module name and compiles.

### Add a language feature

1. AST: add nodes in `ast_nodes.py`.
2. Parsing: produce the nodes in the appropriate parser functions.
3. Types/symbols (if needed): extend `types.py`.
4. Generation: implement in `codegen.py`'s `gen_expr`/`gen_stmt` or the
   specific declaration generator.
5. Forward declarations/naming: check whether a new `ProcJob` or helper
   procedure is needed.
6. Tests: cover at least the success path, the error path and interactions
   with existing features.

## Test framework

`tests/run_tests.py`:

- `tests/cases/*.sw`: single-file success programs; stdout is compared with
  `tests/expected/<name>.out`.
- `tests/projects/<name>/main.sw`: multi-file projects; expected output is
  `tests/expected/<name>.out`.
- `tests/errors/*.sw` and `tests/errors/<name>/main.sw`: expected compile
  failures; the first line of `tests/errors/<name>.err` must appear in the
  compiler output.
- Runs in parallel (`--jobs`); `--filter` filters and `--update` regenerates
  expected output.
- Tests use `bin/swim run` (the full compile + run pipeline).

## Known implementation trade-offs

- Nim's `method` dynamic dispatch and `super` are implemented with impl procs
  plus wrappers, so `swim emit` contains method pairs for class methods.
- The `swimOptFlatMap` template evaluates the outer expression once (saved in a
  temporary); pure expressions are unaffected. If the base of an optional chain
  has side effects, store it in a variable first.
- Multi-line closures in argument position generate multi-line Nim; Nim's
  parenthesis indentation rules are covered by tests.
- Top-level variable types must be inferable from their initializer, otherwise
  an explicit annotation is required.
- Recursive enums use `ref` representation and therefore have reference
  semantics (Swift recursive enums usually use `indirect`), and are managed by
  ARC.
- Reference cycles are not collected automatically (matching Swift ARC).
- Multi-file modules merge into a single Nim module: declarations share one
  flat namespace, and duplicate types/global variables across files are errors;
  functions are de-duplicated by signature. Imported modules' top-level
  statements run before the entry file.
- Module resolution is path-based (no package manager/download): it searches
  the importing file's directory, entry directory, cwd and `SWIM_PATH`; local
  `.sw` files take precedence over built-in module names.

## License

This project is released under the MIT License (see `LICENSE`) and is an
independent implementation: it uses no code from the official Swift repository
or the Swift standard library.
