#import "template.typ": *

#show: project.with(
  title: "基本多态类型检查",
  authors: (
    (name: "Luca Cardelli", contrib: "原作者", affiliation: "AT&T 贝尔实验室"),
    (name: "Chuigda WhiteGive", contrib: "翻译", affiliation: "第七通用设计局"),
    (name: "Flaribbit", contrib: "Typst 技术支持", affiliation: "第七通用设计局"),
  )
)

#show link: set text(fill: rgb(0, 127, 255))
#show math.equation: it => {
  show regex("if|let|then|else|int|bool|list|fun|pred|succ|null|length|hd|tl|true|false|zero|pair|fst|snd|nil|cons"): set text(weight: "bold")
  it
}
#show math.equation.where(block: true): set block(breakable: true)

#let ref(txt) = link(label(txt))[\[#txt\]]

= 前言
本文是对 1984 年 Luca Cardelli 论文 #link("http://lucacardelli.name/Papers/BasicTypechecking%20(TR%201984).pdf")[Basic Polymorphic Typechecking] 的翻译，并且使用 Java 重写了论文中的例子，避免 ML 的语法对读者造成困扰，以及找不到好的 ML 实现对读者造成困扰。

#set heading(numbering: "1.")

= 介绍
多态类型检查（Polymorphic Type Checking）的基础是由 Hindley 所设计的类型系统 #ref("Hindley 69")，并在之后被 Milner 再次发现并进行了扩展 #ref("Milner 78")。这种算法在 ML 语言中被实现 #ref("Gordon 79") #ref("Milner 84")。这种类型系统和 Algol 68 一样支持编译期检查、强类型和高阶函数，但因为它允许多态 —— 也就是定义在多种类型的参数上具有统一行为的函数，所以它更加灵活。

Milner 的多态类型检查算法是非常成功的：它健全、高效、功能丰富且灵活。它也可以被用于在没有类型信息（untyped）或者只有部分类型信息（partially typed）的程序中推导出类型。

然而，多态类型检查只在一小部分人群中得到了使用。目前的出版物中只有 #ref("Milner 78") 描述了这个算法，并且其行文相对专业，更多地面向理论背景。

为了让这个算法能够为更多的人所接受，我们现在提供了一个 ML 实现，这个实现非常类似于 LCF，Hope 和 ML #ref("Gordon 79") #ref("Burstall 80") #ref("Milner 84") 中所使用的实现。尽管有时候人们会为了逻辑清晰而牺牲性能，但这个实现还是相对高效的，并且可以被实际地用于大型程序的类型检查。

本文中的 ML 实现只考虑了类型检查中最基本的情况，并且许多对常见编程语言结构的扩展都相当明显。目前已知的非平凡扩展（本文不会讨论）包括重载、抽象数据类型、异常处理、可更新的数据、带标签的记录（labelled record）以及 联合（union）类型。许多其他的扩展仍然处于研究之中，并且人们普遍认为在类型检查的理论与实践中，重要的发现尚未浮出水面。

= 一个简单的应用序（Applicative）语言

本文所使用的语言是一个简单的带有常量的类型化 lambda 演算（typed lambda calculus），这被认为是 ML 语言的核心。求值机制（call-by-name 或者 call-by-value）并不影响类型检查。

下面给出表达式的具体语法；相应的抽象语法在本文结尾处由程序中的 `Term` 类型给出（不含解析器与打印）。

```bnf
Term ::= Identifier
       | 'if' Term 'then' Term 'else' Term
       | 'fun' Identifier '.' Term
       | Term Term
       | 'let' Declaration 'in' Term
       | '(' Term ')'

Declaration ::= Identifier '=' Term
              | Declaration 'and' Declaration
              | 'rec' Declaration
              | '(' Declaration ')'
```

只要在初始环境中包含一系列预定义的标识符，就可以向这个语言中引入新的数据类型。这样在扩展语言时就不需要修改语法以及类型检查算法。

例如，以下程序定义了一个阶乘函数，并且对 `0` 应用它：

```ml
let rec factorial n =
    if zero n
    then succ 0
    else (times (pair n (factorial (pred n))))
in factorial 0
```

= 类型
一个类型可以是一个用于表示任意类型的_类型变量（type variable）_，如 $alpha$、$beta$，也可以是一个_类型运算符（type operator）_。$"int"$（整数类型）和 $"bool"$（布尔类型）是_无参（nullary）_类型运算符。而 $->$（函数类型）和 $times$（积类型）这样的_参数化（parametric）_类型运算符则接受一个或者多个类型作为参数。以上运算符最一般化的形式是 $alpha -> beta$（表示任意函数的类型）和 $alpha times beta$（任意序对的类型）。包含类型变量的类型被称为_多态（polymorphic）_的，而不含类型变量的类型被称为_单态（monomorphic）_的。常规的编程语言，例如 Pascal 和 Algol 68 等，其中的类型都是单态的。

如果同一个类型变量在表达式中出现了多次，那么这个表达式表示_上下文依赖（contextual dependencies）_。例如，表达式 $alpha -> alpha$ 表达了函数类型的_定义域（domain）_和_值域（codomain）_之间的上下文依赖。类型检查的过程就是匹配类型运算符和_实例化（instantiate）_类型变量的过程。当实例化一个类型变量时，这个类型变量所在的其他位置必须被替换为相同的类型。例如，对于类型变量 $alpha -> alpha$，$"int" -> "int"$、$"bool" -> "bool"$ 和 $(epsilon times xi) -> (epsilon times xi)$ 都是合法的实例化。依据上下文进行实例化的过程是通过_归一化（unification）_#ref("Robinson 65") 来完成的，这也是多态类型检查的基础。当匹配过程遇到两个不同的类型运算符（例如 `int` 和 `bool`），或是尝试将类型变量实例化为一个包含它自身的项目（例如将 $alpha$ 实例化为 $alpha -> beta$，这会产生一个循环结构）时，匹配过程会失败。后者通常会在对_自应用（self-applicative）_（例如 `fun x. (x x)`）的表达式进行类型检查时出现，因而这种表达式是不合法的。

我们来看一个简单的例子。恒等函数 `I = fun x. x` 具有类型 $alpha -> alpha$，因为它将任何类型映射到它自身。在表达式 `(I 0)` 中，`0` 的类型（也就是 $"int"$）被匹配为函数 `I` 的定义域，于是在这个上下文中，`I` 的类型被_特化（specialize）_为 $"int" -> "int"$，于是 `(I 0)` 的类型就是这个特化的 `I` 的值域类型，也就是 $"int"$。

一般而言，表达式的类型是由一系列原语运算符的类型和与语言结构对应的类型结合规则确定的。初始环境可为布尔、整数、序对和列表包含以下原语（其中 #raw(sym.arrow) 是函数类型运算符，`list` 是列表类型运算符，#raw(sym.times) 是笛卡尔积）：

$
  & "true", "false" &:& "bool" \
  & 0, 1, ... &:& "int" \
  & "succ", "pred" &:& "int" -> "int" \
  & "zero" &:& "int" -> "bool" \
  & "pair" &:& alpha -> beta -> (alpha times beta) \
  & "fst" &:& (alpha times beta) -> alpha \
  & "snd" &:& (alpha times beta) -> beta \
  & "nil" &:& alpha "list" \
  & "cons" &:& (alpha times alpha "list") -> alpha "list" \
  & "hd" &:& alpha "list" -> alpha \
  & "tl" &:& alpha "list" -> alpha "list" \
  & "null" &:& alpha "list" -> "bool"
$

= `length` 函数的类型

在描述类型检查算法之前，让我们先来探讨一下下面这个计算列表长度的简单递归程序的类型：

```ml
let rec length =
    fun l .
        if null l
        then 0
        else succ (length (tl l))
```

（为了方便接下来的讨论，我们没有使用等效但更优雅的 `length l = ...` 写法，而是写作 `length = fun l . ...`）

`length` 的类型是 #raw(sym.alpha + " list " + sym.arrow + " int")，这是一个泛型类型，因为 `length` 函数可以对任意类型的列表使用。们可以使用两种方式来描述我们推导出这一类型的过程。原理上来说，类型检查就是建立一个由_类型约束（type constraint）_组成的系统，然后求解这个系统中的类型变量。实践上来说，类型检查是自下而上地审视整个程序，在向根部上升的过程中匹配并综合类型；表达式的类型通过其子表达式的类型和上下文中包含的类型约束计算而来，而预定义标识符的类型已经包含在初始环境中。我们审视程序并进行匹配的顺序并不会影响最终的结果，这是类型系统和类型检查算法的重要特性之一。

#let arena = "b1"
#let l(numbering) = [
  #set text(style: "italic", font: "Noto Serif", size: 9pt)
  #text(str(numbering) + ".", fill: rgb(0, 127, 255), style: "italic") #label(arena + "." + str(numbering))
]
#let j(numbering) = [
  #set text(style: "italic", font: "Noto Serif", size: 9pt)
  #link(label(arena + "." + str(numbering)))[#str(numbering)]
]
#let jf(s, e) = [
  #set text(style: "italic", font: "Noto Serif", size: 9pt)
  #link(label(arena + "." + str(s)))[#str(s)\~#str(e)]
]
#let js(..numbers) = {
  numbers.pos().map(n => j(n)).join(",")
}

#let ex(tag) = [
  #set text(style: "italic", font: "Noto Serif", size: 9pt)
  #text("[" + tag + "]", fill: rgb(0, 127, 255), style: "italic") #label(tag)
]
#let jex(tag) = [
  #set text(style: "italic", font: "Noto Serif", size: 9pt)
  #link(label(tag))[#str(tag)]
]

`length` 函数的类型约束系统是：

$
  & #l(1) && "null" &:& alpha "list" -> "bool" \
  & #l(2) && "tl" &:& beta "list" -> beta "list" \
  & #l(3) && 0 &:& "int" \
  & #l(4) && "succ" &:& "int" -> "int" \
\
\
  & #l(5) && "null" l &:& "bool" \
  & #l(6) && 0 &:& gamma \
  & #l(7) && "succ" ("length" ("tl" l)) &:& gamma \
  & #l(8) && "if" "null" l "then" 0 \
  &&& "else" "succ" ("length" ("tl" l)) &:& gamma \
\
\
  & #l(9) && "null" &:& delta -> epsilon \
  & #l(10) && l &:& delta \
  & #l(11) && "null" l &:& epsilon \
\
\
  & #l(12) && "tl" &:& phi -> xi \
  & #l(13) && l &:& phi \
  & #l(14) && "tl" l &:& xi \
  & #l(15) && "length" &:& theta -> iota \
  & #l(16) && "tl" l &:& theta \
  & #l(17) && "length" ("tl" l) &:& iota \
\
\
  & #l(18) && "succ" &:& kappa -> lambda \
  & #l(19) && "length" ("tl" l) &:& kappa \
  & #l(20) && "succ" ("length" ("tl" l)) &:& lambda \
\
\
  & #l(21) && l &:& mu \
  & #l(22) && "if" "null" l "then" 0 \
  &&& "else" "succ" ("length" ("tl" l)) &:& nu \
  & #l(23) && "fun" l . "if" "null" l "then" 0 \
  &&& "else" "succ" ("length" ("tl" l)) &:& mu -> nu \
\
\
  & #l(24) && "length" &:& pi \
  & #l(25) && "fun" l . "if" "null" l "then" 0 \
  &&& "else" "succ" ("length" ("tl" l)) &:& pi
$

行 #jf(1, 4) 代表预定义全局标识符的类型约束，这部分信息是已知的。条件结构（整个 `if` 表达式，译者注）施加了约束 #jf(5, 8)：测试（`null l`）的结果必须是布尔型，并且两个分支表达式必须具有相同的类型 $gamma$。$gamma$ 同时也是整个条件表达式的类型。程序中的四个函数调用施加了约束 #jf(9, 20)：对于函数调用而言，函数符号必须具有一个函数类型（例如 #j(9) 中的 $delta -> epsilon$）；参数必须具有和函数定义域相同的类型（例如 #j(10) 中的 $delta$）；函数调用的结果必须具有和函数值域相同的类型（例如 #j(11) 中的 $epsilon$）。整个 lambda 表达式 #j(23) 具有类型 $mu -> nu$。

对 `length` 函数作类型检查需要：(i) 确保整个约束系统是一致的（比如绝对不能推导出 $"int" = "bool"$），并且 (ii) 对 $pi$ 求解这些约束。`length` 的类型可以按照如下方式推出：

$
  pi = mu -> nu & "by" [25, 23] \
  nu = phi = beta "list" & "by" [21, 13, 12, 12] \
  nu = gamma = "int" & "by" [22, 8, 6, 3]
$

还需要更多工作才能证明 $beta$ 完全不受约束并且整个系统是一致的。下一节中描述的类型检查算法会系统性地完成这一工作，像约束系统上的定理证明器一样简单。

下面是一个自下而上的 `length` 函数的类型推导，与类型检查算法实际的操作步骤更为接近；约束的一致性（即没有类型错误）也在过程中得到了检验：

$
  & #l(26) && quad l &:& delta && quad [#j(10)] \
  & #l(27) && quad "null" l &:& "bool" \
  &&&         quad epsilon = "bool"; delta = alpha "list" && && quad [#js(11, 9, 1)] \
  & #l(28) && quad 0 &:& "int" \
  &&&         quad gamma = "int" && && quad [#js(6, 3)] \
  & #l(29) && quad "tl" l &:& beta "list" \
  &&&         quad phi = beta "list"; xi = beta "list"; beta = alpha && && quad [#js(26, 27), #jf(12, 14), #j(2)] \
  & #l(30) && quad "length" ("tl" l) &:& iota \
  &&&         quad theta = beta "list" && && quad [#jf(15, 17), #j(29)] \
  & #l(31) && quad "succ" ("length" ("tl" l)) &:& "int" \
  &&&         quad iota = kappa = "int" && && quad [#jf(18, 20), #js(4, 30)] \
  & #l(32) && quad "if" "null" l "then" 0 \
  &&&         quad "else" "succ" ("length" ("tl" l)) &:& "int" && quad [#jf(5, 8), #js(27, 28, 31)] \
  & #l(33) && quad "fun" l. "if" "null" l "then" 0 \
  &&&         wide "else" "succ" ("length" ("tl" l)) &:& beta "list" -> "int" \
  &&&         quad mu = beta "list"; nu = "int" && && quad [#jf(21, 23), #js(26, 27, 32)] \
  & #l(34) && quad "length" &:& beta "list" -> "int" \
  &&&         quad pi = beta "list" -> "int" && && quad [#js(24, 25, 33, 15, 30, 31)]
$

注意上面的过程已经处理了递归：#j(34) 比较了 `length` 函数的两个实例（函数定义处和递归调用处）的类型。

= 类型检查
基本的算法可以被描述为：
+ 当 lambda 绑定引入一个新变量 `x` 时，赋予它一个全新的类型变量 $alpha$，表示它的类型有待根据它出现的上下文进一步确定。将序对 <`x`, $alpha$> 存储到一个环境（在程序中称作 `TypeEnv`）中。每当变量 `x` 出现时，从环境中检索 `x` 并提取出 $alpha$（或是它的任何一个介入实例化）作为 `x` 在此处的类型。
+ 在条件结构中，将 `if` 条件的类型与 $"bool"$ 进行匹配，将 `then` 和 `else` 分支的类型归一化以确保整个表达式具有一个类型。
+ 在函数抽象 `fun x. e` 中，创建一个新的上下文而，为 `x` 赋予一个全新的类型变量，然后在这个上下文中推断 `e` 的类型。
+ 在函数应用 `f a` 中，将 `f` 的类型与 $A -> beta$ 归一化，其中 $A$ 是 `a` 的类型，而 $beta$ 是一个全新的类型变量。也就是说，`f` 必须具有函数类型，并且其定义域可以和 $A$ 归一化；整个函数应用的类型是 $beta$（或是其任何一个实例化）。

要描述 `let` 表达式及其引入变量的类型检查，我们需要引入_泛化（generic）_类型变量记号。考虑以下表达式：

#raw("fun f. pair (f 3) (f true)", lang: "ml") #ex("Ex1")

在 Milner 的类型系统中，这个表达式无法被类型检查，而上述算法会给出一个类型错误。事实上，`f` 的第一次出现（`f 3`）先给出 `f` 的类型是 $"int" -> beta$，随后第二次出现（`f true`）又给出了一个类型 $"bool" -> beta$，而它无法与第一个类型归一化。

像 `f` 这样由 `lambda` 引入的标识符，它的类型变量是_非泛化（non-generic）_的。因为就像这个例子中所展现的，类型变量在 `f` 出现的所有地方共享，并且他们的实例可能会有冲突。

你可以试着给表达式 #jex("Ex1") 一个类型，例如你可以试着给它 $(alpha times beta) -> (beta times beta)$。这在 `f (fun a. 0)` 这样的场景下是可以的，它能正常得到结果 `(pair 0 0)`。然而这种类型系统总的来说是_不健全（unsound）_的：例如 `succ` 的类型可以与 $alpha -> beta$ 匹配，因而会被 `f` 接受，并被错误地应用到 `true` 上。Milner 的类型系统有一些健全的扩展能处理 #jex("Ex1") 这样的表达式，但它们不在讨论本文的范围内。

因此，为 `lambda` 引入的标识符的_异质（heterogeneous）_使用标定类型是一个基本问题。实践中这基本上是可以接受的，因为像 #jex("Ex1") 这样的表达式不是很有用，也不是特别必要。我们需要在 `let` 引入的标识符的异质使用问题上做得更好。考虑以下表达式：

#raw("let f = fun a. a\nin pair (f 3) (f true)", lang: "ml") #ex("Ex2")

必须找到一种办法来为上述表达式标定类型，否则多态函数就没法在同一个上下文里被应用到不同的类型上，多态也就没有用了。好在我们这里的局面比 #jex("Ex1") 要好，因为我们确切地知道 `f` 是什么，并且可以利用这一信息来分别处理它的两次出现。

在这个例子中，`f` 具有类型 $alpha -> alpha$；像 $alpha$ 这样出现在 `let` 引入的标识符的类型（并且不在_包裹_的 `lambda` 引入的标识符类型中出现）的类型变量，我们称它为_泛化（generic）_的。在 `let` 引入的标识符的不同实例化中，泛化的类型变量可以有不同的值。实现时，可以为 `f` 的每次出现创建一个 `f` 的拷贝。

不过，在复制一个类型的时候，我们必须小心，不要复制非泛化的类型变量。非泛化的类型变量必须被共享。以下表达式和 #jex("Ex1") 一样是不合法的，因为 `g` 的类型是非泛化的，而这个类型会被传播到 `f` 中：

#raw("fun g. let f = g\nin pair (f 3) (f true)", lang: "ml") #ex("Ex3")

同样地，你不能给这个表达式一个像 $(alpha -> beta) -> (beta times beta)$ 这样的类型（考虑对这个表达式应用 `succ`）。

泛化变量的定义是：

表达式 `e` 的类型中的一个类型变量是泛化的，当且仅当它不出现在任何包裹着表达式 `e` 的 `lambda` 表达式的绑定器中。（_原文： A type variable occurring in the type of an expression `e` is generic iff it does not occur in the type of the binder of any lambda-expression enclosing `e`._）

注意一个在 lambda 表达式内部非泛化的类型变量，在表达式外部可能是泛化的。例如在 #jex("Ex2") 中，`a` 的类型 $alpha$ 是非泛化的，而 `f` 的类型 $alpha -> alpha$ 是泛化的。

要确定一个变量是否是泛化的，我们随时维护一个非泛化变量的列表：若类型变量不在这个列表中，则它是泛化的。每当进入 lambda 表达式时扩充该列表；而每当离开 lambda 表达式时恢复原先的列表，这样 lambda 表达式引入的类型变量就又泛化了。当复制一个类型的时候，我们必须只赋值泛化的变量，非泛化的变量则应该被共享。在将非泛化类型变量归一化到一个项目（term）上时，该项目中包含的所有类型变量都会变为非泛化的。

最后我们需要考虑递归定义：

```ml
let rec f = ... f ...
in ... f ...
```

我们可以将 `rec` 用 $Y$ 不动点（具有类型 $(alpha -> alpha) -> alpha$）展开：

```ml
let f = Y fun f. ... f ...
in ... f ...
```

显然可知，在递归定义中的 `f` 的实例（中的类型变量）必须是非泛化的，而在 `in` 中的实例是泛化的。

5. 要对 `let` 作类型检查，我们首先检查它的声明部分，获得一个包含标识符与类型的环境，这个环境之后会用于 `let` _体（body）_的检查
6. 检查 `let` 的声明部分时，检查其中所有的定义 $x_i = t_i$，每个定义会在环境中引入一个序对 <$x_i$, $T_i$>，其中 $T_i$ 是 $t_i$ 的类型。对于存在（互）递归的声明 $x_i = t_i$，我们首先为所有要定义的 $x_i$ 创建一个包含序对 <$x_i$, $alpha_i$> 的环境，这里 $alpha_i$ 是非泛化的类型变量（它们在进入声明作用域的时候被插入到非泛化变量的列表中）。所有的 $t_i$ 在这个环境中进行类型检查，然后再将 $T_i$ 与 $alpha_i$（或是其实例化）进行匹配。

= 关于模型、推理系统和算法的题外话
有两种方法能形式化地描述类型的语义。最基本方式的是给设计一个数学模型，通常是将每个类型表达式映射到一组值（具有该类型的值）；这里的基本困难在于找到 $->$ 运算符的数学含义 #ref("Scott 76") #ref("Milner 78") #ref("MacQueen 84")。

另一种与之互补的方法是定义一个由公理（axiom）和推理规则组成的形式系统，在这个系统中可以证明一个表达式具有某种类型。语义模型和形式系统之间的联系非常紧密。语义模型通常是定义一个形式化系统的指南，并且每个形式系统必须是自洽的，这通常通过展示它的语义模型来体现。

在一个好的形式系统中，我们基本上可以证明我们“已知”的所有东西为真（根据直觉，或者因为它在语义模型里就是为真的）。在有了一个好的形式系统之后，我们“差不多”就可以忘记语义模型而，后续的工作就会轻松很多。

相比于语义模型，类型检查和形式系统的关系更加严格，这是其句法的（syntactic）性质所决定的。类型检查算法一定程度上来说就是在实现一个形式系统，通过向该系统提供一个证明定理的过程。形式系统比任何算法都更简单也更基础，所以类型检查算法的最简形式就是它所实现的形式系统。此外，在设计一个类型检查算法时，最好首先为其定义一个形式系统。

并非所有的形式系统都能支持类型检查算法。如果一个形式系统过于强大（比如说，我们可以用它证明很多东西），那么它很可能是_不可决断的（undecidable）_，因而无法为其设计一个决策过程。类型检查通常仅限于可决断的类型系统，在这些类型系统上可以设计类型检查算法。不过有时不可决断的类型系统可以用不完备的_启发式（heuristcs）_类型检查处理（截至发文为止尚无实践），这些类型检查算法只尝试在这个系统中证明命题，但可能在某些时候放弃。实践上来说这是可以接受的，因为程序的复杂度总得有个显示：its meaning could get out of hand long before the limits of the typechecking heuristics are reached.

即使是可决断的类型系统，所有类型检查算法也可能是指数复杂度的，这也需要用启发式方法来处理。人们已经在多态类型系统中处理重载时成功地运用了这一方法 #ref("Burstall 80")。

下一节展示了一个用于多态类型检查的推理系统。现在我们对类型检查有了两种不同的视角：一种是“求解由类型方程组成的系统”，我们在前面已经看到了，而另一种就是“在形式系统中证明命题”，我们接下来会看到的。这两种视角之间可以互换，但后者提供了更多的见解，因为它将类型的语义和算法连接了起来。

= 一个推理系统
在接下来的推理系统中，类型的语法被扩展为类型量词 $forall alpha. tau$. 在 Milner 的类型系统中，所有类型变量都是隐式地在顶层被量化的。例如，$alpha -> beta$ 实际上是 $forall alpha. forall beta. alpha -> beta$。然而，量词不能在类型表达式中嵌套。

如果一个类型具有形式 $forall alpha_1. ... forall alpha_n. tau$，其中 $n >= 0$ 且 $tau$ 中没有量词，则我们说这个类型是_浅显（shallow）_的。我们的推理系统允许构造非浅显的类型，但不幸的是没有类型检查算法能被用在它们上面。因此，我们只关心浅显类型的推理。我们引入量词是因为这有助于解释泛化/非泛化类型变量的行为，它们可以与自由/量化类型变量完全对应。#ref("Damas 82") 中则提出了一种略微不同的推理系统，其中规避了非浅显的类型。

以下是推理规则集合。其中 [VAR] 是公理，其他规则都是推理。横线读作“蕴含”。记号 $A tack e : tau$ 表示给定一个假设集合 $A$，我们可以推导出表达式 $e$ 具有类型 $tau$。一个假设就是表达式 $e$ 中一个变量的类型，它可以是自由类型。记号 $A. x : tau$ 表示将集合 $A$ 与假设 $x : tau$ 取并集；记号 $tau[sigma\/alpha]$ 表示将 $tau$ 中 $alpha$ 的所有自由出现替换为 $sigma$。

$
  & "[VAR]" wide && A.x : tau tack x : tau \
  \
  & "[COND]" wide && frac(
    A tack e : "bool" quad A tack e' : tau quad A tack e'' : tau,
    A tack ("if" e "then" e' "else" e'') : tau
  ) \
  \
  & "[ABS]" wide && frac(
    A.x : sigma tack e : tau,
    A tack (lambda x. e) : sigma -> tau
  ) \
  \
  & "[COMB]" wide && frac(
    A tack e : sigma -> tau quad A tack e' : sigma,
    A tack (e compose e') : tau
  ) \
  \
  & "[LET]" wide && frac(
    A tack e' : sigma quad A.x : sigma tack e : tau,
    A tack ("let" x = e' "in" e) : tau
  ) \
  \
  & "[REC]" wide && frac(
    A.x : tau tack e : tau,
    A tack ("rec" x. e) : tau
  ) \
  \
  & "[GEN]" wide && frac(
    A tack e : tau,
    A tack e : forall alpha . tau
  ) wide (alpha "not free in" A) \
  \
  & "[SPEC]" wide && frac(
    A tack e : forall alpha . tau,
    A tack e : tau[sigma \/ alpha]
  )
$

#set heading(numbering: none)
#let ref-target(txt) = [
  #text("[" + txt + "]", fill: rgb(0, 127, 255)) #label(txt)
]
= 参考文献
#ref-target("Burstall 80") R.Burstall, D.MacQueen, D.Sannella: "Hope: an Experimental Applicative Language", Conference Record of the 1980 LISP Coference, Stanford, August 1980, pp. 136-143.

#ref-target("Damas 82") L.Damas, R.Milner: "Principal type-schemes for functional programs", Proc. POPL 82, pp. 207-212.

#ref-target("Gordon 79") M.J.Gordon, R.Milner, C.P.Wadsworth: "Edinburgh LCF", Lecture Notes in Computer Science, No. 78, Springer-Verlag, 1979.

#ref-target("Hindley 69") R.Hindley: "The principal type scheme of an object in combinatory logic", Transactions of the American Mathematical Society, Vol. 146, Dec 1969, pp. 29-60.

#ref-target("MacQueen 84") D.B.MacQueen, R.Sethi, G.D.Plotkin: "An ideal model for recursive polymorphic types", Proc. Popl 84.

#ref-target("Milner 78") R.Milner: "A theory of type polymorphism in programming", Journal of Computer and System Sciences, No. 17, 1978.

#ref-target("Milner 84") R.Milner: "A proposal for Standard ML", Proc. of the 1984 ACM Symposium on Lisp and Functional Programming, Aug 1984.

#ref-target("Robinson 65") J.A.Robinson: "A machine-oriented logic based on the resolution principle", Journal of the ACM, Vol 12, No. 1, Jan 1965, pp. 23-49.

#ref-target("Scott 76") D.S.Scott: "Data types as lattices". SIAM Journal of Computing, 4, 1976.