# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='clipbox',
    version='1.2.0',
    description='Aesthetic, fast, and secure desktop clipboard manager with auto-categorization and AES encryption',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Kiranmayee Abbireddy',
    url='https://github.com/kiranmayee-abbireddy/clipboard-org',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        '': ['frontend/**/*', 'clipbox.ico'],
    },
    install_requires=[
        'pywebview>=5.0.0',
        'cryptography>=41.0.0',
        'python-dateutil>=2.8.2',
        'pywin32>=306; sys_platform == "win32"',
    ],
    extras_require={
        'build': ['PyInstaller>=6.0.0'],
    },
    entry_points={
        'console_scripts': [
            'clipbox=src.main:main',
            'clipbox-monitor=src.clipboard_monitor:main',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Utilities',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
