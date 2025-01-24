#!/usr/bin/env python3

# PL9J - PL9 in Algorithm J - Extended
#
# 采用 Algorithm J 的 HM 类型系统的实现，同时经过一定程度的扩展

from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass


class Type:
    @abstractmethod
    def contains_type_var(self, type_var: TypeVar) -> bool:
        pass

    @abstractmethod
    def collect_type_vars(self, dst: list[TypeVar]):
        pass

    @abstractmethod
    def instantiate(self, free: dict[TypeVar, TypeVar]) -> Type:
        pass

    @abstractmethod
    def prune(self) -> Type:
        pass

    def need_quote(self) -> bool:
        return False


global_timestamp: dict[str, int] = {}


@dataclass
class TypeVar(Type):
    greek: str
    timestamp: int
    resolve: Type | None

    def __init__(self, greek: str):
        global global_timestamp
        self.greek = greek
        if self.greek in global_timestamp:
            self.timestamp = global_timestamp[self.greek]
            global_timestamp[self.greek] += 1
        else:
            self.timestamp = 0
            global_timestamp[self.greek] = 1
        self.resolve = None

    def __str__(self) -> str:
        # if self.greek == Eta:
        #     return '!'
        return self.greek + str(self.timestamp)

    def __eq__(self, value: object) -> bool:
        if isinstance(value, TypeVar):
            return self.greek == value.greek and self.timestamp == value.timestamp
        return False

    def __hash__(self) -> int:
        return hash(self.greek) + hash(self.timestamp) if self.timestamp is not None else 0

    def prune(self) -> Type:
        if self.resolve is not None:
            pruned = self.resolve.prune()
            self.resolve = pruned
            return pruned
        else:
            return self

    def fresh(self) -> TypeVar:
        return TypeVar(self.greek)

    def contains_type_var(self, type_var: TypeVar) -> bool:
        return self == type_var

    def collect_type_vars(self, dst: list[TypeVar]):
        dst.append(self)

    def instantiate(self, free: dict[TypeVar, TypeVar]) -> Type:
        return free.get(self, self)


Alpha = 'α'
Beta = 'β'
Gamma = 'γ'
Delta = 'δ'
Epsilon = 'ε'
Pi = 'π'
Tau = 'τ'
Eta = 'η'


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

    def contains_type_var(self, type_var: TypeVar) -> bool:
        for arg in self.args:
            if arg.contains_type_var(type_var):
                return True
        return False

    def collect_type_vars(self, dst: list[TypeVar]):
        for arg in self.args:
            arg.collect_type_vars(dst)

    def instantiate(self, free: dict[TypeVar, TypeVar]) -> Type:
        if len(self.args) == 0:
            return self
        return TypeOp(self.op, [arg.instantiate(free) for arg in self.args])

    def prune(self) -> Type:
        return self

    def need_quote(self) -> bool:
        return len(self.args) > 0


def product_type(*types: Type) -> TypeOp:
    return TypeOp('*', list(types))


def fn_type(arg_type: Type, ret_type: Type) -> TypeOp:
    return TypeOp('->', [arg_type, ret_type])


UnitType = TypeOp('unit', [])
IntType = TypeOp('int', [])
BoolType = TypeOp('bool', [])
StrType = TypeOp('str', [])


@dataclass
class TypeScheme:
    free: list[TypeVar]
    ty: Type

    def __init__(self, free: list[TypeVar], ty: Type):
        self.free = free
        self.ty = ty
        self.free_accel = set(free)

    def __str__(self) -> str:
        if len(self.free) == 0:
            return str(self.ty)

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
class TyckException(Exception):
    text: str


def unify(t1: Type, t2: Type):
    t1 = t1.prune()
    t2 = t2.prune()

    fresh_exception = False
    try:
        if isinstance(t1, TypeOp) and isinstance(t2, TypeOp):
            return unify_type_op(t1, t2)
        elif isinstance(t1, TypeVar):
            return unify_type_var(t1, t2)
        elif isinstance(t2, TypeVar):
            return unify_type_var(t2, t1)
        else:
            fresh_exception = True
            raise TyckException(f'错误：无法归一化类型 {str(t1)} 和 {str(t2)}')
    except TyckException as e:
        if not fresh_exception:
            e.text += f'\n  - 当归一化类型 {str(t1)} 和 {str(t2)} 时发生'
        raise e


def unify_type_var(t1: TypeVar, t2: Type):
    if t2.contains_type_var(t1):
        raise TyckException(f'错误：无法归一化类型变量 {str(t1)} 和类型 {str(t2)}：后者中存在对前者的引用，这是不允许的')
    t1.resolve = t2


def unify_type_op(t1: TypeOp, t2: TypeOp):
    if t1.op != t2.op:
        raise TyckException(f'错误：无法归一化类型算子 {str(t1)} 和 {str(t2)}（运算符不同）')

    if len(t1.args) != len(t2.args):
        raise TyckException(f'错误：无法归一化类型算子 {str(t1)} 和 {str(t2)}（类型算子的参数数目不同）')

    for idx in range(0, len(t1.args)):
        try:
            unify(t1.args[idx], t2.args[idx])
        except TyckException as e:
            e.text += f'\n  - 当归一化类型算子的第 {str(idx + 1)} 个参数（{str(t1.args[idx])} 和 {str(t2.args[idx])}）时发生'
            raise e


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
        body = f'({str(self.body)})' if self.body.need_quote() else str(self.body)
        return f'λ{self.x}. {body}'

    def need_quote(self) -> bool:
        return True


@dataclass
class ExprApp(Expr):
    e1: Expr
    e2: Expr

    def __str__(self) -> str:
        e1 = f'({str(self.e1)})' if self.e1.need_quote() else str(self.e1)
        e2 = f'({str(self.e2)})' if self.e2.need_quote() else str(self.e2)
        return f'{e1} {e2}'

    def need_quote(self) -> bool:
        return True


@dataclass
class ExprLet(Expr):
    x: str
    e1: Expr
    e2: Expr

    def __str__(self) -> str:
        e1 = f'({str(self.e1)})' if self.e1.need_quote() else str(self.e1)
        e2 = f'({str(self.e2)})' if isinstance(self.e2, ExprLet) else str(self.e2)
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
        return f'return {str(self.e)}' if self.e is not None else 'return'

    def need_quote(self) -> bool:
        return True


@dataclass
class ExprIf(Expr):
    e1: Expr
    e2: Expr
    e3: Expr

    def __str__(self) -> str:
        e1 = f'({str(self.e1)})' if self.e1.need_quote() else str(self.e1)
        e2 = f'({str(self.e2)})' if self.e2.need_quote() else str(self.e2)
        e3 = f'({str(self.e3)})' if self.e3.need_quote() else str(self.e3)
        return f'if {e1} then {e2} else {e3}'

    def need_quote(self) -> bool:
        return True


@dataclass
class TypeEnv:
    parent: TypeEnv | None
    vars: dict[str, TypeScheme]
    non_generic_type_vars: set[TypeVar]
    return_ty: TypeVar | None

    def __init__(self, parent: TypeEnv | None = None):
        self.parent = parent
        self.vars = {}
        self.non_generic_type_vars = set()
        self.return_tys = []

    def lookup(self, var_name: str) -> TypeScheme | None:
        if var_name in self.vars:
            return self.vars[var_name]

        if self.parent is not None:
            return self.parent.lookup(var_name)

    def collect_type_vars(self, dst: list[TypeVar]):
        for var_scheme in self.vars.values():
            var_scheme.ty.collect_type_vars(dst)
        if self.parent is not None:
            self.parent.collect_type_vars(dst)

    def is_non_generic(self, v: TypeVar) -> bool:
        if v in self.non_generic_type_vars:
            return True
        return self.parent.is_non_generic(v) if self.parent is not None else False


def j(env: TypeEnv, expr: Expr) -> Type:
    try:
        if isinstance(expr, ExprLitInt):
            return IntType
        elif isinstance(expr, ExprLitBool):
            return BoolType
        elif isinstance(expr, ExprLitStr):
            return StrType
        elif isinstance(expr, ExprVar):
            scheme = env.lookup(expr.x)
            if scheme is not None:
                return scheme.instantiate()
            else:
                raise TyckException(f'变量或函数 {expr.x} 尚未定义')
        elif isinstance(expr, ExprAbs):
            beta = TypeVar(Beta)
            env1 = TypeEnv(env)
            env1.vars[expr.x] = TypeScheme([], beta)
            env1.non_generic_type_vars.add(beta)
            env1.return_ty = TypeVar(Eta)
            t1 = j(env1, expr.body)
            unify(env1.return_ty, t1)
            return fn_type(beta.prune(), t1.prune())
        elif isinstance(expr, ExprApp):
            pi = TypeVar(Pi)
            t1 = j(env, expr.e1)
            t2 = j(env, expr.e2)
            unify(fn_type(t2, pi), t1)
            return pi.prune()
        elif isinstance(expr, ExprLet):
            env1 = TypeEnv(env)
            t1 = j(env1, expr.e1)
            x_scheme = generalize(env1, t1)
            env1.vars[expr.x] = x_scheme
            return j(env1, expr.e2)
        elif isinstance(expr, ExprStmt):
            for (idx, stmt) in enumerate(expr.stmts):
                t = j(env, stmt)
                if idx == len(expr.stmts) - 1:
                    return t
            assert False
        elif isinstance(expr, ExprReturn):
            if env.return_ty is None:
                raise TyckException('错误：return 只能在函数体内使用')
            if expr.e is not None:
                t_ret = j(env, expr.e)
            else:
                t_ret = UnitType
            unify(env.return_ty, t_ret)
            return TypeVar(Eta)
        elif isinstance(expr, ExprIf):
            t1 = j(env, expr.e1)
            t2 = j(env, expr.e2)
            t3 = j(env, expr.e3)
            unify(t1, BoolType)
            unify(t2, t3)
            return t2
        else:
            raise Exception(f'表达式 {expr} 的类型未知')
    except TyckException as e:
        e.text += f'\n  - 当检查表达式 {str(expr)} 时发生'
        raise e


def generalize(env: TypeEnv, t: Type) -> TypeScheme:
    type_vars: list[TypeVar] = []
    t.collect_type_vars(type_vars)

    filtered_type_vars: list[TypeVar] = []
    for type_var in set(type_vars):
        if not env.is_non_generic(type_var):
            filtered_type_vars.append(type_var)

    return TypeScheme(filtered_type_vars, t)


def default_env() -> TypeEnv:
    env = TypeEnv()
    env.vars['square'] = TypeScheme([], fn_type(IntType, IntType))
    env.vars['print'] = TypeScheme([], fn_type(StrType, UnitType))
    return env


def try_inference(expr: Expr, env: TypeEnv = default_env()):
    print(f'j(Γ, {str(expr)})')
    try:
        t = j(env, expr)
        t_scheme = generalize(env, t)
        print(f'=> t = {str(t_scheme)}')
    except TyckException as e:
        print(f'=> {e.text}')
    print('------------\n')


r'''
# let f = \x. if x then 10 else 20 in f true
e1 = ExprLet(
    'f',
    ExprAbs('x', ExprIf(
        ExprVar('x'),
        ExprLitInt(10),
        ExprLitInt(20),
    )),
    ExprApp(ExprVar('f'), ExprLitBool(True))
)
try_inference(e1)

# let f = \x. if x then (return 0) else 42 in f true
e2 = ExprLet(
    'f',
    ExprAbs('x', ExprIf(
        ExprVar('x'),
        ExprReturn(ExprLitInt(0)),
        ExprLitInt(42),
    )),
    ExprApp(ExprVar('f'), ExprLitBool(True))
)
try_inference(e2)

# let f = \x. if (cond x) then 42 else (print "does not satisfy"; return 0) in f 114
e3 = ExprLet(
    'f',
    ExprAbs('x', ExprIf(
        ExprApp(ExprVar("cond"), ExprVar('x')),
        ExprLitInt(42),
        ExprStmt([
            ExprApp(ExprVar("print"), ExprLitStr("does not satisfy")),
            ExprReturn(ExprLitInt(0))
        ])
    )),
    ExprApp(ExprVar('f'), ExprLitBool(True))
)
env1 = default_env()
env1.vars['cond'] = TypeScheme([], fn_type(IntType, BoolType))
env1.vars['zero'] = TypeScheme([], fn_type(IntType, BoolType))
env1.vars['dec'] = TypeScheme([], fn_type(IntType, IntType))
env1.vars['times'] = TypeScheme([], fn_type(IntType, fn_type(IntType, IntType)))
try_inference(e3, env1)

# fail case
# let f = \x. if (cond x) then 42 else (print "does not satisfy"; return) in f 114
e4 = ExprLet(
    'f',
    ExprAbs('x', ExprIf(
        ExprApp(ExprVar("cond"), ExprVar('x')),
        ExprLitInt(42),
        ExprStmt([
            ExprApp(ExprVar("print"), ExprLitStr("does not satisfy")),
            ExprReturn(None)
        ])
    )),
    ExprApp(ExprVar('f'), ExprLitBool(True))
)
try_inference(e4, env1)
'''

# let id = \x. x in id
# e5 = ExprLet('id', ExprAbs('x', ExprVar('x')), ExprVar('id'))
# try_inference(e5)

# let id2 = \x. x
#  in let id = \x. id2 x
#      in id

e6 = ExprLet(
    'id2', ExprAbs('x', ExprVar('x')),
    ExprLet(
        'id', ExprAbs('x', ExprApp(ExprVar('id2'), ExprVar('x'))),
        ExprVar('id')
    )
)
try_inference(e6)
