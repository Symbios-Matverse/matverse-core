"""
Módulo de métricas fundamentais

Contém:
- omega_gate: Ω = Σ w_i·m_i com invariância de calibre
- psi_calculator: Ψ = 0.4C + 0.3Co + 0.3T
- theta_normalizer: Θ̂ = exp(-γΘ)
- cvar_estimator: CVaR_α via tail ordering
"""
from .omega_gate import OmegaGate, OmegaState

__all__ = ['OmegaGate', 'OmegaState']
