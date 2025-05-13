#!/usr/bin/env python3
"""
Script to remove sql_app.db from Git history.
"""
import subprocess
import os
import sys

def remove_db_from_git():
    """
    Remove sql_app.db from Git history using git filter-branch.
    This will rewrite the history of all commits that include the file.
    """
    print("Removing sql_app.db from Git history...")
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    try:
        # First, add the file to .gitignore if it's not already there
        add_to_gitignore()
        
        # Then use git filter-branch to remove the file from all commits
        subprocess.run([
            "git", "filter-branch", "--force", "--index-filter",
            "git rm --cached --ignore-unmatch sql_app.db", 
            "--prune-empty", "--tag-name-filter", "cat", "--", "--all"
        ], check=True)
        
        print("\nFile has been removed from Git history!")
        print("\nNext steps:")
        print("1. Force push to your repository with: git push origin --force --all")
        print("2. If you have tags: git push origin --force --tags")
        print("3. Make sure your teammates pull the latest changes")
        return 0
    
    except subprocess.CalledProcessError as e:
        print(f"Error removing file from Git history: {e}")
        return 1

def add_to_gitignore():
    """Add sql_app.db to .gitignore if not already present."""
    gitignore_path = ".gitignore"
    entry = "sql_app.db"
    
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            content = f.read()
        
        if entry not in content:
            with open(gitignore_path, "a") as f:
                if not content.endswith("\n"):
                    f.write("\n")
                f.write(f"{entry}\n")
            print(f"Added {entry} to .gitignore")
    else:
        with open(gitignore_path, "w") as f:
            f.write(f"{entry}\n")
        print(f"Created .gitignore with {entry}")

if __name__ == "__main__":
    print("WARNING: This will rewrite Git history. Make sure you understand the implications.")
    print("This is generally safe if you haven't pushed your commits yet.")
    response = input("Continue? (y/n): ")
    if response.lower() == 'y':
        sys.exit(remove_db_from_git())
    else:
        print("Operation cancelled.")
        sys.exit(0)
