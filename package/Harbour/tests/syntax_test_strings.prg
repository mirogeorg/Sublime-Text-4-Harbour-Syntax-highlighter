// SYNTAX TEST "Packages/Harbour/Harbour.sublime-syntax"

cOne := 'single'
//        ^^^^^^ string.quoted.single.harbour
cTwo := "double"
//        ^^^^^^ string.quoted.double.harbour
cEsc := e"line\nnext"
//       ^^^^^^^^^^^^^ string.quoted.double.escape.harbour
cBracket := [bracket]
//           ^^^^^^^ string.quoted.other.bracket.harbour

