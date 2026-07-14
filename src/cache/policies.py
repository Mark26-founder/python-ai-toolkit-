"""Eviction policies for controlling cache size and storage limits."""

from collections import OrderedDict
from typing import Optional, Protocol


class EvictionPolicy(Protocol):
    """Protocol defining the interface for cache eviction policies."""

    def record_access(self, key: str) -> None:
        """Invoked when a cache key is retrieved."""
        ...

    def record_insert(self, key: str) -> None:
        """Invoked when a cache key is inserted or updated."""
        ...

    def record_delete(self, key: str) -> None:
        """Invoked when a cache key is removed."""
        ...

    def evict(self) -> Optional[str]:
        """Suggests a key to evict. Returns None if empty."""
        ...


class LRUPolicy:
    """Least Recently Used (LRU) eviction policy."""

    def __init__(self) -> None:
        self._keys: OrderedDict[str, None] = OrderedDict()

    def record_access(self, key: str) -> None:
        if key in self._keys:
            self._keys.move_to_end(key)

    def record_insert(self, key: str) -> None:
        if key in self._keys:
            self._keys.move_to_end(key)
        else:
            self._keys[key] = None

    def record_delete(self, key: str) -> None:
        self._keys.pop(key, None)

    def evict(self) -> Optional[str]:
        if not self._keys:
            return None
        # Pop the oldest (first) item
        key, _ = self._keys.popitem(last=False)
        return key


class FIFOPolicy:
    """First-In, First-Out (FIFO) eviction policy."""

    def __init__(self) -> None:
        self._keys: OrderedDict[str, None] = OrderedDict()

    def record_access(self, key: str) -> None:
        # Access order does not matter for FIFO
        pass

    def record_insert(self, key: str) -> None:
        if key not in self._keys:
            self._keys[key] = None

    def record_delete(self, key: str) -> None:
        self._keys.pop(key, None)

    def evict(self) -> Optional[str]:
        if not self._keys:
            return None
        key, _ = self._keys.popitem(last=False)
        return key


class NoEvictionPolicy:
    """Eviction policy that never suggests eviction."""

    def record_access(self, key: str) -> None:
        pass

    def record_insert(self, key: str) -> None:
        pass

    def record_delete(self, key: str) -> None:
        pass

    def evict(self) -> Optional[str]:
        return None
