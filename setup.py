from setuptools import setup, find_packages

setup(
    name="horses-odds-tracker",
    version="0.1.0",
    description="Horse Racing Odds Tracking & Alert System",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "PyYAML>=6.0",
        "python-dotenv>=1.0.0",
        "python-dateutil>=2.8.0",
    ],
    python_requires=">=3.11",
)