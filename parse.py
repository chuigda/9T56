from dataclasses import dataclass
from enum import Enum


class TokenKind(Enum):
    Int       = 1
    Boolean   = 2
    String    = 3
    Ident     = 4
    Backslash = 5

    Dot       = 6
    LParen    = 7
    RParen    = 8
    Eq        = 9
    Let       = 10
    Rec       = 11
    In        = 12

    EOI       = 13


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
    if ident == 'let':
        return index, Token(TokenKind.Let)
    if ident == 'rec':
        return index, Token(TokenKind.Rec)
    if ident == 'in':
        return index, Token(TokenKind.In)
    return index, Token(TokenKind.Ident, ident)


def test_tokenize():
    input = 'let id = \\x. x in id 1'
    tokens = tokenize(input)
    print(tokens)


if __name__ == '__main__':
    test_tokenize()
