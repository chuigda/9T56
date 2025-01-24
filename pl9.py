#!/usr/bin/env python3

from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from typing import Tuple

from plsyntax import Expr, ExprLitInt, ExprLitBool, ExprVar, ExprAbs, ExprApp, ExprLet
from ghaik import Greek

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
    def apply_subst(self, subst: Subst) -> Type:
        pass

    def need_quote(self) -> bool:
        return False


global_timestamp: dict[Greek, int] = {}


@dataclass
class TypeVar(Type):
    greek: Greek
    timestamp: int | None

    def __init__(self, greek: Greek):
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
            return f'{self.greek} {self.timestamp}'
        else:
            return str(self.greek)

    def __eq__(self, value: object) -> bool:
        if isinstance(value, TypeVar):
            return self.greek == value.greek and self.timestamp == value.timestamp
        return False

    def __hash__(self) -> int:
        return hash(self.greek) + hash(self.timestamp) if self.timestamp is not None else 0

    def fresh(self) -> TypeVar:
        return TypeVar(self.greek)

    def contains_type_var(self, type_var: TypeVar) -> bool:
        return self == type_var

    def collect_type_vars(self, dst: list[TypeVar]):
        dst.append(self)

    def instantiate(self, free: dict[TypeVar, TypeVar]) -> Type:
        return free.get(self, self)

    def apply_subst(self, subst: Subst) -> Type:
        return subst.mapping.get(self, self)


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
class Subst:
    mapping: dict[TypeVar, Type]

    def __init__(self, mapping: dict[TypeVar, Type] = {}):
        self.mapping = mapping

    def __str__(self) -> str:
        ret = '{'
        for (idx, tvar) in enumerate(self.mapping):
            trep = self.mapping[tvar]
            ret += f'{tvar}: {trep}'
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
class TyckException(Exception):
    text: str


def unify(t1: Type, t2: Type) -> Subst:
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
            raise TyckException(f'错误：无法归一化类型 {t1} 和 {t2}')
    except TyckException as e:
        if not fresh_exception:
            e.text += f'\n  - 当归一化类型 {t1} 和 {t2} 时发生'
        raise e


def unify_type_var(t1: TypeVar, t2: Type) -> Subst:
    if t2.contains_type_var(t1):
        raise TyckException(f'错误：无法归一化类型变量 {t1} 和类型 {t2}：后者中存在对前者的引用，这是不允许的')
    return Subst({ t1: t2 })


def unify_type_op(t1: TypeOp, t2: TypeOp) -> Subst:
    if t1.op != t2.op:
        raise TyckException(f'错误：无法归一化类型算子 {t1} 和 {t2}（运算符不同）')

    if len(t1.args) != len(t2.args):
        raise TyckException(f'错误：无法归一化类型算子 {t1} 和 {t2}（类型算子的参数数目不同）')

    s0 = Subst()
    for idx in range(0, len(t1.args)):
        try:
            s1 = unify(t1.args[idx].apply_subst(s0), t2.args[idx].apply_subst(s0))
            s0 = compose_subst(s0, s1)
        except TyckException as e:
            e.text += f'\n  - 当归一化类型算子的第 {idx + 1} 个参数（{t1.args[idx]} 和 {t2.args[idx]}）时发生'
            e.text += f'\n    已分析的替换：{s0}'
            raise e
    return s0


@dataclass
class TypeEnv:
    parent: TypeEnv | None
    vars: dict[str, TypeScheme]

    def __init__(self, parent: TypeEnv | None = None):
        self.parent = parent
        self.vars = {}

    def lookup(self, var_name: str) -> TypeScheme | None:
        if var_name in self.vars:
            return self.vars[var_name]

        if self.parent is not None:
            return self.parent.lookup(var_name)

    def apply_subst(self, subst: Subst) -> TypeEnv:
        ret = TypeEnv()
        iter = self
        while iter is not None:
            for var_name in iter.vars:
                var_scheme = iter.vars[var_name]
                ret.vars[var_name] = TypeScheme(var_scheme.free, var_scheme.ty.apply_subst(subst))
            iter = iter.parent
        return ret

    def collect_type_vars(self, dst: list[TypeVar]):
        for var_scheme in self.vars.values():
            var_scheme.ty.collect_type_vars(dst)
        if self.parent is not None:
            self.parent.collect_type_vars(dst)


# 𝑊 :: 𝑇𝑦𝑝𝑒𝐸𝑛𝑣𝑖𝑟𝑜𝑛𝑚𝑒𝑛𝑡 × 𝐸𝑥𝑝𝑟𝑒𝑠𝑠𝑖𝑜𝑛 → 𝑆𝑢𝑏𝑠𝑡𝑖𝑡𝑢𝑡𝑖𝑜𝑛 × 𝑇𝑦𝑝𝑒
def w(env: TypeEnv, expr: Expr) -> Tuple[Subst, Type]:
    try:
        # Trivial cases (literals)
        if isinstance(expr, ExprLitInt):
            return Subst(), IntType
        elif isinstance(expr, ExprLitBool):
            return Subst(), BoolType
        # 𝑊(Γ, 𝑥) = ([], 𝑖𝑛𝑠𝑡𝑎𝑛𝑡𝑖𝑎𝑡𝑒(𝜎)), where (𝑥 : 𝜎) ∈ Γ
        elif isinstance(expr, ExprVar):
            scheme = env.lookup(expr.x)
            if scheme is not None:
                return Subst(), scheme.instantiate()
            else:
                raise TyckException(f'变量或函数 {expr.x} 尚未定义')
        # 𝑊(Γ, 𝜆𝑥 → 𝑒)
        elif isinstance(expr, ExprAbs):
            # fresh 𝛽
            beta = TypeVar(Greek.Beta)
            env1 = TypeEnv(env)
            # Γ' = Γ\𝑥 ∪ {𝑥 : 𝛽}
            env1.vars[expr.x] = TypeScheme([], beta)
            # 𝐥𝐞𝐭 (𝑆1, 𝜏1) = 𝑊(Γ', 𝑒)
            s1, t1 = w(env1, expr.body)
            # (𝑆1𝛽 → 𝜏1, 𝑆1)
            return s1, fn_type(beta.apply_subst(s1), t1)
        # 𝑊(Γ, 𝑒1𝑒2)
        elif isinstance(expr, ExprApp):
            # fresh 𝜋
            pi = TypeVar(Greek.Pi)
            # 𝐥𝐞𝐭 (𝑆1, 𝜏1) = 𝑊(Γ, 𝑒1)
            s1, t1 = w(env, expr.e1)
            # Γ' = 𝑆1Γ
            env1 = env.apply_subst(s1)
            # 𝐥𝐞𝐭 (𝑆2, 𝜏2) = 𝑊(Γ', 𝑒2)
            s2, t2 = w(env, expr.e2)
            # 𝑆3 = 𝑢𝑛𝑖𝑓𝑦(𝑆2𝜏1, 𝜏2 → 𝜋)
            s3 = unify(t1.apply_subst(s2), fn_type(t2, pi))
            # (𝑆3 ∘ 𝑆2 ∘ 𝑆1, 𝑆3𝜋)
            return compose_subst(compose_subst(s1, s2), s3), pi.apply_subst(s3)
        # 𝑊(Γ, 𝐥𝐞𝐭 𝑥 = 𝑒1 𝐢𝐧 𝑒2)
        elif isinstance(expr, ExprLet):
            # 𝐥𝐞𝐭 (𝑆1, 𝜏1) = 𝑊(Γ, 𝑒1)
            s1, t1 = w(env, expr.e1)
            # Γ' = 𝑆1Γ
            env1 = env.apply_subst(s1)
            # scheme(𝑥) = 𝑔𝑒𝑛𝑒𝑟𝑎𝑙𝑖𝑧𝑒(Γ', 𝜏1)
            x_scheme = generalize(env1, t1)
            # Γ'' = 𝑆1Γ\x ∪ {𝑥 : scheme(𝑥)}
            env2 = env1
            env2.vars[expr.x] = x_scheme
            # let(𝑆2, 𝜏2) = 𝑊(Γ'', 𝑒2)
            s2, t2 = w(env2, expr.e2)
            return compose_subst(s1, s2), t2
        else:
            raise Exception(f'表达式 {expr} 的类型未知')
    except TyckException as e:
        e.text += f'\n  - 当检查表达式 {expr} 时发生'
        raise e


def generalize(env: TypeEnv, t: Type) -> TypeScheme:
    type_vars: list[TypeVar] = []
    t.collect_type_vars(type_vars)
    type_vars_in_env: list[TypeVar] = []
    env.collect_type_vars(type_vars_in_env)

    type_vars_in_env_set: set[TypeVar] = set(type_vars_in_env)
    filtered_type_vars: list[TypeVar] = []
    for type_var in set(type_vars):
        if type_var not in type_vars_in_env_set:
            filtered_type_vars.append(type_var)

    return TypeScheme(filtered_type_vars, t)


def try_inference(expr: Expr):
    env = TypeEnv()
    env.vars['square'] = TypeScheme([], fn_type(IntType, IntType))

    print(f'w(Γ, {expr})')
    try:
        s, t = w(env, expr)
        t_scheme = generalize(env, t)
        print(f'=> t = {t_scheme}, S = {s}')
    except TyckException as e:
        print(f'=> {e.text}')


# 成功：let id = \x. x in (id square) (id 5)
try_inference(ExprLet(
    'id', ExprAbs('x', ExprVar('x')),
    ExprApp(ExprApp(ExprVar('id'), ExprVar('square')), ExprApp(ExprVar('id'), ExprLitInt(5)))
))
print('------\n')

# 成功：let id = \x. x in (id id) (id id)
try_inference(ExprLet(
    'id', ExprAbs('x', ExprVar('x')),
    ExprApp(ExprApp(ExprVar('id'), ExprVar('id')), ExprApp(ExprVar('id'), ExprVar('id')))
))
print('------\n')

# 失败，因为存在无限类型：let id = \x. x in (\f. f f) id
try_inference(ExprLet(
    'id', ExprAbs('x', ExprVar('x')),
    ExprApp(ExprAbs('f', ExprApp(ExprVar('f'), ExprVar('f'))), ExprVar('id'))
))
print('------\n')

# 失败，因为 lambda 引入的变量没有多态性：(\id. (id square) (id 5)) (\x. x)
try_inference(ExprApp(
    ExprAbs('id', ExprApp(ExprApp(ExprVar('id'), ExprVar('square')), ExprApp(ExprVar('id'), ExprLitInt(5)))),
    ExprAbs('x', ExprVar('x'))
))
print('------\n')

# 失败，因为 let 绑定的变量来自 lambda，同样没有多态性：(\id. (let id1 = id in (id1 square) (id1 5))) (\x. x)
try_inference(ExprApp(
    ExprAbs('id', ExprLet(
        'id1', ExprVar('id'),
        ExprApp(ExprApp(ExprVar('id1'), ExprVar('square')), ExprApp(ExprVar('id1'), ExprLitInt(5)))
    )),
    ExprAbs('x', ExprVar('x'))
))
