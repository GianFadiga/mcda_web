# tree.py
import os

def tree(dir_path: str, prefix: str = ""):
    files = os.listdir(dir_path)
    files.sort()
    for i, file in enumerate(files):
        path = os.path.join(dir_path, file)
        connector = "└── " if i == len(files) - 1 else "├── "
        print(prefix + connector + file)
        if os.path.isdir(path):
            extension = "    " if i == len(files) - 1 else "│   "
            tree(path, prefix + extension)

tree(".", "")