import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="session")
def chain_available():
    from web3 import Web3
    from config import RPC_URL
    try:
        ok = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 3})).is_connected()
    except Exception:
        ok = False
    if not ok:
        pytest.skip("local Ethereum node not running (npm run chain)")


@pytest.fixture()
def engine(chain_available):
    """Risk engine with its own empty database and a freshly deployed contract."""
    from blockchain.chain import AuditChain
    from risk_engine.engine import RiskEngine
    from risk_engine.store import Store
    tmp = Path(tempfile.mkdtemp())
    return RiskEngine(store=Store(tmp / "t.db"), chain=AuditChain(deployment_file=tmp / "d.json"))


@pytest.fixture(scope="session")
def test_frame():
    from risk_engine.samples import load_test_frame
    return load_test_frame()
