"""
HIT137 Assignment 2 - Question 2
Mathematical expression evaluator using recursive descent parsing.
No classes used; built from plain functions only.

Grammar:
    expression  -> term (('+' | '-') term)*
    term        -> unary (('*' | '/') unary)*
    unary       -> '-' unary | primary
    primary     -> NUMBER | '(' expression ')' | implicit_mul
    implicit_mul-> primary primary  (number immediately followed by '(')

Operator precedence (low to high): + - < * / < unary -
"""

import os
import re

# Tokeniser

# Token types
T_NUM    = 'NUM'
T_OP     = 'OP'
T_LPAREN = 'LPAREN'
T_RPAREN = 'RPAREN'
T_END    = 'END'


def tokenise(expr: str):
    """
    Converting an expression string into a list of (type, value) tuples and returning none if any 
    unknown characer is found.
    """
    tokens = []
    i = 0
    while i < len(expr):
        ch = expr[i]

        if ch in ' \t':           # skip whitespace
            i += 1
            continue

        if ch.isdigit() or (ch == '.' and i + 1 < len(expr) and expr[i+1].isdigit()):
            # Reading a numeric literal (integer or decimal)
            j = i
            while j < len(expr) and (expr[j].isdigit() or expr[j] == '.'):
                j += 1
            tokens.append((T_NUM, float(expr[i:j])))
            i = j
            continue

        if ch in '+-*/':
            tokens.append((T_OP, ch))
            i += 1
            continue

        if ch == '(':
            tokens.append((T_LPAREN, '('))
            i += 1
            continue

        if ch == ')':
            tokens.append((T_RPAREN, ')'))
            i += 1
            continue

        # Unknown character -> error
        return None

    tokens.append((T_END, None))
    return tokens


def tokens_to_str(tokens) -> str:
    """Format a token list as the required output string."""
    parts = []
    for ttype, tval in tokens:
        if ttype == T_END:
            parts.append('[END]')
        elif ttype == T_NUM:
            # Display as integer if whole number, else as-is
            if tval == int(tval):
                parts.append(f'[{ttype}:{int(tval)}]')
            else:
                parts.append(f'[{ttype}:{tval}]')
        else:
            parts.append(f'[{ttype}:{tval}]')
    return ' '.join(parts)


# ---------------------------------------------------------------------------
# Parser  (recursive descent, returns an AST as nested tuples)
#
# AST node shapes:
#   ('num',  value)
#   ('neg',  operand_node)
#   ('op',   symbol, left_node, right_node)
# ---------------------------------------------------------------------------

class ParseError(Exception):
    pass


def _peek(tokens, pos):
    return tokens[pos] if pos < len(tokens) else (T_END, None)


def parse_expression(tokens, pos):
    # expression -> term (('+' | '-') term)*
    left, pos = parse_term(tokens, pos)

    while True:
        ttype, tval = _peek(tokens, pos)
        if ttype == T_OP and tval in ('+', '-'):
            pos += 1
            right, pos = parse_term(tokens, pos)
            left = ('op', tval, left, right)
        else:
            break

    return left, pos


def parse_term(tokens, pos):
    # term -> unary (('*' | '/') unary)*  [implicit * for number(expr)]
    left, pos = parse_unary(tokens, pos)

    while True:
        ttype, tval = _peek(tokens, pos)
        if ttype == T_OP and tval in ('*', '/'):
            pos += 1
            right, pos = parse_unary(tokens, pos)
            left = ('op', tval, left, right)
        elif ttype == T_LPAREN:
            # Implicit multiplication: something like 3(2+1)
            right, pos = parse_primary(tokens, pos)
            left = ('op', '*', left, right)
        else:
            break

    return left, pos


def parse_unary(tokens, pos):
    # unary -> '-' unary | primary
    ttype, tval = _peek(tokens, pos)
    if ttype == T_OP and tval == '-':
        pos += 1
        operand, pos = parse_unary(tokens, pos)
        return ('neg', operand), pos
    if ttype == T_OP and tval == '+':
        # Unary + is NOT supported
        raise ParseError("Unary '+' is not supported.")
    return parse_primary(tokens, pos)


def parse_primary(tokens, pos):
    # primary -> NUMBER | '(' expression ')'
    ttype, tval = _peek(tokens, pos)

    if ttype == T_NUM:
        pos += 1
        return ('num', tval), pos

    if ttype == T_LPAREN:
        pos += 1  # consume '('
        node, pos = parse_expression(tokens, pos)
        ttype2, tval2 = _peek(tokens, pos)
        if ttype2 != T_RPAREN:
            raise ParseError("Expected closing ')'.")
        pos += 1  # consume ')'
        return node, pos

    raise ParseError(f"Unexpected token: {ttype}:{tval!r}")


def parse(tokens):
    """
    Parsing a token list and return the root AST node and showing ParseError on any
    syntax issue.
    """
    # Strip the END token for parsing, but remember its position
    if not tokens or tokens[-1][0] != T_END:
        raise ParseError("Token list has no END token.")
    root, pos = parse_expression(tokens, 0)
    # After parsing, only END should remain
    if tokens[pos][0] != T_END:
        raise ParseError(f"Unexpected token after expression: {tokens[pos]}")
    return root


# ---------------------------------------------------------------------------
# AST → string  (prefix notation)
# ---------------------------------------------------------------------------

def tree_to_str(node) -> str:
    """Convert an AST node to its prefix-notation string representation."""
    kind = node[0]
    if kind == 'num':
        val = node[1]
        return str(int(val)) if val == int(val) else str(val)
    if kind == 'neg':
        return f'(neg {tree_to_str(node[1])})'
    if kind == 'op':
        _, sym, left, right = node
        return f'({sym} {tree_to_str(left)} {tree_to_str(right)})'
    raise ValueError(f"Unknown node kind: {kind}")


# ---------------------------------------------------------------------------
# AST evaluator
# ---------------------------------------------------------------------------

class EvalError(Exception):
    pass


def evaluate(node):
    """Walk the AST and compute the numeric result. Raises EvalError on div/0."""
    kind = node[0]
    if kind == 'num':
        return node[1]
    if kind == 'neg':
        return -evaluate(node[1])
    if kind == 'op':
        _, sym, left, right = node
        lv = evaluate(left)
        rv = evaluate(right)
        if sym == '+': return lv + rv
        if sym == '-': return lv - rv
        if sym == '*': return lv * rv
        if sym == '/':
            if rv == 0:
                raise EvalError("Division by zero.")
            return lv / rv
    raise ValueError(f"Unknown node kind: {kind}")


# ---------------------------------------------------------------------------
# Format result
# ---------------------------------------------------------------------------

def format_result(value) -> str:
    """
    Display as integer if value is a whole number (e.g. 8.0 -> '8'),
    otherwise round to 4 decimal places.
    """
    if value == int(value):
        return str(int(value))
    return f'{value:.4f}'


# ---------------------------------------------------------------------------
# Per-expression processing
# ---------------------------------------------------------------------------

def process_expression(expr: str) -> dict:
    """
    Process one expression string and return a result dictionary:
      { 'input': str, 'tree': str, 'tokens': str, 'result': float | 'ERROR' }
    """
    result = {'input': expr, 'tree': 'ERROR', 'tokens': 'ERROR', 'result': 'ERROR'}

    # Tokenise
    tokens = tokenise(expr)
    if tokens is None:
        return result   # unknown character
    result['tokens'] = tokens_to_str(tokens)

    # Parse
    try:
        ast = parse(tokens)
    except ParseError:
        result['tokens'] = 'ERROR'
        return result

    result['tree'] = tree_to_str(ast)

    # Evaluate
    try:
        value = evaluate(ast)
        result['result'] = value
    except EvalError:
        pass   # result stays 'ERROR', tree and tokens are fine

    return result


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def _format_result_for_output(r) -> str:
    if r == 'ERROR':
        return 'ERROR'
    return format_result(r)


def evaluate_file(input_path: str) -> list:
    input_dir = os.path.dirname(os.path.abspath(input_path))
    output_path = os.path.join(input_dir, 'output.txt')

    with open(input_path, 'r', encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f]

    results = [process_expression(line) for line in lines]

    with open(output_path, 'w', encoding='utf-8') as f:
        for i, r in enumerate(results):
            f.write(f"Input: {r['input']}\n")
            f.write(f"Tree: {r['tree']}\n")
            f.write(f"Tokens: {r['tokens']}\n")
            f.write(f"Result: {_format_result_for_output(r['result'])}\n")
            if i < len(results) - 1:
                f.write('\n')

    print(f"[Evaluator] '{input_path}' -> '{output_path}'")
    return results


# Main

if __name__ == '__main__':
    base_dir   = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, 'sample_input.txt')
    results    = evaluate_file(input_path)

    print(f"\nProcessed {len(results)} expression(s).\n")
    for r in results:
        print(f"  {r['input']!r:30s}  ->  {_format_result_for_output(r['result'])}")
