# setup.py
from setuptools import setup, find_packages

setup(
    name='clipboard-organizer',
    version='1.0.0',
    description='Aesthetic clipboard manager with categorization and security',
    author='Kiryee',
    packages=find_packages(),
    install_requires=[
        'PyQt6>=6.6.0',
        'pywebview>=5.0',
        'cryptography>=41.0.0',
        'python-dateutil>=2.8.0',
    ],
    entry_points={
        'console_scripts': [
            'clipboard-organizer=src.main:main',
        ],
    },
    python_requires='>=3.8',
)
