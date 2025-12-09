"""
Setup do Symbios Engine v3.0

Package: symbios-engine
Version: 3.0.0
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="symbios-engine",
    version="3.0.0",
    author="MatVerse Symbios Collective",
    author_email="contact@matverse.ai",
    description="Engine computacional do MatVerse Symbios - Sistema de governança algorítmica antifrágil",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Symbios-Matverse/matverse-core",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.21.0",
        "scipy>=1.7.0",
        "pandas>=1.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
        "dashboard": [
            "gradio>=4.0.0",
            "plotly>=5.0.0",
        ],
        "quantum": [
            "qiskit>=0.45.0",
        ],
        "blockchain": [
            "web3>=6.0.0",
        ],
    },
)
