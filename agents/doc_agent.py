import re

class DocAgent:
    def generate_docs(self, code: str) -> str:
        """
        Generates documentation for each function in the code.
        """
        doc = "Generated Documentation:\n"
        # Find all function definitions
        functions = re.findall(r"def (\w+)\((.*?)\):", code)
        
        if not functions:
            doc += "- No functions found.\n"
        else:
            for func_name, args in functions:
                arg_list = [arg.strip() for arg in args.split(",") if arg]
                doc += f"\nFunction: {func_name}\n"
                doc += f"Arguments: {', '.join(arg_list) if arg_list else 'None'}\n"
                doc += f"Purpose: TODO (Describe what {func_name} does)\n"

        doc += f"\nTotal functions: {len(functions)}"
        return doc

