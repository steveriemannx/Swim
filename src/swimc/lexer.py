"""Lexer for the swim language.

swim uses Swift-style syntax.  This lexer produces a flat token stream that the
parser turns into an AST.  Newlines are not significant tokens (the parser only
uses line numbers for the few places where Swift is line sensitive, such as a
bare ``return``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import SwimError


# Token kinds
IDENT = "ident"
KEYWORD = "keyword"
NUMBER = "number"
STRING = "string"
OP = "op"
PUNCT = "punct"
EOF = "eof"

# Characters that make up a Swift operator token.  Note that ``.`` is *not*
# included: in Swift the dot is punctuation, and ``...`` / ``..<`` are handled
# specially below.
OP_CHARS = set("/=-+!*%<>&|^~?")

# Swift keywords (reserved words).  Contextual keywords are lexed as plain
# identifiers and matched by the parser when needed.
KEYWORDS = {
    "associatedtype", "class", "deinit", "enum", "extension", "fileprivate",
    "func", "import", "init", "inout", "internal", "let", "open", "operator",
    "private", "precedencegroup", "protocol", "public", "rethrows", "static",
    "struct", "subscript", "typealias", "var", "break", "case", "catch",
    "continue", "default", "defer", "do", "else", "fallthrough", "for",
    "guard", "if", "in", "repeat", "return", "throw", "switch", "where",
    "while", "as", "Any", "catch", "false", "is", "nil", "super", "self",
    "Self", "throw", "throws", "true", "try", "async", "await",
}


@dataclass
class Token:
    kind: str
    value: Any
    line: int
    col: int
    # For string literals: list of ("text", str) / ("expr", source, line, col)
    parts: list = field(default_factory=list)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Token({self.kind}, {self.value!r}, {self.line}:{self.col})"

    def is_(self, kind: str, value: str | None = None) -> bool:
        if self.kind != kind:
            return False
        return value is None or self.value == value


class Lexer:
    def __init__(self, src: str, filename: str = "<input>") -> None:
        self.src = src
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []

    # ------------------------------------------------------------------ utils
    def error(self, msg: str, line: int | None = None, col: int | None = None):
        raise SwimError(
            msg,
            filename=self.filename,
            line=self.line if line is None else line,
            col=self.col if col is None else col,
        )

    def peek(self, off: int = 0) -> str:
        i = self.pos + off
        return self.src[i] if i < len(self.src) else ""

    def advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def skip_whitespace(self) -> None:
        while self.pos < len(self.src):
            ch = self.src[self.pos]
            if ch in " \t\r\n\v\f":
                self.advance()
            elif ch == "/" and self.peek(1) == "/":
                while self.pos < len(self.src) and self.src[self.pos] != "\n":
                    self.advance()
            elif ch == "/" and self.peek(1) == "*":
                start_line, start_col = self.line, self.col
                self.advance()
                self.advance()
                depth = 1
                while self.pos < len(self.src) and depth > 0:
                    if self.peek() == "/" and self.peek(1) == "*":
                        self.advance()
                        self.advance()
                        depth += 1
                    elif self.peek() == "*" and self.peek(1) == "/":
                        self.advance()
                        self.advance()
                        depth -= 1
                    else:
                        self.advance()
                if depth > 0:
                    self.error("unterminated block comment", start_line, start_col)
            else:
                return

    # ------------------------------------------------------------------- main
    def tokenize(self) -> list[Token]:
        while self.pos < len(self.src):
            self.skip_whitespace()
            if self.pos >= len(self.src):
                break
            line, col = self.line, self.col
            ch = self.src[self.pos]

            if ch == '"':
                self.lex_string()
                continue
            if ch.isdigit():
                self.lex_number()
                continue
            if ch == "_" or ch.isalpha() or ch == "$" or ch == "`":
                self.lex_ident()
                continue
            if ch in OP_CHARS:
                self.lex_operator()
                continue
            if ch == ".":
                # ``...`` and ``..<`` are range operators, otherwise punctuation
                if self.peek(1) == "." and self.peek(2) == ".":
                    self.advance()
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(OP, "...", line, col))
                elif self.peek(1) == "." and self.peek(2) == "<":
                    self.advance()
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(OP, "..<", line, col))
                else:
                    self.advance()
                    self.tokens.append(Token(PUNCT, ".", line, col))
                continue
            if ch in "(){}[],:;@#\\":
                self.advance()
                self.tokens.append(Token(PUNCT, ch, line, col))
                continue
            self.error(f"unexpected character {ch!r}")

        self.tokens.append(Token(EOF, "", self.line, self.col))
        return self.tokens

    # ---------------------------------------------------------------- pieces
    def lex_ident(self) -> None:
        line, col = self.line, self.col
        if self.peek() == "`":
            self.advance()
            start = self.pos
            while self.pos < len(self.src) and self.src[self.pos] != "`":
                self.advance()
            if self.pos >= len(self.src):
                self.error("unterminated backtick identifier")
            name = self.src[start:self.pos]
            self.advance()  # closing backtick
            self.tokens.append(Token(IDENT, name, line, col))
            return
        if self.peek() == "$":
            # implicit closure parameter: $0, $1, ...
            self.advance()
            start = self.pos
            while self.pos < len(self.src) and self.src[self.pos].isdigit():
                self.advance()
            if start == self.pos:
                self.error("expected digit after '$'")
            self.tokens.append(Token(IDENT, "$" + self.src[start:self.pos], line, col))
            return
        start = self.pos
        while self.pos < len(self.src):
            ch = self.src[self.pos]
            if ch == "_" or ch.isalnum():
                self.advance()
            else:
                break
        name = self.src[start:self.pos]
        kind = KEYWORD if name in KEYWORDS else IDENT
        self.tokens.append(Token(kind, name, line, col))

    def lex_operator(self) -> None:
        line, col = self.line, self.col
        start = self.pos
        while self.pos < len(self.src) and self.src[self.pos] in OP_CHARS:
            # do not swallow a comment starter
            if self.src[self.pos] in "/" and self.peek(1) in "/*":
                if self.pos == start:
                    self.error("unexpected '/'")
                break
            self.advance()
        self.tokens.append(Token(OP, self.src[start:self.pos], line, col))

    def lex_number(self) -> None:
        line, col = self.line, self.col
        start = self.pos
        text = ""
        if self.peek() == "0" and self.peek(1) in "xXbBoO":
            self.advance()
            self.advance()
            while self.pos < len(self.src) and (
                self.src[self.pos].isalnum() or self.src[self.pos] == "_"
            ):
                self.advance()
            text = self.src[start:self.pos]
            self.tokens.append(Token(NUMBER, text, line, col))
            return
        while self.pos < len(self.src) and (
            self.src[self.pos].isdigit() or self.src[self.pos] == "_"
        ):
            self.advance()
        is_float = False
        if self.peek() == "." and self.peek(1).isdigit():
            is_float = True
            self.advance()
            while self.pos < len(self.src) and (
                self.src[self.pos].isdigit() or self.src[self.pos] == "_"
            ):
                self.advance()
        if self.peek() in "eE":
            nxt = self.peek(1)
            if nxt.isdigit() or (nxt in "+-" and self.peek(2).isdigit()):
                is_float = True
                self.advance()
                if self.peek() in "+-":
                    self.advance()
                while self.pos < len(self.src) and self.src[self.pos].isdigit():
                    self.advance()
        text = self.src[start:self.pos]
        self.tokens.append(Token(NUMBER, text, line, col))

    # ---------------------------------------------------------------- strings
    def lex_string(self) -> None:
        line, col = self.line, self.col
        multiline = False
        if self.peek(1) == '"' and self.peek(2) == '"':
            multiline = True
            self.advance()
            self.advance()
            self.advance()
        else:
            self.advance()

        parts: list = []
        buf: list[str] = []

        def flush_text() -> None:
            if buf:
                parts.append(("text", "".join(buf)))
                buf.clear()

        while True:
            if self.pos >= len(self.src):
                self.error("unterminated string literal", line, col)
            ch = self.src[self.pos]

            if ch == '"':
                if multiline:
                    if (
                        self.peek(1) == '"'
                        and self.peek(2) == '"'
                    ):
                        self.advance()
                        self.advance()
                        self.advance()
                        break
                    buf.append(self.advance())
                    continue
                self.advance()
                break

            if ch == "\\":
                nxt = self.peek(1)
                if nxt == "(":
                    flush_text()
                    self.advance()  # backslash
                    self.advance()  # opening paren
                    expr_src, expr_line, expr_col = self.scan_interpolation()
                    parts.append(("expr", expr_src, expr_line, expr_col))
                    continue
                self.advance()
                esc = self.advance() if self.pos < len(self.src) else ""
                mapping = {
                    "n": "\n", "t": "\t", "r": "\r", "0": "\0",
                    "\\": "\\", '"': '"', "'": "'",
                }
                if esc in mapping:
                    buf.append(mapping[esc])
                elif esc == "u":
                    # \u{1F600}
                    if self.peek() != "{":
                        self.error("expected '{' after \\u")
                    self.advance()
                    hexs: list[str] = []
                    while self.pos < len(self.src) and self.src[self.pos] != "}":
                        hexs.append(self.advance())
                    if self.pos >= len(self.src):
                        self.error("unterminated \\u escape")
                    self.advance()
                    try:
                        buf.append(chr(int("".join(hexs), 16)))
                    except ValueError:
                        self.error("invalid unicode escape")
                elif multiline and esc == "\n":
                    # line continuation inside a multiline string
                    pass
                else:
                    self.error(f"invalid escape sequence '\\{esc}'")
                continue

            buf.append(self.advance())

        flush_text()

        raw_text = None
        if multiline:
            parts = self.dedent_multiline(parts, line, col)

        self.tokens.append(
            Token(STRING, raw_text, line, col, parts=parts)
        )

    def scan_interpolation(self) -> tuple[str, int, int]:
        """Scan the balanced ``( ... )`` body of a string interpolation.

        Returns the source text and the approximate line/column of its start.
        """
        depth = 1
        start = self.pos
        start_line, start_col = self.line, self.col
        while self.pos < len(self.src):
            ch = self.src[self.pos]
            if ch == "(":
                depth += 1
                self.advance()
            elif ch == ")":
                depth -= 1
                self.advance()
                if depth == 0:
                    return self.src[start:self.pos - 1], start_line, start_col
            elif ch == '"':
                # nested string literal: skip it (with interpolation aware scan)
                self.skip_string_in_interpolation()
            else:
                self.advance()
        self.error("unterminated string interpolation", start_line, start_col)

    def skip_string_in_interpolation(self) -> None:
        multiline = self.peek(1) == '"' and self.peek(2) == '"'
        for _ in range(3 if multiline else 1):
            self.advance()
        while self.pos < len(self.src):
            ch = self.src[self.pos]
            if ch == "\\":
                self.advance()
                if self.pos < len(self.src) and self.src[self.pos] == "(":
                    self.advance()
                    self.scan_interpolation()
                elif self.pos < len(self.src):
                    self.advance()
                continue
            if ch == '"':
                if multiline:
                    if self.peek(1) == '"' and self.peek(2) == '"':
                        self.advance()
                        self.advance()
                        self.advance()
                        return
                    self.advance()
                else:
                    self.advance()
                    return
            else:
                self.advance()
        self.error("unterminated string literal in interpolation")

    def dedent_multiline(self, parts: list, line: int, col: int) -> list:
        """Approximate Swift's multiline string indentation stripping."""
        # Only text parts that begin the string / follow an interpolation are
        # dedented; Swift dedents according to the closing delimiter.  The
        # closing delimiter's indentation can be inferred from the last line.
        if not parts:
            return parts
        text = "".join(p[1] for p in parts if p[0] == "text")
        lines = text.split("\n")
        if lines and lines[0].strip() == "":
            lines = lines[1:]
        if lines and lines[-1].strip() == "":
            lines = lines[:-1]
        indent = min(
            (len(ln) - len(ln.lstrip(" \t")) for ln in lines if ln.strip()),
            default=0,
        )
        lines = [ln[indent:] if len(ln) >= indent else ln for ln in lines]
        joined = "\n".join(lines)
        # Rebuild parts: this loses fine-grained interleaving with
        # interpolations, so only do it when there are no interpolations.
        if all(p[0] == "text" for p in parts):
            return [("text", joined)]
        # With interpolations we do a simpler cleanup: strip leading newline.
        out = []
        first = True
        for p in parts:
            if p[0] == "text":
                t = p[1]
                if first and t.startswith("\n"):
                    t = t[1:]
                # dedent each line by ``indent``
                t = "\n".join(
                    ln[indent:] if len(ln) >= indent else ln for ln in t.split("\n")
                )
                out.append(("text", t))
            else:
                out.append(p)
            first = False
        return out


def tokenize(src: str, filename: str = "<input>") -> list[Token]:
    return Lexer(src, filename).tokenize()
