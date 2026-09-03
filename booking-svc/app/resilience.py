import pybreaker

from .observability import logger


class _BreakerStateLogger(pybreaker.CircuitBreakerListener):
    """Loguea cada vez que el circuit breaker cambia de estado, para que se
    vea claramente en los logs cuándo se abre y cuándo se cierra."""

    def state_change(self, cb, old_state, new_state):
        logger.warning(
            "circuit_breaker_state_change",
            breaker=cb.name,
            old_state=old_state.name,
            new_state=new_state.name,
        )


# fail_max=3: 3 fallos seguidos abren el circuito.
# reset_timeout=30: pasados 30s, prueba una vez más (half-open).
notif_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=30,
    listeners=[_BreakerStateLogger()],
    name="notif-svc",
)
