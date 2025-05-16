from setuptools import setup, find_packages

setup(
    name="natural-agi-common",
    version="0.1.16",
    packages=find_packages(include=["common", "common.*"]),
    install_requires=["pydantic", "networkx"],
)
