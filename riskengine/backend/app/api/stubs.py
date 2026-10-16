"""Module endpoints. Honest 501s until the modules exist: nothing here fabricates a result."""
from fastapi import APIRouter, HTTPException

router = APIRouter()


def _nyi(what: str):
    raise HTTPException(501, f"{what} is not implemented yet (planned for a later phase).")


@router.get("/portfolio", tags=["module-a"], summary="Current index portfolio (Module A)")
def portfolio():
    _nyi("Module A portfolio")


@router.post("/rebalance", tags=["module-a"], summary="Rebalance the index from current signals (Module A)")
def rebalance():
    _nyi("Module A rebalancing")


@router.post("/stress-test", tags=["module-b"], summary="Run an event-driven stress test (Module B)")
def stress_test():
    _nyi("Module B stress testing")
