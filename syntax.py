from dataclasses import dataclass


class Expr:
    def need_quote(self) -> bool:
        return False


@dataclass
class ExprLitInt(Expr):
    value: int

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class ExprLitBool(Expr):
    value: bool

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class ExprLitStr(Expr):
    value: str

    def __str__(self) -> str:
        return f'"{self.value}"'


@dataclass
class ExprVar(Expr):
    x: str

    def __str__(self) -> str:
        return str(self.x)


@dataclass
class ExprAbs(Expr):
    x: str
    body: Expr

    def __str__(self) -> str:
        body = f'({self.body})' if self.body.need_quote() else str(self.body)
        return f'λ{self.x}. {body}'

    def need_quote(self) -> bool:
        return True


@dataclass
class ExprApp(Expr):
    e1: Expr
    e2: Expr

    def __str__(self) -> str:
        e1 = f'({self.e1})' if self.e1.need_quote() else str(self.e1)
        e2 = f'({self.e2})' if self.e2.need_quote() else str(self.e2)
        return f'{e1} {e2}'

    def need_quote(self) -> bool:
        return True


@dataclass
class ExprLet(Expr):
    x: str
    e1: Expr
    e2: Expr

    def __str__(self) -> str:
        e1 = f'({self.e1})' if self.e1.need_quote() else str(self.e1)
        e2 = f'({self.e2})' if isinstance(self.e2, ExprLet) else str(self.e2)
        return f'let {self.x} = {e1} in {e2}'

    def need_quote(self) -> bool:
        return True


@dataclass
class ExprStmt(Expr):
    stmts: list[Expr]

    def __str__(self) -> str:
        ret = ''
        for (idx, stmt) in enumerate(self.stmts):
            ret += str(stmt)
            if idx != len(self.stmts) - 1:
                ret += '; '
        return ret

    def need_quote(self) -> bool:
        return True


@dataclass
class ExprReturn(Expr):
    e: Expr | None

    def __str__(self) -> str:
        return f'return {self.e}' if self.e is not None else 'return'

    def need_quote(self) -> bool:
        return True


@dataclass
class ExprIf(Expr):
    e1: Expr
    e2: Expr
    e3: Expr

    def __str__(self) -> str:
        e1 = f'({self.e1})' if self.e1.need_quote() else str(self.e1)
        e2 = f'({self.e2})' if self.e2.need_quote() else str(self.e2)
        e3 = f'({self.e3})' if self.e3.need_quote() else str(self.e3)
        return f'if {e1} then {e2} else {e3}'

    def need_quote(self) -> bool:
        return True


@dataclass
class ExprLetRec(Expr):
    decls: list[tuple[str, Expr]]
    body: Expr

    def __str__(self) -> str:
        ret = 'let rec '
        for (idx, (name, expr)) in enumerate(self.decls):
            expr_s = f'({expr}))' if expr.need_quote() else str(expr)
            ret += f'{name} = {expr_s}'
            if idx != len(self.decls) - 1:
                ret += '; '
        ret += ' in '
        body_s = f'({self.body})' if self.body.need_quote() else str(self.body)
        ret += body_s
        return ret

    def need_quote(self):
        return True
