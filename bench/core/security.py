from cave_agent import AttributeRule, FunctionRule, ImportRule, RegexRule, SecurityChecker


SECURITY_CHECKER = SecurityChecker([
    ImportRule({
        "os", "subprocess", "sys", "shutil", "pathlib", "socket", "urllib",
        "http", "ctypes", "inspect", "importlib", "evals", "cases", "core.data",
    }),
    FunctionRule({
        "exec", "compile", "open", "input", "exit", "quit", "__import__",
        "globals", "locals", "eval", "breakpoint",
    }),
    AttributeRule({
        "__globals__", "__code__", "__closure__", "__dict__", "__class__",
        "__bases__", "__mro__", "__subclasses__", "__builtins__",
    }),
    RegexRule(r"(?:evals|cases)[/\\.]", "benchmark answer-key access is forbidden"),
])
