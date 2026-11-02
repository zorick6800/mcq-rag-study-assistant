# Publish to a separate GitHub repository

Create an empty repository named `mcq-rag-study-assistant` under your own GitHub account. Choose visibility deliberately. Do not initialize it with a README because this package already includes one.

Extract the package and open a terminal in the project folder. Before staging, check that it contains only project code, documentation and original demo data.

```powershell
git init -b main
git add .
git status
git commit -m "Add MCQ practice assistant with local RAG"
git remote add origin https://github.com/YOUR_USERNAME/mcq-rag-study-assistant.git
git push -u origin main
```

Replace YOUR_USERNAME with your GitHub username. If Git asks for author identity, configure your preferred author name and GitHub-associated or GitHub no-reply email. Authenticate through your normal GitHub credential flow; do not put tokens in code or URLs.

Alternatively, share the new empty repository URL in the conversation to continue with the connected GitHub tools. No remote commit has been made by preparing this package.
