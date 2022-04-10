from pathlib import Path
import shutil
from setuptools import setup as _setup, find_packages

PKG = "vscode-alt-marketplace"

root = Path(__file__).parent


def clean():
    for path in (root / "src").iterdir():
        if path.suffix == ".egg-info":
            shutil.rmtree(path)
    shutil.rmtree(root / "build", ignore_errors=True)


pkgs = find_packages("src")


def setup(*args, **kwargs):
    clean()
    readme = (Path(__file__).parent / "README.md").read_text()
    _setup(
        *args,
        long_description=readme,
        long_description_content_type="text/markdown",
        author="Jose A.",
        author_email="jose-pr@coqui.dev",
        url=f"https://github.com/jose-pr/{PKG}",
        package_dir={PKG: "src"},
        packages=[PKG, *[f"{PKG}.{pkg}" for pkg in pkgs]],
        install_requires=Path("requirements.txt").read_text().splitlines(),
        **kwargs,
    )
    clean()


setup(
    name=PKG,
    version=Path("VERSION").read_text(),
    description="Python methods and classes and some examples to mirror/proxy or create your own visual studio marketplace. Usefull for air gapped or similar networks where there is no access to the internet.",
    package_data={
        PKG: ["examples/templates/*"],
    },
)
