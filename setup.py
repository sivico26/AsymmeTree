import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="asymmetree",
    version="0.0.1",
    author="David Schaller",
    author_email="david@0x002A.com",
    description="Simulation of species and gene tree scenarios with asymmetric evolution rates.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/david-schaller/asymmetree",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
