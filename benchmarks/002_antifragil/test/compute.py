import hashlib


def compute_antifragil_metrics(seed: int = 42, stress_levels: int = 10) -> dict:
    # Determinístico: a "adaptação ao estresse" é modelada de forma controlada e reproduzível.
    h = hashlib.sha256(f"matverse_antifragil_seed_{seed}_v1".encode()).hexdigest()

    base_omega = 0.95
    base_psi = 0.90
    base_cvar = 0.05

    # Ganho sob estresse (modelo simples e congelável)
    psi_gain_per_level = 0.004
    cvar_reduction_per_level = 0.003

    final_psi = base_psi + psi_gain_per_level * stress_levels
    final_cvar = max(base_cvar - cvar_reduction_per_level * stress_levels, 0.01)

    # Variação leve determinística via hash (centrada em 0, amplitude 0.1)
    final_omega = base_omega + (int(h[16:24], 16) / 0xffffffff * 0.1 - 0.05)

    return {
        "seed_used": seed,
        "stress_levels": stress_levels,
        "metrics": {
            "final_omega_prime": round(final_omega, 4),
            "final_psi": round(final_psi, 4),
            "final_cvar_alpha_095": round(final_cvar, 4)
        }
    }


if __name__ == "__main__":
    import json, sys
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    stress = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    print(json.dumps(compute_antifragil_metrics(seed, stress), indent=2))
