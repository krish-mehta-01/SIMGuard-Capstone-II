// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title  SIMSwapAuditLog
 * @notice Append-only, tamper-evident audit trail for SIM replacement decisions.
 *
 * What goes on-chain
 *   - a pseudonymous subscriber reference (HMAC of the MSISDN, never the number)
 *   - the three-tier decision and the composite risk score (basis points)
 *   - SHA-256 of the canonical decision record
 *   - SHA-256 of the canonical SHAP explanation (the reasoning behind the decision)
 * The full record and the human-readable explanation stay off-chain in the
 * operator's database. Anyone can later recompute both hashes from that record and
 * compare them with the values stored here, so any after-the-fact edit is exposed.
 *
 * Access control
 *   - owner: authorises / revokes risk-engine addresses
 *   - authorised engine: the only address allowed to append entries
 *   - nobody (including the owner) can modify or delete an existing entry
 */
contract SIMSwapAuditLog {
    enum Decision { AUTO_APPROVE, MANUAL_REVIEW, AUTO_BLOCK }

    // Packs into four storage slots.
    struct AuditEntry {
        bytes32 subscriberRef;
        bytes32 decisionHash;
        bytes32 shapHash;
        uint48  timestamp;
        uint16  riskBps;       // composite risk score x 10000
        Decision decision;
        address loggedBy;
    }

    struct Resolution {
        Decision finalDecision;
        bytes32  analystRef;   // pseudonymous analyst identifier
        bytes32  noteHash;     // SHA-256 of the analyst's written justification
        uint48   timestamp;
        address  resolvedBy;
    }

    address public owner;
    uint256 public entryCount;
    uint256[3] public decisionCounts;

    mapping(uint256 => AuditEntry) private entries;
    mapping(uint256 => Resolution) private resolutions;
    mapping(uint256 => bool) public isResolved;
    mapping(address => bool) public authorizedEngines;
    mapping(bytes32 => uint256[]) private subscriberEntries;

    event DecisionLogged(
        uint256 indexed entryId,
        bytes32 indexed subscriberRef,
        Decision decision,
        uint16 riskBps,
        bytes32 decisionHash,
        bytes32 shapHash
    );
    event ReviewResolved(
        uint256 indexed entryId,
        Decision finalDecision,
        bytes32 analystRef,
        bytes32 noteHash
    );
    event EngineAuthorized(address indexed engine);
    event EngineRevoked(address indexed engine);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    error NotOwner();
    error NotAuthorizedEngine();
    error InvalidScore();
    error UnknownEntry();
    error NotPendingReview();
    error AlreadyResolved();
    error InvalidFinalDecision();
    error ZeroAddress();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlyEngine() {
        if (!authorizedEngines[msg.sender]) revert NotAuthorizedEngine();
        _;
    }

    constructor() {
        owner = msg.sender;
        authorizedEngines[msg.sender] = true;
        emit OwnershipTransferred(address(0), msg.sender);
        emit EngineAuthorized(msg.sender);
    }

    // ---------------------------------------------------------------- admin

    function authorizeEngine(address engine) external onlyOwner {
        if (engine == address(0)) revert ZeroAddress();
        authorizedEngines[engine] = true;
        emit EngineAuthorized(engine);
    }

    function revokeEngine(address engine) external onlyOwner {
        authorizedEngines[engine] = false;
        emit EngineRevoked(engine);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    // ----------------------------------------------------------- write path

    function logDecision(
        bytes32 subscriberRef,
        Decision decision,
        uint16 riskBps,
        bytes32 decisionHash,
        bytes32 shapHash
    ) external onlyEngine returns (uint256 id) {
        if (riskBps > 10000) revert InvalidScore();

        id = entryCount++;
        entries[id] = AuditEntry({
            subscriberRef: subscriberRef,
            decisionHash: decisionHash,
            shapHash: shapHash,
            timestamp: uint48(block.timestamp),
            riskBps: riskBps,
            decision: decision,
            loggedBy: msg.sender
        });
        subscriberEntries[subscriberRef].push(id);
        decisionCounts[uint8(decision)]++;

        emit DecisionLogged(id, subscriberRef, decision, riskBps, decisionHash, shapHash);
    }

    /// @notice Record the human analyst's outcome for a MANUAL_REVIEW entry.
    ///         The original entry is never modified; the resolution is a second record.
    function resolveReview(
        uint256 entryId,
        Decision finalDecision,
        bytes32 analystRef,
        bytes32 noteHash
    ) external onlyEngine {
        if (entryId >= entryCount) revert UnknownEntry();
        if (entries[entryId].decision != Decision.MANUAL_REVIEW) revert NotPendingReview();
        if (isResolved[entryId]) revert AlreadyResolved();
        if (finalDecision == Decision.MANUAL_REVIEW) revert InvalidFinalDecision();

        isResolved[entryId] = true;
        resolutions[entryId] = Resolution({
            finalDecision: finalDecision,
            analystRef: analystRef,
            noteHash: noteHash,
            timestamp: uint48(block.timestamp),
            resolvedBy: msg.sender
        });
        emit ReviewResolved(entryId, finalDecision, analystRef, noteHash);
    }

    // ------------------------------------------------------------ read path

    function getEntry(uint256 id) external view returns (AuditEntry memory) {
        if (id >= entryCount) revert UnknownEntry();
        return entries[id];
    }

    function getResolution(uint256 id) external view returns (Resolution memory) {
        if (!isResolved[id]) revert UnknownEntry();
        return resolutions[id];
    }

    /// @notice Compare off-chain recomputed hashes with the anchored ones.
    function verifyEntry(uint256 id, bytes32 decisionHash, bytes32 shapHash)
        external
        view
        returns (bool decisionOk, bool shapOk)
    {
        if (id >= entryCount) revert UnknownEntry();
        AuditEntry storage e = entries[id];
        return (e.decisionHash == decisionHash, e.shapHash == shapHash);
    }

    function getSubscriberEntries(bytes32 subscriberRef) external view returns (uint256[] memory) {
        return subscriberEntries[subscriberRef];
    }

    function getStats() external view returns (uint256 total, uint256 approved, uint256 review, uint256 blocked) {
        return (entryCount, decisionCounts[0], decisionCounts[1], decisionCounts[2]);
    }
}
