"""Setup script for Framely-Eyes."""
from setuptools import setup, find_packages

setup(
    name="framely-eyes",
    version="1.0.0",
    packages=find_packages(include=["services*"]),
    python_requires=">=3.10",
)
