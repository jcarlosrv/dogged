from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")
R_co = TypeVar("R_co", covariant=True)