from typing import Any, Dict, Type, Optional, Union, ClassVar
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import ast
import operator

class ArithmeticInput(BaseModel):
    a: Optional[float] = Field(None, description="First number")
    b: Optional[float] = Field(None, description="Second number")
    operation: Optional[str] = Field(None, description="Operation: add, subtract, multiply, divide, power")
    expression: Optional[str] = Field(None, description="Mathematical expression to evaluate (e.g., '2+3*4-5/2')")

class ArithmeticTool(BaseTool):
    name: str = "arithmetic_calculator"
    description: str = "Performs arithmetic operations. Use either: 1) Individual operations with a, b, operation parameters or 2) Complete expressions with expression parameter"
    args_schema: Type[BaseModel] = ArithmeticInput

    operators: ClassVar[Dict] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _run(self, **kwargs) -> str:
        if kwargs.get('a') is not None and kwargs.get('b') is not None and kwargs.get('operation'):
            return self.calculate_basic_operation(**kwargs)
        elif kwargs.get('expression'):
            return self.evaluate_expression(kwargs['expression'])
        else:
            return "Please provide either (a, b, operation) for individual operations or (expression) for complex calculations"

    def calculate_basic_operation(self, a: float, b: float, operation: str, **kwargs) -> str:
        operations = {
            'add': lambda x, y: x + y,
            'subtract': lambda x, y: x - y,
            'multiply': lambda x, y: x * y,
            'divide': lambda x, y: x / y if y != 0 else "Error: Division by zero",
            'power': lambda x, y: x ** y,
            'mod': lambda x, y: x % y if y != 0 else "Error: Modulo by zero"
        }

        op_func = operations.get(operation.lower())
        if not op_func:
            available_ops = ', '.join(operations.keys())
            return f"Unknown operation '{operation}'. Available operations: {available_ops}"

        result = op_func(a, b)
        if isinstance(result, str):
            return result

        return f"The result of {a} {operation} {b} is {result}"

    def evaluate_expression(self, expression: str) -> str:
        expression = expression.strip()
        result = self.parse_mathematical_expression(expression)
        if isinstance(result, str):  # Error message
            return result
        return f"The result of '{expression}' is {result}"

    def parse_mathematical_expression(self, expression: str) -> Union[int, float, str]:
        try:
            node = ast.parse(expression, mode='eval')
            return self.evaluate_ast_node(node.body)
        except (SyntaxError, ValueError) as e:
            return f"Invalid mathematical expression: {e}"

    def evaluate_ast_node(self, node) -> Union[int, float]:
        if isinstance(node, ast.Constant):
            return node.value

        elif isinstance(node, ast.Num):
            return node.n

        elif isinstance(node, ast.BinOp):
            left = self.evaluate_ast_node(node.left)
            right = self.evaluate_ast_node(node.right)

            op_func = self.operators.get(type(node.op))
            if not op_func:
                raise ValueError(f"Unsupported operation: {type(node.op).__name__}")

            if isinstance(node.op, ast.Div) and right == 0:
                raise ValueError("Division by zero")

            return op_func(left, right)

        elif isinstance(node, ast.UnaryOp):
            operand = self.evaluate_ast_node(node.operand)
            op_func = self.operators.get(type(node.op))
            if not op_func:
                raise ValueError(f"Unsupported unary operation: {type(node.op).__name__}")
            return op_func(operand)

        else:
            raise ValueError(f"Unsupported node type: {type(node).__name__}")

    async def _arun(self, **kwargs) -> str:
        return self._run(**kwargs)