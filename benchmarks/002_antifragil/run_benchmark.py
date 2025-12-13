import json
import hashlib
import subprocess
import sys


def canon(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def fail(msg: str) -> None:
    print(msg)
    raise SystemExit(1)


def main():
    spec = json.load(open("benchmarks/002_antifragil/spec/claim_v1.0.0.json", "r", encoding="utf-8"))

    seed = int(spec["seed"])
    stress_levels = int(spec["stress_levels"])

    result = subprocess.run(
        [sys.executable, "benchmarks/002_antifragil/test/compute.py", str(seed), str(stress_levels)],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        fail("REJECT: compute.py failed\n" + (result.stderr or "").strip())

    output = json.loads(result.stdout)
    metrics = output["metrics"]

    # Validação de thresholds (sem “narrativa”: só regra objetiva)
    exp = spec["expected"]
    if metrics["final_omega_prime"] < exp["final_omega_prime"]["min"]:
        fail(f"REJECT: final_omega_prime {metrics['final_omega_prime']} < {exp['final_omega_prime']['min']}")
    if metrics["final_psi"] < exp["final_psi"]["min"]:
        fail(f"REJECT: final_psi {metrics['final_psi']} < {exp['final_psi']['min']}")
    if metrics["final_cvar_alpha_095"] > exp["final_cvar_alpha_095"]["max"]:
        fail(f"REJECT: final_cvar_alpha_095 {metrics['final_cvar_alpha_095']} > {exp['final_cvar_alpha_095']['max']}")

    # M canônico (sem timestamp)
    M = {
        "benchmark": "002_antifragil",
        "version": spec["version"],
        "seed": seed,
        "stress_levels": stress_levels,
        "metrics": metrics
    }

    h_m = hashlib.sha256(canon(M)).hexdigest()
    expected = json.load(open("benchmarks/002_antifragil/observable/expected_output.json", "r", encoding="utf-8"))

    verdict = "ACCEPT" if h_m == expected["h_m"] else "REJECT"

    print("=== MatVerse Benchmark #002 Antifrágil ===")
    print(f"VERDICT: {verdict}")
    print(f"H(M) calculado : {h_m}")
    print(f"H(M) esperado  : {expected['h_m']}")
    print(f"Match          : {'OK' if verdict == 'ACCEPT' else 'FAIL'}")

    raise SystemExit(0 if verdict == "ACCEPT" else 2)


if __name__ == "__main__":
    main()
