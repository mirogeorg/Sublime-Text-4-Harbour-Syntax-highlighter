PROCEDURE Main()
   LOCAL d := {^2026-08-09}, t := {^2026-08-09 12:34:56}
   LOCAL n := 2, l := .T., x := NIL
   n **= 3
   ? n <> 0, "ABC" $ "ABCDE", Alias->Field, Object:Member, Object::Parent
   Demo( @n, &cMacro )
RETURN

