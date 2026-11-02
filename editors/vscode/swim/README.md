# swim language support for VS Code

Syntax highlighting plus bracket/indentation configuration for `.sw` files.

## Install

Option 1 (development mode):

```bash
cd editors/vscode/swim
code --extensionDevelopmentPath="$(pwd)"
```

Option 2 (package as a .vsix):

```bash
cd editors/vscode/swim
npx @vscode/vsce package
code --install-extension swim-language-0.1.0.vsix
```

You can also copy `syntaxes/swim.tmLanguage.json` into any editor that supports
TextMate grammars (Sublime Text, TextMate, Zed, etc.).
