grep -vE '^\s*#|^\s*$|^crashtest|^pytest|^pytest-asyncio|^fakeredis|^poetry|^poetry-core|^pip|^build|^installer|^pkginfo|^trove-classifiers|^virtualenv|^pbs-installer|^distlib|^cleo|^findpython|^jaraco|^pluggy|^pyproject_hooks|^iniconfig|^shellingham|^tomlkit' requirements.txt \
  | sed 's/==/@/' \
  | xargs poetry add

# In pyproject.toml add/change: requires-python = ">=3.13,<4.0"

poetry add --group dev crashtest pytest pytest-asyncio
