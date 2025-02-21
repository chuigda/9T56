from enum import Enum


class Greek(Enum):
    Alpha = 'α'
    Beta = 'β'
    Gamma = 'γ'
    Delta = 'δ'
    Epsilon = 'ε'
    Pi = 'π'
    Sigma = 'σ'
    Tau = 'τ'
    Eta = 'η'

    def __str__(self) -> str:
         return self.value
