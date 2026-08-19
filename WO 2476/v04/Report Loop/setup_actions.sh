#!/bin/bash

# Array of your specific repositories
REPOS=(
  "Paltro-SD01/LAB-IQ-150"
  "Paltro-SD01/HFRR-ADV"
  "Paltro-SD01/B2V2"
  "Paltro-SD01/BOCLE"
  "Paltro-SD01/LAB-IQ-350"
  "Paltro-SD01/AIRJET"
)

# Set base URL. 
# Using HTTPS here. If you use SSH keys, change this to: "git@github.com:"
BASE_URL="https://github.com/"

# Create a temporary workspace folder so it doesn't clutter your current directory
WORKSPACE="github_actions_setup"
mkdir -p "$WORKSPACE"
cd "$WORKSPACE" || exit

for REPO in "${REPOS[@]}"; do
  echo "========================================"
  echo "🚀 Processing $REPO..."
  echo "========================================"

  # Extract just the repo name (e.g., LAB-IQ-150)
  REPO_NAME=$(basename "$REPO")

  # Clone the repository
  git clone "${BASE_URL}${REPO}.git"
  cd "$REPO_NAME" || { echo "❌ Failed to clone $REPO"; continue; }

  # Detect the default branch (main or master)
  DEFAULT_BRANCH=$(git branch --show-current)
  echo "📌 Detected default branch: $DEFAULT_BRANCH"

  # Create the required GitHub Actions folder path
  mkdir -p .github/workflows

  # Generate the YAML file
  # Note: Variables starting with \$ are escaped so they stay literal in the YAML file
  cat <<EOF > .github/workflows/log_changes.yml
name: Generate Push Log

on:
  push:
    branches:
      - $DEFAULT_BRANCH

jobs:
  create-log-file:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - name: Extract Commit Info and Create File
        run: |
          TIMESTAMP=\$(git log -1 --format="%cd" --date=iso)
          COMMENT=\$(git log -1 --format="%B")
          CHANGED_FILES=\$(git diff-tree --no-commit-id --name-only -r \${{ github.sha }})
          
          echo "🕒 Timestamp: \$TIMESTAMP" > latest_commit_log.txt
          echo "💬 Comment: \$COMMENT" >> latest_commit_log.txt
          echo "---------------------------------" >> latest_commit_log.txt
          echo "📁 Files Changed:" >> latest_commit_log.txt
          echo "\$CHANGED_FILES" >> latest_commit_log.txt

      - name: Commit and Push Log File
        run: |
          git config --global user.name 'github-actions[bot]'
          git config --global user.email 'github-actions[bot]@users.noreply.github.com'
          git add latest_commit_log.txt
          
          git commit -m "docs: Auto-update commit log [skip ci]" || echo "No changes to commit"
          git push
EOF

  # Stage, commit, and push the workflow file
  git add .github/workflows/log_changes.yml
  git commit -m "ci: add commit logging action"
  
  # Push back to GitHub
  git push origin "$DEFAULT_BRANCH"

  # Back out to the workspace folder for the next loop
  cd ..
  
  echo "✅ Finished processing $REPO"
  echo ""
done

echo "🎉 All 6 repositories updated successfully!"