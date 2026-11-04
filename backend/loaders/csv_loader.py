import pandas as pd
from langchain.schema import Document

def load_csv(file_path):

    df = pd.read_csv(file_path)

    text = df.to_string()

    return [
        Document(
            page_content=text
        )
    ]