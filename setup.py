from pathlib import Path
import shutil
from setuptools import setup as _setup, find_packages

PKG = "vscode-alt-marketplace"
PKG_ = PKG.replace("-", "_")

root = Path(__file__).parent


def clean():
    for path in (root / "src").iterdir():
        if path.suffix == ".egg-info":
            shutil.rmtree(path)
    for path in root.iterdir():
        if path.suffix == ".egg-info":
            shutil.rmtree(path)
    shutil.rmtree(root / "build", ignore_errors=True)


pkgs = find_packages("src")


def setup(*args, **kwargs):
    clean()
    (root / "dist").mkdir(exist_ok=True)
    readme = (Path(__file__).parent / "README.md").read_text()
    _setup(
        *args,
        long_description=readme,
        long_description_content_type="text/markdown",
        author="Jose A.",
        author_email="jose-pr@coqui.dev",
        url=f"https://github.com/jose-pr/{PKG}",
        package_dir={PKG_: "src"},
        packages=[PKG_, *[f"{PKG_}.{pkg}" for pkg in pkgs]],
        install_requires=Path("requirements.txt").read_text().splitlines(),
        **kwargs,
    )
    clean()


import os


def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join("..", path, filename))
    return paths


setup(
    name=PKG,
    version=Path("VERSION").read_text(),
    description="Python methods and classes and some examples to mirror/proxy or create your own visual studio marketplace. Usefull for air gapped or similar networks where there is no access to the internet.",
    package_data={
        PKG_: [*package_files("examples/templates"), *package_files("examples/static")],
    },
)
