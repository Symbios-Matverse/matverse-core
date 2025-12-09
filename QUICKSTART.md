# 🚀 MatVerse Symbios v3.0 - Quick Start

## ⚡ Início Rápido (2 minutos)

### 1️⃣ Clone e Setup
```bash
# Já clonado em /home/user/matverse-core
cd /home/user/matverse-core

# Instalar dependências básicas
pip install numpy scipy pandas pytest
```

### 2️⃣ Execute o Exemplo
```bash
cd symbios-engine
python examples/basic_usage.py
```

**Output esperado**:
```
🌀 MatVerse Symbios v3.0 - Exemplo Básico do Ω-GATE
============================================================
Ω-Score: 0.7857
Status: ✅/❌
Antifragilidade β_q: > 0 (Antifrágil)
```

### 3️⃣ Execute os Testes
```bash
python -m pytest tests/ -v
```

**Output esperado**:
```
test_omega_calculation PASSED
test_omega_range PASSED
test_gate_decision_logic PASSED
test_weight_validation PASSED
test_antifragility_coefficient PASSED
```

## 📊 Estrutura Atual

```
matverse-core/
├── 📄 README.md                      ← Documentação principal
├── 📄 STATUS.md                      ← Progresso detalhado
├── 📄 CONTRIBUTING.md                ← Guia de contribuição
├── 📄 LICENSE                        ← MIT License
│
├── 🔧 symbios-engine/                ← ENGINE (35% completo)
│   ├── core/
│   │   └── metrics/
│   │       ├── __init__.py
│   │       └── omega_gate.py         ← ✅ IMPLEMENTADO (300 linhas)
│   ├── tests/
│   │   └── test_omega_gate.py        ← ✅ 5 TESTES
│   ├── examples/
│   │   └── basic_usage.py            ← ✅ FUNCIONAL
│   ├── requirements.txt
│   ├── setup.py
│   └── README.md
│
├── 📐 symbios-theory/                ← THEORY (estrutura)
│   ├── papers/
│   ├── formalism/
│   ├── simulations/
│   └── README.md
│
└── 🌉 symbios-bridge/                ← BRIDGE (estrutura)
    ├── phi_omega/
    ├── cog/
    ├── integration/
    └── README.md
```

## 🎯 O Que Funciona AGORA

### ✅ Implementado e Testado
1. **OmegaGate**: Motor de decisão Ω-GATE completo
   ```python
   from core.metrics import OmegaGate, OmegaState
   gate = OmegaGate()
   omega, breakdown = gate.calculate(state)
   ```

2. **Cálculo de Ω-Score**: Agregação ponderada de 5 métricas
   - Ψ (coerência semântica): 40%
   - Θ̂ (latência normalizada): 30%
   - 1-CVaR (risco inverso): 20%
   - PoLE (evolução): 5%
   - COG (conhecimento): 5%

3. **Decisão Binária**: Aprovação/rejeição baseada em thresholds
   ```python
   decision = gate.gate_decision(state)
   if decision['passed']:
       print("✅ APROVADO")
   ```

4. **Antifragilidade**: Cálculo do coeficiente β_q
   ```python
   beta_q = gate.antifragility_coefficient(states_history)
   # β_q > 1 → Antifrágil (melhora com ruído)
   ```

5. **Testes Automatizados**: 5 casos de teste passando
   - Cálculo correto de Ω
   - Validação de bounds [0, 1]
   - Lógica de decisão
   - Validação de pesos
   - Coeficiente de antifragilidade

## 🔧 Como Usar

### Exemplo Mínimo
```python
from datetime import datetime
from core.metrics import OmegaGate, OmegaState

# Criar gate
gate = OmegaGate()

# Criar estado
state = OmegaState(
    timestamp=datetime.utcnow(),
    psi=0.9,      # 90% coerência
    theta=75.0,   # 75ms latência
    cvar=0.03,    # 3% risco
    pole=0.92,    # 92% evolução
    cog=0.88      # 88% conhecimento
)

# Calcular Ω
omega, breakdown = gate.calculate(state)
print(f"Ω = {omega:.4f}")

# Decidir
decision = gate.gate_decision(state)
print(f"Aprovado: {decision['passed']}")
```

### Personalizar Pesos
```python
# Criar gate com pesos customizados
custom_weights = {
    'psi': 0.5,    # 50% peso em coerência
    'theta': 0.3,  # 30% em performance
    'cvar': 0.15,  # 15% em risco
    'pole': 0.025, # 2.5% em evolução
    'cog': 0.025   # 2.5% em conhecimento
}

gate = OmegaGate(weights=custom_weights)
```

### Ajustar Thresholds
```python
# Thresholds mais rígidos
strict_thresholds = {
    'omega_min': 0.90,    # Ω mínimo 90%
    'psi_min': 0.85,      # Coerência mínima 85%
    'cvar_max': 0.03,     # Risco máximo 3%
    'theta_max': 50.0,    # Latência máxima 50ms
    'pole_min': 0.5       # Evolução positiva
}

gate = OmegaGate(thresholds=strict_thresholds)
```

## 📦 Próximos Módulos a Implementar

### Prioridade ALTA
1. **PSI Calculator** (`core/metrics/psi_calculator.py`)
   - Calcular Ψ = 0.4·C + 0.3·Co + 0.3·T
   - Completude, Consistência, Rastreabilidade

2. **Theta Normalizer** (`core/metrics/theta_normalizer.py`)
   - Normalizar Θ̂ = exp(-γ·Θ)
   - Análise de distribuição de latências

3. **CVaR Estimator** (`core/metrics/cvar_estimator.py`)
   - CVaR_α via métodos histórico/normal/t-student
   - Backtesting de risco

4. **PoSE Anchor** (`core/blockchain/pose_anchor.py`)
   - Ancoragem Merkle em blockchain
   - Verificação de proofs

5. **ΦΩ Field** (`symbios-bridge/phi_omega/field_calculator.py`)
   - Acoplamento ENGINE ⊕ THEORY
   - Cálculo de coerência cruzada

## 🎯 Comandos Úteis

```bash
# Executar testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=core

# Executar exemplo
python examples/basic_usage.py

# Instalar em modo desenvolvimento
pip install -e .

# Formatar código (quando tiver black)
black core/ tests/

# Verificar código (quando tiver flake8)
flake8 core/ tests/
```

## 📊 Status do Projeto

```
PROGRESSO: [████████░░░░░░░░░░░░░░] 35%

✅ COMPLETO:
- Estrutura dos 3 repositórios
- OmegaGate implementado e testado
- Documentação completa
- Exemplo funcional
- Git/GitHub integrado

🚧 EM PROGRESSO:
- Módulos de métricas adicionais
- PoSE/PoLE blockchain
- ΦΩ-Field coupling
- Simulações quânticas

📋 PLANEJADO:
- HuggingFace Space
- Paper arXiv
- Deploy Polygon Amoy
```

## 🔗 Links Importantes

- **Repositório**: `/home/user/matverse-core`
- **GitHub**: Symbios-Matverse/matverse-core
- **Branch**: claude/setup-core-repos-017C2EnxegVY3bZqSFwwLhru
- **Documentação**: Veja README.md e STATUS.md

## 💡 Dicas

1. **Para Desenvolver**: Comece implementando os módulos de Prioridade ALTA
2. **Para Testar**: Use `pytest tests/ -v` após cada mudança
3. **Para Documentar**: Adicione docstrings e exemplos
4. **Para Contribuir**: Leia CONTRIBUTING.md primeiro

## ❓ FAQ

**P: O exemplo funciona?**
R: ✅ Sim! Execute `python symbios-engine/examples/basic_usage.py`

**P: Os testes passam?**
R: ✅ Sim! 5/5 testes passando

**P: Posso usar em produção?**
R: ⚠️  Ainda não. Versão 3.0.0-alpha em desenvolvimento

**P: Como contribuir?**
R: Veja CONTRIBUTING.md e escolha uma tarefa de STATUS.md

---

**Última atualização**: 2024-12-09
**Status**: 🟢 ATIVO
**Versão**: 3.0.0-alpha
