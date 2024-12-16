import io
import os

from setuptools import find_packages, setup

from modules.__version__ import version

DESCRIPTION = ("A CLI Timer Manager",)
here = os.path.abspath(os.path.dirname(__file__))

try:
    with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION


setup(
    name="TimeMate",
    version=version,
    description=long_description,
    author="Daniel A Graham",
    author_email="dnlgrhm@gmail.com",
    packages=find_packages(),
    install_requires=[
        "click",
        "click-shell",
        "prompt_toolkit",
        "rich",
        "pyyaml",
    ],
    python_requires=">=3.9",
    url="https://github.com/dagraham/time-mate",  # Adjust based on the minimum Python version your app supports
    entry_points={
        "console_scripts": [
            "timemate=modules.__main__:main",  # Replace `your_module_name` with the actual module
        ],
    },
)
