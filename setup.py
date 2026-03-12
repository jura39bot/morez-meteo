from setuptools import setup, find_packages
setup(
    name="morez-meteo",
    version="0.1.0",
    packages=find_packages(),
    entry_points={"console_scripts": ["morez-meteo=morez_meteo.cli:run"]},
)
