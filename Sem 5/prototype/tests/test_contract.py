import pytest
from web3.exceptions import ContractLogicError

from blockchain.chain import AuditChain

H = "ab" * 32
A, B = bytes.fromhex("11" * 32), bytes.fromhex("22" * 32)


@pytest.fixture()
def chain(chain_available, tmp_path):
    return AuditChain(deployment_file=tmp_path / "d.json")


def test_log_and_read_back(chain):
    r = chain.log_decision(H, "AUTO_BLOCK", 0.9123, "11" * 32, "22" * 32)
    e = chain.get_entry(r["entry_id"])
    assert e["decision"] == "AUTO_BLOCK" and e["risk_score"] == 0.9123
    assert e["decision_hash"] == "11" * 32 and e["shap_hash"] == "22" * 32
    assert chain.stats()["AUTO_BLOCK"] == 1


def test_entries_are_append_only(chain):
    names = {f["name"] for f in chain.build["abi"] if f["type"] == "function"}
    assert not any(n.startswith(("update", "delete", "remove", "edit", "modify", "set")) for n in names)


def test_only_authorised_engine_can_write(chain):
    outsider = chain.w3.eth.accounts[3]
    with pytest.raises(ContractLogicError):
        chain.contract.functions.logDecision(bytes.fromhex(H), 0, 100, A, B).call({"from": outsider})


def test_owner_can_authorise_and_revoke(chain):
    other = chain.w3.eth.accounts[4]
    chain.contract.functions.authorizeEngine(other).transact({"from": chain.engine_account})
    chain.contract.functions.logDecision(bytes.fromhex(H), 1, 5000, A, B).transact({"from": other})
    chain.contract.functions.revokeEngine(other).transact({"from": chain.engine_account})
    with pytest.raises(ContractLogicError):
        chain.contract.functions.logDecision(bytes.fromhex(H), 1, 5000, A, B).call({"from": other})


def test_non_owner_cannot_authorise(chain):
    with pytest.raises(ContractLogicError):
        chain.contract.functions.authorizeEngine(chain.w3.eth.accounts[5]).call({"from": chain.w3.eth.accounts[6]})


def test_risk_score_above_one_is_rejected(chain):
    with pytest.raises(ContractLogicError):
        chain.contract.functions.logDecision(bytes.fromhex(H), 0, 10001, A, B).call({"from": chain.engine_account})


def test_review_resolution_rules(chain):
    approve = chain.log_decision(H, "AUTO_APPROVE", 0.01, "11" * 32, "22" * 32)["entry_id"]
    review = chain.log_decision(H, "MANUAL_REVIEW", 0.5, "33" * 32, "44" * 32)["entry_id"]
    frm = {"from": chain.engine_account}
    with pytest.raises(ContractLogicError):          # only reviews can be resolved
        chain.contract.functions.resolveReview(approve, 2, bytes.fromhex(H), bytes.fromhex(H)).call(frm)
    with pytest.raises(ContractLogicError):          # final decision cannot be 'review'
        chain.contract.functions.resolveReview(review, 1, bytes.fromhex(H), bytes.fromhex(H)).call(frm)
    chain.resolve_review(review, "AUTO_BLOCK", H, "55" * 32)
    assert chain.get_resolution(review)["final_decision"] == "AUTO_BLOCK"
    assert chain.get_entry(review)["decision"] == "MANUAL_REVIEW"       # original entry untouched
    with pytest.raises(ContractLogicError):          # only once
        chain.contract.functions.resolveReview(review, 2, bytes.fromhex(H), bytes.fromhex(H)).call(frm)


def test_unknown_entry_reverts(chain):
    with pytest.raises(ContractLogicError):
        chain.contract.functions.getEntry(999).call()


def test_subscriber_index(chain):
    a = chain.log_decision(H, "AUTO_APPROVE", 0.0, "11" * 32, "22" * 32)["entry_id"]
    b = chain.log_decision(H, "AUTO_BLOCK", 0.99, "33" * 32, "44" * 32)["entry_id"]
    assert chain.contract.functions.getSubscriberEntries(bytes.fromhex(H)).call() == [a, b]
