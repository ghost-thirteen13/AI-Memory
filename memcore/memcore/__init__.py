# memcore/__init__.py
# 对外只暴露门面 Memory，其余模块内部可见。

from .memory import Memory

__all__ = ["Memory"]
