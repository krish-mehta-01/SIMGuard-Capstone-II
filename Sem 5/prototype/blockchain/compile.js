// Compiles SIMSwapAuditLog.sol with solc-js and writes build/SIMSwapAuditLog.json
// (ABI + bytecode + compiler metadata) for the Python deployment service.
const fs = require("fs");
const path = require("path");
const solc = require("solc");

const file = "SIMSwapAuditLog.sol";
const source = fs.readFileSync(path.join(__dirname, file), "utf8");

const input = {
  language: "Solidity",
  sources: { [file]: { content: source } },
  settings: {
    optimizer: { enabled: true, runs: 200 },
    evmVersion: "shanghai",
    outputSelection: { "*": { "*": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object"] } },
  },
};

const out = JSON.parse(solc.compile(JSON.stringify(input)));
const errors = (out.errors || []);
errors.forEach((e) => console.log(`${e.severity.toUpperCase()}: ${e.formattedMessage}`));
if (errors.some((e) => e.severity === "error")) process.exit(1);

const c = out.contracts[file].SIMSwapAuditLog;
fs.mkdirSync(path.join(__dirname, "build"), { recursive: true });
fs.writeFileSync(
  path.join(__dirname, "build", "SIMSwapAuditLog.json"),
  JSON.stringify(
    {
      contractName: "SIMSwapAuditLog",
      compiler: solc.version(),
      optimizer: { enabled: true, runs: 200 },
      evmVersion: "shanghai",
      abi: c.abi,
      bytecode: "0x" + c.evm.bytecode.object,
      deployedBytecodeSize: c.evm.deployedBytecode.object.length / 2,
    },
    null,
    2
  )
);
console.log(`Compiled ${file} with solc ${solc.version()}`);
console.log(`Deployed bytecode size: ${c.evm.deployedBytecode.object.length / 2} bytes`);
