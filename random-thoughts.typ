$
  & display(
    (Gamma tack e_1 : tau_1 wide Gamma tack e_2 : tau_2)
    /
    (Gamma tack e_1 ";" e_2 : tau_2)
  ) && "[STMT]" \
  \
  & display(
    (Gamma tack lambda x -> e : sigma -> pi wide Gamma tack e_1 : pi)
    /
    (Gamma tack bold("return") e_1 : !)
  ) && "[RETURN]" wide bold("return") e_1 "is an expression inside" e \
  \
  & display(
    (Gamma tack e : tau)
    /
    (Gamma tack bold("throw") e : !)
  ) && "[THROW]" \
  \
  & display(
    (Gamma tack e : tau)
    /
    (Gamma tack bold("loop") e : !)
  ) && "[LOOP]" wide "if there's no" bold("break") "in" e \
  \
  & display(
    (Gamma tack e : tau wide Gamma tack e_1 : pi)
    /
    (Gamma tack bold("break") e_1 : ! wide Gamma tack bold("loop") e : pi)
  ) && "[BREAK]" wide bold("break")  e_1 "is an expression inside" e \
$
