// Biên dịch EnergyCertificate.sol bằng solc-js -> contracts/build/EnergyCertificate.json (abi + bytecode)
const solc = require("solc"), fs = require("fs"), path = require("path");
const file = path.join(__dirname, "..", "contracts", "EnergyCertificate.sol");
const input = {
  language: "Solidity",
  sources: { "EnergyCertificate.sol": { content: fs.readFileSync(file, "utf8") } },
  settings: { optimizer: { enabled: true, runs: 200 }, outputSelection: { "*": { "*": ["abi", "evm.bytecode.object"] } } },
};
const out = JSON.parse(solc.compile(JSON.stringify(input)));
(out.errors || []).forEach(e => console.error(e.formattedMessage));
if ((out.errors || []).some(e => e.severity === "error")) process.exit(1);
const c = out.contracts["EnergyCertificate.sol"]["EnergyCertificate"];
const dir = path.join(__dirname, "..", "contracts", "build");
fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(path.join(dir, "EnergyCertificate.json"), JSON.stringify({ abi: c.abi, bytecode: "0x" + c.evm.bytecode.object }, null, 2));
console.log("Compiled OK, bytecode bytes:", c.evm.bytecode.object.length / 2);
