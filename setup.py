import io
import os

from setuptools import find_packages, setup
from setuptools.command.clean import clean as Clean

from modules.__version__ import version


class CleanCommand(Clean):
    """Custom clean command to tidy up the project root."""

    def run(self):
        Clean.run(self)
        for directory in ["dist", "build", "*.egg-info"]:
            os.system(f"rm -rf {directory}")


DESCRIPTION = "Record and report times spent in various activities."
here = os.path.abspath(os.path.dirname(__file__))

try:
    with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION


setup(
    name="timemate",
    version=version,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Daniel A Graham",
    author_email="dnlgrhm@gmail.com",
    packages=find_packages(),
    cmdclass={"clean": CleanCommand},
    install_requires=[
        "click",
        "click-shell",
        "prompt_toolkit",
        "rich",
        "pyyaml",
        "pytz",
    ],
    python_requires=">=3.9",
    url="https://github.com/dagraham/timemate",  # Adjust based on the minimum Python version your app supports
    entry_points={
        "console_scripts": [
            "timemate=modules.__main__:main",  # Replace `your_module_name` with the actual module
        ],
    },
)
