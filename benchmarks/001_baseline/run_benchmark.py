import json
import hashlib
import subprocess
from pathlib import Path

def canon(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode()

def main():
    spec = json.load(open("benchmarks/001_baseline/spec/claim_v1.0.0.json"))
    
    result = subprocess.run(
        ["python", "benchmarks/001_baseline/test/compute.py", str(spec["seed"])],
        capture_output=True, text=True
    )
    
    output = json.loads(result.stdout)

    # M canônico — só métricas + seed (timestamp NÃO entra)
    M = {
        "benchmark": "001_baseline",
        "version": spec["version"],
        "seed": spec["seed"],
        "metrics": output["metrics"]
    }

    h_m = hashlib.sha256(canon(M)).hexdigest()
    expected = json.load(open("benchmarks/001_baseline/observable/expected_output.json"))

    verdict = "ACCEPT" if h_m == expected["h_m"] else "REJECT"

    print("=== MatVerse Benchmark #001 ===")
    print(f"VERDICT: {verdict}")
    print(f"H(M) calculado : {h_m}")
    print(f"H(M) esperado  : {expected['h_m']}")
    print(f"Match           : {'✅' if verdict == 'ACCEPT' else '❌'}")

if __name__ == "__main__":
    main()
