"""
Testes para o Ω-GATE v3.0
"""
import pytest
from datetime import datetime
import sys
import os

# Adicionar o diretório core ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.metrics.omega_gate import OmegaGate, OmegaState


class TestOmegaGate:
    """Testes do Ω-GATE"""

    def test_omega_calculation(self):
        """Testa cálculo básico do Ω-Score"""
        gate = OmegaGate()
        state = OmegaState(
            timestamp=datetime.utcnow(),
            psi=0.9,
            theta=75.0,
            cvar=0.03,
            pole=0.92,
            cog=0.88
        )

        omega, breakdown = gate.calculate(state)

        assert 0.0 <= omega <= 1.0, "Ω deve estar em [0,1]"
        assert 'components' in breakdown
        assert len(breakdown['components']) == 5

    def test_omega_range(self):
        """Testa que Ω está sempre em [0, 1]"""
        gate = OmegaGate()

        extreme_states = [
            OmegaState(datetime.utcnow(), 0.0, 0.0, 0.0, 0.0, 0.0),
            OmegaState(datetime.utcnow(), 1.0, 0.0, 0.0, 1.0, 1.0),
            OmegaState(datetime.utcnow(), 0.5, 500.0, 0.5, 0.5, 0.5),
        ]

        for state in extreme_states:
            omega, _ = gate.calculate(state)
            assert 0.0 <= omega <= 1.0, f"Ω={omega} fora de [0,1]"

    def test_gate_decision_logic(self):
        """Testa lógica de decisão binária"""
        gate = OmegaGate()

        # Estado que deve passar
        good_state = OmegaState(
            timestamp=datetime.utcnow(),
            psi=0.9,     # > 0.8
            theta=75.0,  # < 100
            cvar=0.03,   # < 0.05
            pole=0.5,    # > 0
            cog=0.8
        )

        result = gate.gate_decision(good_state)
        assert result['passed'] is True, "Estado bom deveria passar"

        # Estado que deve falhar
        bad_state = OmegaState(
            timestamp=datetime.utcnow(),
            psi=0.9,
            theta=75.0,
            cvar=0.08,   # > 0.05 (falha)
            pole=0.5,
            cog=0.8
        )

        result = gate.gate_decision(bad_state)
        assert result['passed'] is False, "Estado ruim deveria falhar"

    def test_weight_validation(self):
        """Testa validação de pesos"""
        # Pesos válidos (somam 1.0)
        valid_weights = {
            'psi': 0.4,
            'theta': 0.3,
            'cvar': 0.2,
            'pole': 0.05,
            'cog': 0.05
        }

        gate = OmegaGate(weights=valid_weights)
        assert gate is not None

        # Pesos inválidos (não somam 1)
        invalid_weights = {
            'psi': 0.5,
            'theta': 0.5,
            'cvar': 0.5,
            'pole': 0.5,
            'cog': 0.5
        }

        with pytest.raises(ValueError):
            OmegaGate(weights=invalid_weights)

    def test_antifragility_coefficient(self):
        """Testa cálculo de β_q"""
        gate = OmegaGate()

        # Histórico onde sistema melhora sob ruído
        states = [
            OmegaState(datetime.utcnow(), 0.9, 100.0, 0.05, 0.5, 0.8),
            OmegaState(datetime.utcnow(), 0.92, 110.0, 0.06, 0.6, 0.82),
            OmegaState(datetime.utcnow(), 0.95, 120.0, 0.07, 0.7, 0.85),
        ]

        beta_q = gate.antifragility_coefficient(states)

        # β_q deve ser > 0 para evolução positiva
        assert beta_q > 0, f"β_q={beta_q} deveria ser positivo"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
