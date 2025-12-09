# 🌀 Symbios Engine v3.0

**Engine computacional do MatVerse Symbios - Sistema de governança algorítmica antifrágil**

## 📋 Visão Geral

O **Symbios Engine** é o coração computacional do MatVerse Symbios, implementando:

- **Ω-GATE**: Métrica multiobjetivo antifrágil
- **PoSE/PoLE**: Provas criptográficas de coerência e evolução
- **Validação Quântica**: Fidelidade que melhora sob ruído (β_q > 1)

## ✨ Funcionalidades Principais

### Ω-GATE (Motor de Decisão)
```python
Ω = 0.40·Ψ + 0.30·Θ̂ + 0.20·(1-CVaR) + 0.05·PoLE + 0.05·COG
```

- **Ψ**: Coerência semântica
- **Θ̂**: Latência normalizada
- **CVaR**: Risco condicional
- **PoLE**: Prova de evolução
- **COG**: Conhecimento documentado

## 🚀 Instalação

```bash
cd symbios-engine
pip install -e .

# Com extras
pip install -e .[dev,dashboard,quantum,blockchain]
```

## 📊 Uso Básico

```python
from core.metrics import OmegaGate, OmegaState
from datetime import datetime

# Criar motor Ω
gate = OmegaGate()

# Criar estado
state = OmegaState(
    timestamp=datetime.utcnow(),
    psi=0.9,      # Coerência semântica
    theta=75.0,   # Latência em ms
    cvar=0.03,    # Risco
    pole=0.92,    # Evolução
    cog=0.88      # Conhecimento
)

# Calcular Ω-Score
omega, breakdown = gate.calculate(state)
print(f"Ω-Score: {omega:.4f}")

# Tomar decisão
decision = gate.gate_decision(state)
if decision['passed']:
    print("✅ Sistema APROVADO")
```

## 🧪 Testes

```bash
# Executar testes
python -m pytest tests/ -v

# Com cobertura
pytest tests/ --cov=core
```

## 🏗️ Estrutura

```
symbios-engine/
├── core/
│   ├── metrics/              # Ω, Ψ, Θ, CVaR
│   ├── blockchain/           # PoSE/PoLE
│   ├── quantum/              # Simulações
│   └── observability/        # Monitoramento
├── tests/                    # Testes
└── deployment/              # Deploy HF, blockchain
```

## 📄 Licença

MIT License - Veja LICENSE para detalhes.
