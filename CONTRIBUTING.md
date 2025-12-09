# 🤝 Contributing to MatVerse Symbios v3.0

Obrigado por seu interesse em contribuir!

## 🏗️ Estrutura do Projeto

Este repositório contém 3 módulos ortogonais:

1. **symbios-engine** (M_Eng): Código executável
2. **symbios-theory** (T_Phys): Formalismo matemático
3. **symbios-bridge** (ΦΩ): Acoplamento entre ENGINE e THEORY

## 🚀 Como Contribuir

### Para Desenvolvedores (ENGINE)

1. Fork o repositório
2. Crie uma branch para sua feature:
   ```bash
   git checkout -b feature/nova-metrica
   ```
3. Desenvolva e teste:
   ```bash
   cd symbios-engine
   pip install -e .[dev]
   python -m pytest tests/ -v
   ```
4. Commit com mensagens claras:
   ```bash
   git commit -m "feat: adiciona métrica X para Y"
   ```
5. Push e abra um Pull Request

### Para Pesquisadores (THEORY)

1. Contribua com provas formais em `symbios-theory/formalism/`
2. Escreva seções do paper em `symbios-theory/papers/`
3. Proponha novos axiomas
4. Desenvolva simulações em `symbios-theory/simulations/`

### Para Integradores (BRIDGE)

1. Otimize acoplamento ΦΩ
2. Melhore rastreamento COG
3. Desenvolva operadores de sincronização

## 📐 Padrões de Código

- **Python**: PEP 8, type hints, docstrings
- **LaTeX**: Standard academic format
- **Git**: Conventional Commits

### Exemplo de Commit Messages

```
feat: adiciona suporte para CVaR dinâmico
fix: corrige cálculo de β_q em casos extremos
docs: atualiza README com exemplos
test: adiciona testes para PoLE
refactor: simplifica cálculo de Ω
```

## 🧪 Testes

Todos os PRs devem incluir testes:

```bash
# Executar testes
pytest tests/ -v

# Com cobertura (mínimo 80%)
pytest tests/ --cov=core --cov-report=html
```

## 📝 Documentação

- Toda função pública deve ter docstring
- Adicione exemplos quando relevante
- Atualize README quando necessário

## 🔍 Code Review

Todos os PRs passam por:

1. Verificação automática (CI/CD)
2. Review por 2+ mantainers
3. Validação de testes
4. Check de cobertura

## 📞 Dúvidas?

- Abra uma Issue
- Pergunte no Discord
- Email: contact@matverse.ai

---

**Obrigado por contribuir para o MatVerse Symbios! 🌀**
