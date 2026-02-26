import secrets
from typing import Optional

class SecureRandom:
    """
    Cryptographically secure random number generator.
    Uses secrets module which provides access to the OS's secure random source.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the secure RNG.
        
        Note: The seed parameter is accepted for API compatibility but is
        ignored when using cryptographically secure randomness. For reproducible
        simulations (e.g., testing), use the standard random.Random class.
        """
        self._seed = seed
        self._use_secure = seed is None
        if not self._use_secure:
            # If seed provided, use standard random for reproducibility
            import random
            self._fallback_rng = random.Random(seed)
    
    def randint(self, a: int, b: int) -> int:
        """Return a random integer N such that a <= N <= b."""
        if self._use_secure:
            return secrets.randbelow(b - a + 1) + a
        return self._fallback_rng.randint(a, b)
    
    def choice(self, seq):
        """Return a random element from the non-empty sequence."""
        if self._use_secure:
            return secrets.choice(seq)
        return self._fallback_rng.choice(seq)
    
    def random(self) -> float:
        """Return a random float in [0.0, 1.0)."""
        if self._use_secure:
            return secrets.randbelow(2**53) / (2**53)
        return self._fallback_rng.random()
    
    def shuffle(self, x):
        """Shuffle list x in place."""
        if self._use_secure:
            # Fisher-Yates shuffle using secure random
            for i in range(len(x) - 1, 0, -1):
                j = secrets.randbelow(i + 1)
                x[i], x[j] = x[j], x[i]
        else:
            self._fallback_rng.shuffle(x)