from setuptools import setup, find_packages
from pathlib import Path

# Read version from VERSION file
version_file = Path(__file__).parent / "VERSION"
if version_file.exists():
    version = version_file.read_text().strip()
else:
    version = "2.0.1"

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="unbound-manager",
    version=version,
    author="Regix",
    author_email="your.email@example.com",
    description="A modern Unbound DNS server management tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/regix1/unbound-manager",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "Topic :: Internet :: Name Service (DNS)",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "unbound-manager=unbound_manager.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "unbound_manager": ["../templates/*.j2", "../configs/*.yaml"],
    },
)