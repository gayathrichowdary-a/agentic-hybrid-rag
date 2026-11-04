class ProfileMemoryAgent:

    def extract(self, text):

        memory = {}

        if "favorite language is" in text.lower():

            lang = text.split("favorite language is")[-1].strip()

            memory["favorite_language"] = lang

        return memory