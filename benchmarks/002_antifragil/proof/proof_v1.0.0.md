# Prova — Benchmark #002 Antifrágil

Definição canônica:

M = {benchmark, version, seed, stress_levels, metrics}
H(M) = SHA-256(JSON canônico de M)

Parâmetros congelados:
- seed = 42
- stress_levels = 10

Métricas (4 casas decimais):
- final_omega_prime = 0.9361
- final_psi = 0.9400
- final_cvar_alpha_095 = 0.0200

Hash congelado:
H(M) = 3f185330214a20cf910ddf8c781d8dde95489ea95d5611c08ff4cbe226ab32a2

Qualquer execução correta deve reproduzir exatamente o hash acima.
Congelado em 13/12/2025.
