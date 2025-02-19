import ast
import pytest
from jishaku.repl.walkers import KeywordTransformer

def test_visit_return():
    transformer = KeywordTransformer()
    return_node = ast.Return(
        value=ast.Constant(value=42, lineno=1, col_offset=0),
        lineno=1,
        col_offset=0
    )
    transformed_node = transformer.visit_Return(return_node)

    assert isinstance(transformed_node, ast.If)
    assert isinstance(transformed_node.body[0], ast.Expr)
    assert isinstance(transformed_node.body[0].value, ast.Yield)
    assert transformed_node.body[0].value.value.value == 42
    assert isinstance(transformed_node.body[1], ast.Return)
    assert transformed_node.body[1].value is None

def test_visit_delete():
    transformer = KeywordTransformer()
    delete_node = ast.Delete(
        targets=[ast.Name(id='foobar', ctx=ast.Del(), lineno=1, col_offset=0)],
        lineno=1,
        col_offset=0
    )
    transformed_node = transformer.visit_Delete(delete_node)

    assert isinstance(transformed_node, ast.If)
    assert isinstance(transformed_node.body[0], ast.If)
    assert isinstance(transformed_node.body[0].test, ast.Compare)
    assert isinstance(transformed_node.body[0].body[0], ast.Expr)
    assert isinstance(transformed_node.body[0].body[0].value, ast.Call)
    assert transformed_node.body[0].body[0].value.func.attr == 'pop'
    assert isinstance(transformed_node.body[0].orelse[0], ast.Delete)

def test_globals_call():
    transformer = KeywordTransformer()
    node = ast.Constant(value=42, lineno=1, col_offset=0)
    globals_node = transformer.globals_call(node)
    
    assert isinstance(globals_node, ast.Call)
    assert isinstance(globals_node.func, ast.Name)
    assert globals_node.func.id == 'globals'