import autopep8

class RefactorAgent:
    def refactor(self, code: str) -> str:
        """
        Refactors Python code using autopep8 formatting.
        """
        # Format the code according to PEP8
        formatted_code = autopep8.fix_code(code)
        return formatted_code

