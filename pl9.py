from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass

class Type:
    @abstractmethod
    def instantiate(self, free: dict[TypeVar, TypeVar]) -> Type:
        pass

    @abstractmethod
    def apply_subst(self, subst: Subst) -> Type:
        pass

    def need_quote(self) -> bool:
        return False


global_timestamp: dict[str, int] = {}


@dataclass
class TypeVar(Type):
    greek: str
    timestamp: int | None

    def __init__(self, greek: str):
        global global_timestamp
        self.greek = greek
        if self.greek in global_timestamp:
            self.timestamp = global_timestamp[self.greek]
            global_timestamp[self.greek] += 1
        else:
            self.timestamp = 0
            global_timestamp[self.greek] = 1

    def __str__(self) -> str:
        if self.timestamp is not None:
            return self.greek + str(self.timestamp)
        else:
            return self.greek

    def __eq__(self, value: object) -> bool:
        if isinstance(value, TypeVar):
            return self.greek == value.greek and self.timestamp == value.timestamp
        return False

    def __hash__(self) -> int:
        return hash(self.greek) + hash(self.timestamp) if self.timestamp is not None else 0

    def fresh(self) -> TypeVar:
        return TypeVar(self.greek)

    def instantiate(self, free: dict[TypeVar, TypeVar]) -> Type:
        return free.get(self, self)

    def apply_subst(self, subst: Subst) -> Type:
        return subst.mapping.get(self, self)


Alpha = 'α'
Beta = 'β'
Gamma = 'γ'
Delta = 'δ'
Epsilon = 'ε'
Pi = 'π'
Tau = 'τ'


@dataclass
class TypeOp(Type):
    op: str
    args: list[Type]

    def __str__(self) -> str:
        if self.op == 'unit':
            return '()'

        if len(self.args) == 0:
            return self.op

        ret = ''
        if self.op == '*' or self.op == '->':
            for (idx, arg) in enumerate(self.args):
                if arg.need_quote():
                    ret += '(' + str(arg) + ')'
                else:
                    ret += str(arg)
                if idx != len(self.args) - 1:
                    ret += ' × ' if self.op == '*' else '→'
        else:
            ret += self.op
            for (idx, arg) in enumerate(self.args):
                if arg.need_quote():
                    ret += '(' + str(arg) + ')'
                else:
                    ret += str(arg)
                if idx != len(self.args) - 1:
                    ret += ' '
        return ret

    def instantiate(self, free: dict[TypeVar, TypeVar]) -> Type:
        if len(self.args) == 0:
            return self
        return TypeOp(self.op, [arg.instantiate(free) for arg in self.args])

    def apply_subst(self, subst: Subst) -> Type:
        if len(self.args) == 0:
            return self
        return TypeOp(self.op, [arg.apply_subst(subst) for arg in self.args])

    def need_quote(self) -> bool:
        return len(self.args) > 0


def product_type(*types: Type) -> TypeOp:
    return TypeOp('*', list(types))


def fn_type(arg_type: Type, ret_type: Type) -> TypeOp:
    return TypeOp('->', [arg_type, ret_type])


UnitType = TypeOp('unit', [])
IntType = TypeOp('int', [])
BoolType = TypeOp('bool', [])


@dataclass
class TypeScheme:
    free: list[TypeVar]
    ty: Type

    def __init__(self, free: list[TypeVar], ty: Type):
        self.free = free
        self.ty = ty
        self.free_accel = set(free)

    def __str__(self) -> str:
        ret = ''
        for item in self.free:
            ret += '∀' + str(item)
        ret += '. ' + str(self.ty)
        return ret

    def instantiate(self) -> Type:
        free = {}
        for item in self.free:
            free[item] = item.fresh()
        return self.ty.instantiate(free)


@dataclass
class Subst:
    mapping: dict[TypeVar, Type]

    def __str__(self) -> str:
        ret = '{'
        for (idx, tvar) in enumerate(self.mapping):
            trep = self.mapping[tvar]
            ret += str(tvar) + ': ' + str(trep)
            if idx != len(self.mapping) - 1:
                ret += ', '
        ret += '}'
        return ret


def compose_subst(s1: Subst, s2: Subst) -> Subst:
    for tvar in s1.mapping.keys():
        trep = s1.mapping[tvar]
        s1.mapping[tvar] = trep.apply_subst(s2)

    for tvar in s2.mapping.keys():
        if tvar not in s1.mapping:
            s1.mapping[tvar] = s2.mapping[tvar]
    return s1


@dataclass
class UnifyException(Exception):
    text: str


def unify(t1: Type, t2: Type) -> Subst:
    fresh_exception = False
    try:
        if isinstance(t1, TypeOp) and isinstance(t2, TypeOp):
            return unify_type_op(t1, t2)
        elif isinstance(t1, TypeVar):
            return Subst({ t1: t2 })
        elif isinstance(t2, TypeVar):
            return Subst({ t2: t1 })
        else:
            fresh_exception = True
            raise UnifyException('错误：无法归一化类型 ' + str(t1) + ' 和 ' + str(t2))
    except UnifyException as e:
        if not fresh_exception:
            e.text += '\n  - 当归一化类型 ' + str(t1) + ' 和 ' + str(t2) + ' 时发生'
        raise e


def unify_type_op(t1: TypeOp, t2: TypeOp) -> Subst:
    if t1.op != t2.op:
        raise UnifyException('错误：无法归一化类型算子 ' + str(t1) + ' 和 ' + str(t2) + '（运算符不同）')

    if len(t1.args) != len(t2.args):
        raise UnifyException('错误：无法归一化类型算子 ' + str(t1) + ' 和 ' + str(t2) + '（类型算子的参数数目不同）')

    s0 = Subst({})
    for idx in range(0, len(t1.args)):
        try:
            s1 = unify(t1.args[idx].apply_subst(s0), t2.args[idx].apply_subst(s0))
            s0 = compose_subst(s0, s1)
        except UnifyException as e:
            e.text += '\n  - 当归一化类型算子的第 ' + str(idx + 1) + ' 个参数（' + str(t1.args[idx]) + ' 和 ' + str(t2.args[idx]) + '）时发生'
            e.text += '\n    已分析的替换：' + str(s0)
            raise e
    return s0


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
class ExprVar(Expr):
    var_name: str

    def __str__(self) -> str:
        return str(self.var_name)


@dataclass
class ExprAbs(Expr):
    var_name: str
    body: Expr

    def __str__(self) -> str:
        body = f'({str(self.body)})' if self.body.need_quote() else str(self.body)
        return f'λ{self.var_name}. {body}'

    def need_quote(self) -> bool:
        return True


@dataclass
class ExprApp(Expr):
    fn: Expr
    arg: Expr

    def __str__(self) -> str:
        fn = f'({str(self.fn)})' if self.fn.need_quote() else str(self.fn)
        arg = f'({str(self.arg)})' if self.fn.need_quote() else str(self.arg)
        return f'{fn} {arg}'

    def need_quote(self) -> bool:
        return True


@dataclass
class TypeEnv:
    parent: TypeEnv | None
    vars: dict[str, TypeScheme]

    def __init__(self, parent: TypeEnv | None = None):
        self.parent = parent
        self.vars = {}


alpha = TypeVar(Alpha)
sch1 = TypeScheme([alpha], fn_type(alpha, alpha))
t1 = sch1.instantiate()
print('instantate(', sch1, ') = ', t1, sep='')

t2 = fn_type(IntType, BoolType)
print('unify(', t1, ', ', t2, ')', sep='')
try:
    print('=> ', unify(t1, t2), sep='')
except UnifyException as e:
    print(e.text)
