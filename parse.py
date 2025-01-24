from dataclasses import dataclass
from enum import Enum

from syntax import *


class TokenKind(Enum):
    Int       = 'int'
    Boolean   = 'bool'
    String    = 'str'
    Ident     = 'ident'

    Backslash = '\\'
    Dot       = '.'
    Comma     = ','
    Semicolon = ';'
    LParen    = '('
    RParen    = ')'
    Eq        = '='

    Let       = 'let'
    Rec       = 'rec'
    In        = 'in'
    If        = 'if'
    Then      = 'then'
    Else      = 'else'
    Return    = 'return'

    EOI       = 'EOI'


@dataclass
class Token:
    kind: TokenKind
    data: int | bool | str | None

    def __init__(self, kind: TokenKind, data: int | bool | str | None = None):
        self.kind = kind
        self.data = data


def tokenize(input: str) -> list[Token]:
    ret = []

    index = 0
    while index < len(input):
        index = skip_whitespace(index, input)
        if index == len(input):
            break
        ch = input[index]
        if ch.isdigit():
            start = index
            while index < len(input) and input[index].isdigit():
                index += 1
            ret.append(Token(TokenKind.Int, int(input[start:index])))
        elif ch == '"':
            index += 1
            start = index
            while index < len(input) and input[index] != '"':
                index += 1
            ret.append(Token(TokenKind.String, input[start:index]))
            index += 1
        elif ch.isalpha():
            index, token = tokenize_ident_or_keyword(index, input)
            ret.append(token)
        elif ch == '\\':
            ret.append(Token(TokenKind.Backslash))
            index += 1
        elif ch == '.':
            ret.append(Token(TokenKind.Dot))
            index += 1
        elif ch == ',':
            ret.append(Token(TokenKind.Comma))
            index += 1
        elif ch == ';':
            ret.append(Token(TokenKind.Semicolon))
            index += 1
        elif ch == '(':
            ret.append(Token(TokenKind.LParen))
            index += 1
        elif ch == ')':
            ret.append(Token(TokenKind.RParen))
            index += 1
        elif ch == '=':
            ret.append(Token(TokenKind.Eq))
            index += 1
        else:
            raise Exception(f'未知字符：{ch}')
    ret.append(Token(TokenKind.EOI))
    return ret


def skip_whitespace(index: int, input: str) -> int:
    while index < len(input) and input[index].isspace():
        index += 1
    return index


def tokenize_ident_or_keyword(index: int, input: str) -> tuple[int, Token]:
    start = index
    while index < len(input) and input[index].isalnum():
        index += 1
    ident = input[start:index]
    if ident == 'true' or ident == 'false':
        return index, Token(TokenKind.Boolean, ident == 'true')
    elif ident == 'let':
        return index, Token(TokenKind.Let)
    elif ident == 'rec':
        return index, Token(TokenKind.Rec)
    elif ident == 'in':
        return index, Token(TokenKind.In)
    elif ident == 'if':
        return index, Token(TokenKind.If)
    elif ident == 'then':
        return index, Token(TokenKind.Then)
    elif ident == 'else':
        return index, Token(TokenKind.Else)
    elif ident == 'return':
        return index, Token(TokenKind.Return)
    else:
        return index, Token(TokenKind.Ident, ident)


def parse(tokens: list[Token]) -> Expr:
    return parse_expr(tokens, 0)[0]


def parse_expr(tokens: list[Token], index: int) -> tuple[Expr, int]:
    e1, index = parse_simple_expr(tokens, index)
    if tokens[index].kind == TokenKind.Semicolon:
        e2, index = parse_expr(tokens, index + 1)
        if isinstance(e2, ExprStmt):
            return ExprStmt([e1] + e2.stmts), index
        else:
            return ExprStmt([e1, e2]), index
    else:
        try:
            e2, index = parse_expr(tokens, index)
            return ExprApp(e1, e2), index
        except Exception:
            return e1, index


def parse_simple_expr(tokens: list[Token], index: int) -> tuple[Expr, int]:
    cur = tokens[index]
    if cur.kind == TokenKind.EOI:
        raise Exception('解析到末尾')

    if cur.kind == TokenKind.Int:
        assert isinstance(cur.data, int)
        return ExprLitInt(cur.data), index + 1
    elif cur.kind == TokenKind.Boolean:
        assert isinstance(cur.data, bool)
        return ExprLitBool(cur.data), index + 1
    elif cur.kind == TokenKind.String:
        assert isinstance(cur.data, str)
        return ExprLitStr(cur.data), index + 1
    elif cur.kind == TokenKind.Ident:
        assert isinstance(cur.data, str)
        return ExprVar(cur.data), index + 1
    elif cur.kind == TokenKind.Backslash:
        assert tokens[index + 1].kind == TokenKind.Ident
        var_name = tokens[index + 1].data
        assert isinstance(var_name, str)

        assert tokens[index + 2].kind == TokenKind.Dot

        e1, index = parse_expr(tokens, index + 3)
        return ExprAbs(var_name, e1), index
    elif cur.kind == TokenKind.LParen:
        e1, index = parse_expr(tokens, index + 1)
        assert tokens[index].kind == TokenKind.RParen
        return e1, index + 1
    elif cur.kind == TokenKind.Let:
        if tokens[index + 1].kind == TokenKind.Rec:
            return parse_let_rec(tokens, index + 2)
        else:
            return parse_let(tokens, index + 1)
    elif cur.kind == TokenKind.If:
        return parse_if(tokens, index + 1)
    elif cur.kind == TokenKind.Return:
        e1, index = parse_expr(tokens, index + 1)
        if isinstance(e1, ExprVar) and e1.x == 'nothing':
            return ExprReturn(None), index
        else:
            return ExprReturn(e1), index
    else:
        raise Exception(f'未知 Token: {cur}')


# let rec var1 = e1, var2 = e2, ..., varn = en in e
def parse_let_rec(tokens: list[Token], index: int) -> tuple[Expr, int]:
    bindings: list[tuple[str, Expr]] = []
    while tokens[index].kind == TokenKind.Ident:
        var_name = tokens[index].data
        assert isinstance(var_name, str)

        assert tokens[index + 1].kind == TokenKind.Eq
        e1, index = parse_expr(tokens, index + 2)
        bindings.append((var_name, e1))

        if tokens[index].kind == TokenKind.Comma:
            index += 1
        else:
            break

    assert tokens[index].kind == TokenKind.In
    e, index = parse_expr(tokens, index + 1)

    return ExprLetRec(bindings, e), index


# let var = e1 in e2
def parse_let(tokens: list[Token], index: int) -> tuple[Expr, int]:
    assert tokens[index].kind == TokenKind.Ident
    var_name = tokens[index].data
    assert isinstance(var_name, str)

    assert tokens[index + 1].kind == TokenKind.Eq
    e1, index = parse_expr(tokens, index + 2)

    assert tokens[index].kind == TokenKind.In
    e2, index = parse_expr(tokens, index + 1)

    return ExprLet(var_name, e1, e2), index


# if e1 then e2 else e3
def parse_if(tokens: list[Token], index: int) -> tuple[Expr, int]:
    e1, index = parse_expr(tokens, index)
    assert tokens[index].kind == TokenKind.Then
    e2, index = parse_expr(tokens, index + 1)
    assert tokens[index].kind == TokenKind.Else
    e3, index = parse_expr(tokens, index + 1)

    return ExprIf(e1, e2, e3), index
