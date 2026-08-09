# Ръчно тестване в Sublime Text 4

Инсталирай само `package/Harbour` като `Packages/Harbour`. За всеки файл отвори
`Tools → Developer → Show Scope Name` и постави курсора върху посочения token.

| Файл | Действие | Очакван scope/цвят | Признак за дефект |
|---|---|---|---|
| `syntax_test_comments.prg` | Провери трите line comment форми и block comment | `comment.*.harbour` | Текст след comment се оцветява като код |
| `syntax_test_strings.prg` | Провери `'`, `"`, `e"` и bracket string | `string.quoted.*.harbour` | String приключва твърде рано или поглъща следващия ред |
| `syntax_test_literals_operators.prg` | Постави курсора върху date, `.T.`, `:=`, `**=` и `->` | `constant.*` и `keyword.operator.harbour` | Операторът се дели или остава plain text |
| `syntax_test_declarations_oo.prg` | Отвори Symbol List / Goto Symbol | function/class имената са symbols | Липсват symbols или keyword е име |
| `syntax_test_preprocessor.ch` | Провери directive, `<marker>` и `=>` | `meta.preprocessor`, parameter, assignment | Целият следващ ред остава preprocessor |
| `syntax_test_dbstru.res` | Отвори файла директно | syntax се избира автоматично; секциите са маркирани | `.res` е Plain Text |
| `syntax_test_preprocessed.ppo` | Отвори файла директно | Harbour syntax автоматично | `.ppo` е Plain Text |
| `syntax_test_script.hb` | Отвори файла директно | Harbour syntax; `hb_Version` е function | `.hb` е Plain Text |
| `syntax_test_idu.idu` | Отвори файла директно | Harbour syntax и preprocessor | `.idu` е Plain Text |
| `syntax_test_invalid.prg` | Провери unclosed string и stray `*/` | `invalid.illegal.*` | Дефектът не се маркира |
| `syntax_test_all_functions.prg` | Run Syntax Tests | всеки generated symbol е `support.function.harbour` | Има assertion failure |

Допълнителни проверки:

1. Отвори нов `.c` и `.h` файл: те трябва да останат C/C++, не Harbour.
2. Изпълни Toggle Comment върху Harbour ред и провери `//` toggle.
3. Въведи `hb_Vers` и отвори autocomplete. Completion-ът трябва да показва
   кратък етикет `help`, сигнатура и кратко описание.
4. Изпълни двете команди `Harbour: Function Help`. Символ без source evidence
   не трябва да показва измислена помощ.
5. Провери tab stops на snippets: `function`, `procedure`, `if`, `docase`, `for`,
   `include`.
6. Измери отварянето на `syntax_test_all_functions.prg` (цел: до 2 s) и 20
   последователни редакции в края му (цел: всяка до 100 ms) на ST4 build 4200.
