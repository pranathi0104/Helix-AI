"""
utils/document_loader.py — Loads documents for the RAG Knowledge Base.
"""

import os

class DocumentLoader:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def load_documents(self) -> list:
        """
        Traverse the root directory and load all supported documents.
        Returns a list of dictionaries with structure:
        {
            "content": str,
            "source": str,
            "filename": str,
            "title": str
        }
        """
        documents = []
        if not os.path.exists(self.root_dir):
            return documents

        for root, dirs, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith((".txt", ".md")):
                    file_path = os.path.join(root, file)
                    # Use directory name as source (e.g., WHO, CDC)
                    source = os.path.basename(root)
                    title = os.path.splitext(file)[0].replace("_", " ").title()
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        documents.append({
                            "content": content,
                            "source": source,
                            "filename": file,
                            "title": title
                        })
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
                        
        return documents
