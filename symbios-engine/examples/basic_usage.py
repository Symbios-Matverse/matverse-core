"""
Exemplo Básico: Usando o Ω-GATE v3.0

Este exemplo demonstra como:
1. Criar um motor Ω-GATE
2. Criar estados
3. Calcular Ω-Score
4. Tomar decisões
5. Avaliar antifragilidade
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.metrics import OmegaGate, OmegaState
from datetime import datetime

def main():
    print("🌀 MatVerse Symbios v3.0 - Exemplo Básico do Ω-GATE")
    print("=" * 60)

    # 1. Criar motor Ω-GATE com pesos padrão
    print("\n1️⃣  Criando motor Ω-GATE...")
    gate = OmegaGate()
    print(f"   Pesos: {gate.weights}")

    # 2. Criar estado de exemplo
    print("\n2️⃣  Criando estado de exemplo...")
    state = OmegaState(
        timestamp=datetime.utcnow(),
        psi=0.9,      # 90% de coerência semântica
        theta=75.0,   # 75ms de latência
        cvar=0.03,    # 3% de risco
        pole=0.92,    # 92% de evolução positiva
        cog=0.88      # 88% de conhecimento documentado
    )
    print(f"   Estado criado: Ψ={state.psi}, Θ={state.theta}ms, CVaR={state.cvar}")

    # 3. Calcular Ω-Score
    print("\n3️⃣  Calculando Ω-Score...")
    omega, breakdown = gate.calculate(state)
    print(f"   Ω-Score: {omega:.4f}")
    print(f"\n   Breakdown dos componentes:")
    for component, data in breakdown['components'].items():
        print(f"      {component.upper():8s}: {data['value']:.3f} × {data['weight']:.2f} = {data['contribution']:.4f}")

    # 4. Tomar decisão
    print("\n4️⃣  Tomando decisão de aprovação...")
    decision = gate.gate_decision(state)

    if decision['passed']:
        print(f"   ✅ SISTEMA APROVADO (Ω={decision['omega']:.4f})")
    else:
        print(f"   ❌ SISTEMA REPROVADO (Ω={decision['omega']:.4f})")
        print(f"   Razões: {decision.get('checks', {})}")

    # 5. Simular evolução e calcular antifragilidade
    print("\n5️⃣  Simulando evolução do sistema...")

    # Criar histórico de estados (simulação de melhoria sob ruído)
    states_history = [
        OmegaState(datetime.utcnow(), 0.85, 100.0, 0.05, 0.5, 0.8),
        OmegaState(datetime.utcnow(), 0.88, 95.0, 0.06, 0.6, 0.82),
        OmegaState(datetime.utcnow(), 0.91, 90.0, 0.065, 0.7, 0.85),
        OmegaState(datetime.utcnow(), 0.94, 85.0, 0.07, 0.8, 0.88),
        state  # Estado atual
    ]

    # Calcular β_q (coeficiente de antifragilidade)
    beta_q = gate.antifragility_coefficient(states_history)

    print(f"   Histórico de {len(states_history)} estados")
    print(f"   β_q (antifragilidade): {beta_q:.4f}")

    if beta_q > 1.0:
        print(f"   🎉 Sistema é ANTIFRÁGIL (melhora com ruído)")
    elif beta_q > 0:
        print(f"   ✅ Sistema é RESILIENTE (resiste ao ruído)")
    else:
        print(f"   ⚠️  Sistema é FRÁGIL (piora com ruído)")

    # 6. Resumo final
    print("\n" + "=" * 60)
    print("📊 RESUMO:")
    print(f"   Ω-Score Final:        {omega:.4f}")
    print(f"   Status:              {'✅ Aprovado' if decision['passed'] else '❌ Reprovado'}")
    print(f"   Antifragilidade β_q:  {beta_q:.4f}")
    print(f"   Classificação:       {'Antifrágil' if beta_q > 1 else 'Resiliente' if beta_q > 0 else 'Frágil'}")
    print("=" * 60)

    print("\n✨ Exemplo concluído com sucesso!")

if __name__ == "__main__":
    main()
