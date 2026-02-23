from setuptools import setup, find_packages

setup(
    name="ghostroute",
    version="1.0",
    description="Free AI for OpenClaw - Automatic free model management via OpenRouter",
    author="Dr.Kittimasak Naijit",
    url="https://github.com/kittimasak/GhostRoute",
    packages=find_packages(include=["ghostroute", "ghostroute.*"]),
    py_modules=["main", "watcher"],
    install_requires=[
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "ghostroute=main:main",
            "ghostroute-watcher=watcher:main",
        ],
    },
    python_requires=">=3.8",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
)