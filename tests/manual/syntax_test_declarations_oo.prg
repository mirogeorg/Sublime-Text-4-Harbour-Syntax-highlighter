CLASS Sample
   DATA Value
   METHOD New( x )
ENDCLASS

METHOD New( x ) CLASS Sample
   ::Value := x
RETURN Self

FUNCTION Standalone( x )
RETURN x

