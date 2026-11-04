from langchain.schema import Document

def load_txt(file_path):

    with open(
        file_path,
        encoding="utf-8"
    ) as f:

        text = f.read()

    return [
        Document(
            page_content=text
        )
    ]